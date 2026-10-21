# TODO: 参考 https://github.com/mitmproxy/mitmproxy/blob/main/mitmproxy/log.py
# 完善日志系统
def print_success(msg):
    print(f"\033[32m{msg}\033[0m")


def print_warning(msg):
    print(f"\033[33m{msg}\033[0m")


def print_error(msg):
    print(f"\033[31m{msg}\033[0m")
