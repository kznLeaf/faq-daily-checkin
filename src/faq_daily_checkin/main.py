import argparse
import sys

from faq_daily_checkin.checkin import send_checkin_request

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

    if not args.session or not args.session.strip():
        print("Error: 缺少session cookie")
        sys.exit(1)

    if args.debug:
        print("Debug Mode Enabled")
        base_url = "http://localhost:8080"
        api_path = "/"

    print(send_checkin_request("123", LATITUDE, LONGITUDE, base_url, api_path))


if __name__ == "__main__":
    main()
