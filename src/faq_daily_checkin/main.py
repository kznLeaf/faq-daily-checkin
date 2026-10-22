import argparse
import sys

from faq_daily_checkin.checkin import send_checkin_request
from faq_daily_checkin.config import get_config
from faq_daily_checkin.login import auto_login
from faq_daily_checkin.utils import print_error, print_success

LATITUDE = get_config("position.latitude", 0.0)
LONGITUDE = get_config("position.longitude", 0.0)
TIME_START = get_config("time.start", "")
TIME_END = get_config("time.end", "")

BASE_URL = "https://jzsz.uestc.edu.cn"
API_PATH = "/daily-checkin/api/student-checkin-record/checkin"


def parse_args():
    parser = argparse.ArgumentParser(description="F U UESTC")
    parser.add_argument(
        "-s",
        "--session",
        type=str,
        default="",
        help="手动输入 session cookie. 启用此项将跳过脚本登录, 直接用给定的 cookie 访问打卡接口.",
    )

    # TODO: 完善命令行参数的解析
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--now", action="store_true", help="立即尝试打卡. 默认行为."
    )

    mode_group.add_argument(
        "--once",
        action="store_true",
        help="有效打卡时间区间内随机选择一个时间点, 完成打卡后退出程序",
    )
    mode_group.add_argument(
        "--loop",
        action="store_true",
        help="--loop 在完成一次打卡后继续等待下一次打卡, 不退出程序",
    )

    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    session_cookie = args.session
    if not args.session:
        print("开始登录获取session...")
        active_session = auto_login()
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
        session_cookie, LATITUDE, LONGITUDE, BASE_URL, API_PATH
    )
    if result["success"] is True:
        print_success("打卡成功")
    else:
        print_error("未完成打卡，响应如下：")
        print(result)


if __name__ == "__main__":
    main()
