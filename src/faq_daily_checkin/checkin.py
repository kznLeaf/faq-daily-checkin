import random
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

from faq_daily_checkin.config import get_config


def _get_mmwebid() -> int:
    """
    MMWEBID 是微信内置 WebView 组件实例 ID. 格式为三位或四位数字.
    由客户端生成, 与客户端实例长期绑定, 极少发生变化,
    不管是公众号还是小程序, User-Agent 带有同一个 MMWEBID.
    如果你知道自己的 MMWEBID, 建议手动修改config.yaml
    不过这玩意本来也没那么重要, 随便编一个数字就行了
    """

    id = get_config("mmwebid", 0)
    if id == 0:
        return random.randint(100, 9999)
    return id

def _generate_wechat_miniprogram_ua(appid="wxaa78bf2905f01cee") -> str:
    """
    产生 HTTP 请求头的 User-Agent 字段.
    User-Agent 非常稳定, 基本保持不变
    """
    net_type = "WIFI"

    mm_web_id = _get_mmwebid()

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


def _add_realistic_drift(value, max_limit=0.000003) -> float:
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


def send_checkin_request(
    session_cookie: str,
    latitude: float,
    longitude: float,
    base_url: str,
    api_path: str,
) -> dict[str, Any]:
    """
    发送每日打卡请求.

    Args:
        session_cookie: 用户 SESSION cookie 值
        latitude: 纬度
        longitude: 经度

    Returns:
        包含打卡结果的字典:
        {
            "success": bool,       # 是否成功
            "message": str,        # 成功或失败的具体信息
            "raw_response": dict,  # 服务器返回的原始 JSON (如果解析成功)
        }
    """

    # 填充请求体的 clientTime 字段
    # e.g. 2026-10-17 14:35:12
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    client_time = now.strftime("%Y-%m-%d %H:%M:%S")
    user_agent = _generate_wechat_miniprogram_ua()

    session_id = str(uuid.uuid4())

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "platform": "h5",
        "Origin": base_url,
        "X-Requested-With": "com.tencent.mm",
        "User-Agent": user_agent,
        "Referer": f"{base_url}/daily-checkin-h5/index.html?sessionId={session_id}",
        "sec-ch-ua-platform": '"Android"',
        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Android WebView";v="150"',
        "sec-ch-ua-mobile": "?1",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }

    cookies = {"SESSION": session_cookie}

    payload = {
        "latitude": _add_realistic_drift(latitude),
        "longitude": _add_realistic_drift(longitude),
        "reverseGeocode": "四川省成都市郫都区蓉昌高速",
        "clientTime": client_time,
        "userAgent": user_agent,
        "coordinateSystemCode": "gcj02",
        "accuracy": 30,
        "locationDurationMs": random.randint(300, 1000),
        "networkTypeCode": "wifi",
        "locationEnabled": False,
        "locationAuthorized": "",
        "locationAccuracy": "",
        "errorMessage": "",
    }

    # 4. 发送请求并处理异常
    response = None
    try:
        response = requests.post(
            url=f"{base_url}{api_path}",
            headers=headers,
            cookies=cookies,
            json=payload,
            timeout=10,
        )
        # 检查 HTTP 状态码是否为 200 OK (可选，但推荐)
        response.raise_for_status()

        res_json = response.json()

        # 根据业务逻辑判断是否成功
        if res_json.get("code") == 0 and res_json.get("ok"):
            return {
                "success": True,
                "message": res_json.get("msg", "打卡成功"),
                "raw_response": res_json,
            }
        else:
            return {
                "success": False,
                "message": res_json.get("msg", "未完成打卡"),
                "raw_response": res_json,
            }

    except requests.exceptions.HTTPError as e:
        return {
            "success": False,
            "message": f"HTTP 错误: {e}",
            "raw_response": getattr(response, "text", "无响应内容"),
        }
    except requests.exceptions.RequestException as e:
        # 捕获所有网络层面的异常 (超时、连接断开、DNS解析失败等)
        return {
            "success": False,
            "message": f"网络请求异常: {e}",
            "raw_response": None,
        }
    except ValueError:
        # JSON 解析失败
        resp_text = response.text if response is not None else "无响应"
        return {
            "success": False,
            "message": f"服务器返回了无效的 JSON 数据: {resp_text[:100]}...",
            "raw_response": None,
        }
