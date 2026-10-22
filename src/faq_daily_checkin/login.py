import random
import re
import sys
import time

import requests

from faq_daily_checkin.config import get_config
from faq_daily_checkin.encrypt import encrypt_password
from faq_daily_checkin.utils import print_error

# ==========================================
STUDENT_ID = get_config("student_id", "")
PASSWORD = get_config("password", "")
# 打开 F12，从 idas.uestc.edu.cn 的 Cookie 中复制 MULTIFACTOR_BROWSER_FINGERPRINT 的值
BROWSER_FINGERPRINT = get_config("browser_fingerprint", "")
# ==========================================
IDAS_HOST = "https://idas.uestc.edu.cn"
JZSZ_HOST = "https://jzsz.uestc.edu.cn"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:153.0) Gecko/20100101 Firefox/153.0"
# ==========================================
CHARSET = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"


def get_random_string(length: int) -> str:
    """使用指定字符集生成随机字符串"""
    return "".join(random.choice(CHARSET) for _ in range(length))


def auto_login():
    """
    自动利用账密完成登录, 如果成功则返回已经建立的session对象.
    如果失败，返回false。
    session用于获取session cookie，用于请求打卡接口
    """
    if not STUDENT_ID or not PASSWORD or not BROWSER_FINGERPRINT:
        print("学号/密码/浏览器指纹缺失, 退出程序.")
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

    print("[1/4] 获取登录页动态参数")
    login_url = f"{IDAS_HOST}/authserver/login?service={JZSZ_HOST}/"
    resp = session.get(login_url)
    resp.raise_for_status()

    # 提取 execution(用于提交表单) 和 pwdEncryptSalt(用于加密密码)
    exec_match = re.search(r'name="execution"\s+value="([^"]+)"', resp.text)
    salt_match = re.search(r'id="pwdEncryptSalt"\s+value="([^"]+)"', resp.text)

    if not exec_match or not salt_match:
        print_error("无法从登录页提取 execution 或 pwdEncryptSalt")
        return False

    execution = exec_match.group(1)
    salt = salt_match.group(1)
    print(f"成功获取 execution={execution}, salt={salt}")

    # 只有访问 idas 登录的时候才需要携带 MULTIFACTOR_BROWSER_FINGERPRINT
    session.cookies.set(
        name="MULTIFACTOR_BROWSER_FINGERPRINT",
        value=BROWSER_FINGERPRINT,
        domain="idas.uestc.edu.cn",
        path="/",
    )

    print("[2/4] 正在加密密码并提交登录...")
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
        print(f"登录成功，获得重定向 Ticket: {location}")

        # 跟随重定向，换取业务平台的 SESSION
        print("[3/4] 正在跟随重定向获取 SESSION...")
        session.headers["Referer"] = f"{IDAS_HOST}/"

        # 必须向重定向指向的目标 URL 发送一次请求，
        # 否则下一步可能拿不到SESSION
        session.get(location)

        # 检查是否成功获取了 jzsz 的 SESSION
        session_cookie = session.cookies.get("SESSION", domain="jzsz.uestc.edu.cn")
        if session_cookie:
            print(f"成功获取业务 SESSION: {session_cookie}")
        else:
            print_error("未检测到 SESSION Cookie. 完整cookie列表:")
            for cookie in session.cookies:
                print(f"  - {cookie.name}: {cookie.value} (Domain: {cookie.domain})")
            sys.exit(1)

        # 真实用户通过浏览器访问 jzsz 时会先向 /api/isLoginFailure 发送请求
        print("[4/4] 激活 session cookie")
        warmup_url = f"{JZSZ_HOST}/api/isLoginFailure?_t={int(time.time() * 1000)}"
        session.headers["Accept"] = "application/json, text/plain, */*"
        session.headers["Content-Type"] = "application/json;charset=UTF-8"
        session.headers["Origin"] = JZSZ_HOST
        session.headers["Referer"] = f"{JZSZ_HOST}/"
        session.headers["Sec-Fetch-Site"] = "same-origin"
        session.headers["Sec-Fetch-Mode"] = "cors"

        resp_warmup = session.get(warmup_url)
        if resp_warmup.status_code == 200:
            print("成功激活！")
            # 此时 session 对象中已包含所有有效的 Cookie，可以直接用于后续的 POST 打卡请求
            return session
        else:
            print_error(f"激活失败: {resp_warmup.status_code}")
            return False

    else:
        print_error(f"登录失败，响应如下：\n{resp_submit.text}")
        return False
