import argparse
import sys

from faq_daily_checkin.checkin import send_checkin_request
from faq_daily_checkin.login import auto_login
from faq_daily_checkin.utils import print_error, print_success

# ==========================================
# 用户特定的常量
# 一个有效打卡位置的经纬度坐标, 每个人的有效打卡范围不同, 自己测定. 保留 6 位小数.
LATITUDE = 0.0
LONGITUDE = 0.0
# ==========================================


def parse_args():
    parser = argparse.ArgumentParser(description="F U UESTC")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode. Test only."
    )
    parser.add_argument(
        "-s",
        "--session",
        type=str,
        default="",
        help="Manually pass session cookie via command line",
    )
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    base_url = "https://jzsz.uestc.edu.cn"
    api_path = "/daily-checkin/api/student-checkin-record/checkin"

    if args.debug:
        print("Debug Mode Enabled")
        base_url = "http://localhost:8080"
        api_path = "/"

    print("开始登录获取session...")
    active_session = auto_login()
    session_cookie = ""
    if active_session:
        print_success("登录流程全部完成！")
        for cookie in active_session.cookies:
            if cookie.name == "SESSION":
                session_cookie = cookie.value
    else:
        print_error("登录失败")
        sys.exit(1)

    if not session_cookie:
        print_error("获取 session cookie 失败")
        sys.exit(1)

    print("开始打卡")
    result = send_checkin_request(
        session_cookie, LATITUDE, LONGITUDE, base_url, api_path
    )
    if result["success"] is True:
        print_success("打卡成功")
    else:
        print_error("未完成打卡，响应如下：")
        print(result)


if __name__ == "__main__":
    main()
