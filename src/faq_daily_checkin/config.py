# config.py

from typing import Any

import yaml

from faq_daily_checkin.utils import get_project_root

CONFIG_PATH = get_project_root() / "config.yaml"
EXAMPLE_CONFIG_PATH = get_project_root() / "config.yaml.example"

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        CONFIG = yaml.safe_load(f)
        # TODO: Validate
except FileNotFoundError:
    if EXAMPLE_CONFIG_PATH.is_file():
        error_msg = (
            f" 找不到配置文件: {CONFIG_PATH}\n"
            f" 尝试将 config.yaml.example 重命名为config.yaml\n"
        )
        raise RuntimeError(error_msg)
    else:
        raise RuntimeError(f"找不到配置文件 {CONFIG_PATH}")
except yaml.YAMLError as e:
    raise RuntimeError(f"YAML 解析失败\n{e}")


def get_config(key_path: str, default=None) -> Any:
    """
    返回 config.yaml 中的配置值
    用法: get_config('a.b.c', default)
    """
    if CONFIG is None:
        return default

    keys = key_path.split(".")
    val = CONFIG
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val
