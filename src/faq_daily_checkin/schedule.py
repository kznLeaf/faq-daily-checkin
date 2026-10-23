import datetime
import random
import time


def schedule_random_task(start_time_str: str, end_time_str: str, task_func):
    """
    在指定的两个时间字符串之间随机选择一个时间点，并在该时间执行给定任务。
    
    :param start_time_str: 开始时间，格式 "HH:MM" (如 "21:00")
    :param end_time_str: 结束时间，格式 "HH:MM" (如 "22:00")
    :param task_func: 要执行的函数
    """
    fmt = "%H:%M"
    today = datetime.date.today()
    now = datetime.datetime.now()
    
    # 解析时间字符串为 time 对象
    start_t = datetime.datetime.strptime(start_time_str, fmt).time()
    end_t = datetime.datetime.strptime(end_time_str, fmt).time()
    
    # 组合成今天的 datetime 对象
    start_dt = datetime.datetime.combine(today, start_t)
    end_dt = datetime.datetime.combine(today, end_t)
    
    # 处理跨天情况 (例如 start="23:00", end="01:00")
    if end_dt <= start_dt:
        end_dt += datetime.timedelta(days=1)
        
    # 计算时间跨度（秒），并生成随机秒数
    delta_seconds = int((end_dt - start_dt).total_seconds())
    random_seconds = random.randint(0, delta_seconds)
    target_dt = start_dt + datetime.timedelta(seconds=random_seconds)
    
    #  边界处理：如果生成的时间已经过去了，自动推迟到明天
    if target_dt < now:
        target_dt += datetime.timedelta(days=1)
        
    # 计算需要等待的秒数并阻塞
    wait_seconds = (target_dt - now).total_seconds()
    
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"预计打卡时间: {target_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"需要等待: {wait_seconds / 60:.1f} 分钟")
    
    time.sleep(wait_seconds)
    
    task_func()
