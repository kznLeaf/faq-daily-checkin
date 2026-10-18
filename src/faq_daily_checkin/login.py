import random
import re
import time

import requests

from faq_daily_checkin.encrypt import encrypt_password

# ================= 配置区域 =================
# 替换为你自己的真实信息
STUDENT_ID = "你的学号"
PASSWORD = "你的密码"
# 从浏览器 F12 -> Application -> Cookies -> idas.uestc.edu.cn 中复制的 32 位十六进制字符串
BROWSER_FINGERPRINT = "你的32位MULTIFACTOR_BROWSER_FINGERPRINT"

# 固定字符集 (与前端 encrypt.js 保持一致)
CHARSET = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"

IDAS_HOST = "https://idas.uestc.edu.cn"
JZSZ_HOST = "https://jzsz.uestc.edu.cn"
# ==========================================


def get_random_string(length: int) -> str:
    """使用指定字符集生成随机字符串"""
    return "".join(random.choice(CHARSET) for _ in range(length))


def auto_login():
    # 使用 Session 自动管理 Cookie (JSESSIONID, CASTGC, SESSION 等)
    session = requests.Session()

    # 设置通用 Headers，模拟真实浏览器
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    )

    print("[Step 1] 正在获取登录页动态参数...")
    login_url = f"{IDAS_HOST}/authserver/login?service={JZSZ_HOST}/"
    resp = session.get(login_url)
    resp.raise_for_status()

    # 提取 execution 和 pwdEncryptSalt
    exec_match = re.search(r'name="execution"\s+value="([^"]+)"', resp.text)
    salt_match = re.search(r'id="pwdEncryptSalt"\s+value="([^"]+)"', resp.text)

    if not exec_match or not salt_match:
        print(
            "❌ 失败：无法从登录页提取 execution 或 pwdEncryptSalt。页面结构可能已更改。"
        )
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

    # 提交登录 (allow_redirects=False 以便我们观察 302 重定向)
    resp_submit = session.post(login_url, data=login_data, allow_redirects=False)

    if resp_submit.status_code == 302:
        location = resp_submit.headers.get("Location", "")
        print(f"✅ 登录成功，获得重定向 Ticket: {location[:60]}...")

        # Step 4: 跟随重定向，换取业务平台的 SESSION
        print("[Step 4] 正在使用 Ticket 换取业务平台 SESSION...")
        session.headers["Referer"] = f"{IDAS_HOST}/"
        resp_ticket = session.get(location)

        # 检查是否成功获取了 jzsz 的 SESSION
        session_cookie = session.cookies.get("SESSION", domain="jzsz.uestc.edu.cn")
        if session_cookie:
            print(f"✅ 成功获取业务 SESSION: {session_cookie[:20]}...")
        else:
            print("⚠️ 未检测到 SESSION Cookie，可能登录态异常。")

        # Step 5: 门户预热 (关键！)
        print("[Step 5] 正在进行门户预热 (激活微应用权限)...")
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


if __name__ == "__main__":
    print("=" * 50)
    print(" UESTC 自动化登录脚本")
    print("=" * 50)

    active_session = auto_login()

    if active_session:
        print("\n🎉 登录流程全部完成！")
        print("你可以使用 `active_session.post(...)` 继续发起打卡请求。")
        print("当前有效的 Cookies:")
        for cookie in active_session.cookies:
            print(
                f"  - {cookie.name}: {cookie.value[:30]}... (Domain: {cookie.domain})"
            )
