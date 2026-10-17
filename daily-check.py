# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests>=2.34.2",
# ]
# ///

import argparse
import os
import random
import sys
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# ==========================================
# 用户特定的常量
# 一个有效打卡位置的经纬度坐标, 每个人的有效打卡范围不同, 自己测定. 保留 6 位小数.
LATITUDE = 0.0
LONGITUDE = 0.0
# session cookie, 在 PC 端打开 F12 登录 https://jzsz.uestc.edu.cn
# 然后在 Cookie 选项卡中就能看到.
# session cookie 安全性极差, 重放 cookie 即可通过身份验证.
CHECKIN_SESSION = ""
# ==========================================
# 服务器地址
BASE_URL = "https://jzsz.uestc.edu.cn"
API_PATH = "/daily-checkin/api/student-checkin-record/checkin"
# ==========================================
CONFIG_FILE = Path(__file__).resolve().parent  / "config.txt"

def get_mmwebid() -> int:
    """
    MMWEBID 是微信内置 WebView 组件实例 ID. 格式为三位或四位数字.
    由客户端生成, 与客户端实例长期绑定, 极少发生变化,
    不管是公众号还是小程序, User-Agent 带有同一个 MMWEBID.
    这里采用的方式是仅在第一次运行时随机产生一个ID, 后续每次复用.
    如果你知道自己的 MMWEBID, 建议手动修改config.txt
    """
    if CONFIG_FILE.exists():
        try:
            number = int(CONFIG_FILE.read_text(encoding="utf-8").strip())
            if 100 <= number <= 9999:
                return number
        except (ValueError, OSError):
            pass

    number = random.randint(100, 9999)
    CONFIG_FILE.write_text(str(number), encoding="utf-8")
    return number
    


def generate_wechat_miniprogram_ua(appid="wxaa78bf2905f01cee") -> str:
    """
    产生 HTTP 请求头的 User-Agent 字段.
    User-Agent 非常稳定, 基本保持不变
    """
    net_type = "WIFI"

    mm_web_id = get_mmwebid()

    # 一些版本信息
    wechat_version = "8.0.79.3200(0x28004F32)"
    xweb_version = "1500145"
    sdk_date = "20260902"
    chrome_version = "150.0.7871.189"

    # 组装 UA
    ua = (
        f"Mozilla/5.0 (Linux; Android 14; ELI-AN00 Build/HONORELI-AN00; wv) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{chrome_version} "
        f"Mobile Safari/537.36 XWEB/{xweb_version} MMWEBSDK/{sdk_date} "
        f"MMWEBID/{mm_web_id} MicroMessenger/{wechat_version} "
        f"WeChat/arm64 Weixin NetType/{net_type} Language/zh_CN ABI/arm64 "
        f"miniProgram/{appid}"
    )
    return ua


def add_realistic_drift(value, max_limit=0.000003) -> float:
    """
    为给定的经纬度叠加一个误差值, 用于混淆.
    位置坐标测量值波动幅度大约是 1e-6°, 这里让最大偏移不超过0.000003
    """
    # 标准差
    sigma = max_limit / 3.0

    # 生成均值为 0, 标准差为 σ 的正态随机偏差
    drift = random.gauss(0, sigma)

    # 确保不超出 ±0.000003 的范围
    drift = max(-max_limit, min(drift, max_limit))

    # 仍然保留六位小数
    return round(value + drift, 6)


# 从环境变量中获取固定的用户常量
# 防止手贱把敏感信息提交到repo
if LATITUDE == 0.0:
    LATITUDE = float(os.environ.get("LATITUDE", "0.0"))
if LONGITUDE == 0.0:
    LONGITUDE = float(os.environ.get("LONGITUDE", "0.0"))

# 解析命令行参数
parser = argparse.ArgumentParser(description="F U UESTC")
parser.add_argument(
    "--debug", action="store_true", help="Enable debug mode. Test only."
)
parser.add_argument(
    "-s",
    "--session",
    type=str,
    default=None,
    help="Pass session cookie via command line",
)
args = parser.parse_args()

if args.session is not None:
    CHECKIN_SESSION = args.session
if CHECKIN_SESSION == "":
    print("Error: 缺少session cookie")
    sys.exit(1)

if args.debug:
    print("Debug Mode Enabled")
    BASE_URL = "http://localhost:8080"
    API_PATH = "/"


# 填充请求体的 clientTime 字段
# e.g. 2026-10-17 14:35:12
now = datetime.now(ZoneInfo("Asia/Shanghai"))
client_time = now.strftime("%Y-%m-%d %H:%M:%S")

user_agent = generate_wechat_miniprogram_ua()

# 这个 sessionId 不同于 Cookie, 与打卡无关, 仅占位凑够请求头
sessonId = str(uuid.uuid4())

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "platform": "h5",
    "Origin": "https://jzsz.uestc.edu.cn",
    "X-Requested-With": "com.tencent.mm",
    "User-Agent": user_agent,
    "Referer": "https://jzsz.uestc.edu.cn/daily-checkin-h5/index.html?sessionId="
    + sessonId,
    # 浏览器指纹, 没那么重要, 以防万一还是加上
    "sec-ch-ua-platform": '"Android"',
    "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Android WebView";v="150"',
    "sec-ch-ua-mobile": "?1",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}

cookies = {"SESSION": CHECKIN_SESSION}

# request body
payload = {
    "latitude": add_realistic_drift(LATITUDE),
    "longitude": add_realistic_drift(LONGITUDE),
    "reverseGeocode": "四川省成都市郫都区蓉昌高速",
    "clientTime": client_time,
    "userAgent": user_agent,
    # gcj02 是中国独创的地理位置混淆算法(混淆机制未公开), 在国际标准 WGS84 基础上刻意加入非线性偏移量以降低定位精度
    # 腾讯地图用的就是这一套, 固定写死
    "coordinateSystemCode": "gcj02", 
    "accuracy": 30,
    "locationDurationMs": random.randint(300, 1000),  # 定位耗时(ms)
    "networkTypeCode": "wifi",
    "locationEnabled": False,
    "locationAuthorized": "",
    "locationAccuracy": "",
    "errorMessage": "",
}

response = None

try:
    response = requests.post(
        url=BASE_URL + API_PATH,
        headers=headers,
        cookies=cookies,
        json=payload,
        timeout=10,
    )
    res_json = response.json()
    if res_json.get("code") == 0 and res_json.get("ok"):
        print(f"✅打卡成功, msg: {res_json.get('msg')}")
    else:
        print("⚠️未完成打卡, 完整响应如下:")
        print(f"{res_json}")

except requests.exceptions.RequestException as e:
    # 统一捕获所有网络层面的异常 (超时、连接断开、DNS解析失败等)
    print(f"❌网络请求异常: {e}")

except ValueError:
    if response is not None:
        print(f"❌服务器返回了无效的 JSON 数据:\n{response.text}...")
    else:
        print("❌解析错误")
