import argparse
import sys
from typing import Any

from faq_daily_checkin.checkin import send_checkin_request
from faq_daily_checkin.config import get_config
from faq_daily_checkin.login import get_session_cookie
from faq_daily_checkin.schedule import TaskScheduler
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
        "--session",
        type=str,
        default="",
        help="手动输入 session cookie. 启用此项将跳过脚本登录, 直接用给定的 cookie 访问打卡接口.",
    )

    parser.add_argument(
        "--loop",
        action="store_true",
        help="在指定范围内随机选择一个时间进行打卡, 完成一次打卡后继续重复上述过程.",
    )

    args = parser.parse_args()
    return args


def login_and_checkin(session_cookie: Any):
    if not session_cookie:
        session_cookie = get_session_cookie()
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


def main():
    args = parse_args()

    session_cookie = args.session

    try:
        if args.loop:
            t = TaskScheduler(TIME_START, TIME_END)
            while True:
                t.run(lambda: login_and_checkin(session_cookie))
        else:
            login_and_checkin(session_cookie)
    except KeyboardInterrupt:
        print("退出程序...")


if __name__ == "__main__":
    main()
