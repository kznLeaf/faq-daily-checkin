import os
import random
import re
import time

import requests

from faq_daily_checkin.encrypt import encrypt_password

# ==========================================
# 从环境变量从提取
STUDENT_ID = os.environ.get("STUDENT_ID", "")
PASSWORD = os.environ.get("PASSWORD", "")
# 从浏览器 F12 -> Application -> Cookies -> idas.uestc.edu.cn 中复制的 32 位十六进制字符串
BROWSER_FINGERPRINT = os.environ.get("BROWSER_FINGERPRINT", "")
# ==========================================
IDAS_HOST = "https://idas.uestc.edu.cn"
JZSZ_HOST = "https://jzsz.uestc.edu.cn"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:153.0) Gecko/20100101 Firefox/153.0"
# ==========================================
# 固定字符集 (与前端 encrypt.js 保持一致)
CHARSET = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"


def get_random_string(length: int) -> str:
    """使用指定字符集生成随机字符串"""
    return "".join(random.choice(CHARSET) for _ in range(length))


def auto_login():
    if not STUDENT_ID or not PASSWORD or not BROWSER_FINGERPRINT:
        print("学号/密码/浏览器指纹不完整, 退出程序.")
        return False
    # 使用 Session 自动管理 Cookie (JSESSIONID, CASTGC, SESSION 等)
    session = requests.Session()

    # 默认请求头，每次都携带
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,en-US;q=0.9,en;q=0.8",
        }
    )

    print("[Step 1] 正在获取登录页动态参数...")
    login_url = f"{IDAS_HOST}/authserver/login?service={JZSZ_HOST}/"
    resp = session.get(login_url)
    resp.raise_for_status()

    # 提取 execution(用于提交表单) 和 pwdEncryptSalt(用于加密密码)
    exec_match = re.search(r'name="execution"\s+value="([^"]+)"', resp.text)
    salt_match = re.search(r'id="pwdEncryptSalt"\s+value="([^"]+)"', resp.text)

    if not exec_match or not salt_match:
        print("❌ 无法从登录页提取 execution 或 pwdEncryptSalt")
        return False

    execution = exec_match.group(1)
    salt = salt_match.group(1)
    print(f"✅ 获取成功: execution={execution}, salt={salt}")

    print("[Step 2] 正在上报浏览器指纹 (绕过二次验证)...")
    bfp_url = f"{IDAS_HOST}/authserver/bfp/info?bfp={BROWSER_FINGERPRINT}&_={int(time.time() * 1000)}"
    session.headers["X-Requested-With"] = "XMLHttpRequest"
    resp_bfp = session.get(bfp_url)
    if resp_bfp.status_code == 200:
        print("✅ 指纹上报成功，已建立可信设备标记。")
    else:
        print(f"⚠️ 指纹上报返回状态码: {resp_bfp.status_code} (继续尝试登录)")
    # 恢复默认 Accept header
    session.headers.pop("X-Requested-With", None)

    print("[Step 3] 正在加密密码并提交登录...")
    encrypted_pwd = encrypt_password(PASSWORD, salt)

    login_data = {
        "username": STUDENT_ID,
        "password": encrypted_pwd,
        "captcha": "",
        "_eventId": "submit",
        "cllt": "userNameLogin",
        "dllt": "generalLogin",
        "lt": "",
        "execution": execution,
    }

    session.headers["Content-Type"] = "application/x-www-form-urlencoded"
    session.headers["Origin"] = IDAS_HOST
    session.headers["Referer"] = login_url

    # 提交登录. 这里禁用了自动重定向
    resp_submit = session.post(login_url, data=login_data, allow_redirects=False)

    if resp_submit.status_code == 302:
        location = resp_submit.headers.get("Location", "")
        print(f"✅ 登录成功，获得重定向 Ticket: {location}")

        # Step 4: 跟随重定向，换取业务平台的 SESSION
        print("[Step 4] 正在跟随重定向获取 SESSION...")
        session.headers["Referer"] = f"{IDAS_HOST}/"
        resp_ticket = session.get(location)

        # 检查是否成功获取了 jzsz 的 SESSION
        session_cookie = session.cookies.get("SESSION", domain="jzsz.uestc.edu.cn")
        if session_cookie:
            print(f"✅ 成功获取业务 SESSION: {session_cookie}")
        else:
            print("⚠️ 未检测到 SESSION Cookie")

        # 真实用户通过浏览器访问 jzsz 时会先向 /api/isLoginFailure 发送请求
        print("[Step 5] /api/isLoginFailure")
        warmup_url = f"{JZSZ_HOST}/api/isLoginFailure?_t={int(time.time() * 1000)}"
        session.headers["Accept"] = "application/json, text/plain, */*"
        session.headers["Content-Type"] = "application/json;charset=UTF-8"
        session.headers["Origin"] = JZSZ_HOST
        session.headers["Referer"] = f"{JZSZ_HOST}/"
        session.headers["Sec-Fetch-Site"] = "same-origin"
        session.headers["Sec-Fetch-Mode"] = "cors"

        resp_warmup = session.get(warmup_url)
        if resp_warmup.status_code == 200:
            print("✅ 门户预热成功！当前 Session 已完全激活，可用于后续打卡接口。")
            # 此时 session 对象中已包含所有有效的 Cookie，可以直接用于后续的 POST 打卡请求
            return session
        else:
            print(f"❌ 门户预热失败，状态码: {resp_warmup.status_code}")
            return False

    else:
        print(f"❌ 登录提交失败，状态码: {resp_submit.status_code}")
        print("响应内容片段:", resp_submit.text[:200])
        return False
