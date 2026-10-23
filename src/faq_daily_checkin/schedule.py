import datetime
import random
import time
from collections.abc import Callable


class TaskScheduler:
    def __init__(self, start_time_str: str, end_time_str: str):
        self.start_time_str = start_time_str
        self.end_time_str = end_time_str
        self.last_exec_date: datetime.date | None = None

    def run(self, task_func: Callable[[], None]):
        fmt = "%H:%M"
        today = datetime.date.today()
        now = datetime.datetime.now()

        start_t = datetime.datetime.strptime(self.start_time_str, fmt).time()
        end_t = datetime.datetime.strptime(self.end_time_str, fmt).time()

        start_dt = datetime.datetime.combine(today, start_t)
        end_dt = datetime.datetime.combine(today, end_t)

        if end_dt <= start_dt:
            end_dt += datetime.timedelta(days=1)

        delta_seconds = int((end_dt - start_dt).total_seconds())
        random_seconds = random.randint(0, delta_seconds)
        target_dt = start_dt + datetime.timedelta(seconds=random_seconds)

        if target_dt < now:
            target_dt += datetime.timedelta(days=1)

        if target_dt.date() == today and self.last_exec_date == today:
            target_dt += datetime.timedelta(days=1)

        wait_seconds = (target_dt - now).total_seconds()

        print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"下次打卡时间: {target_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        time.sleep(wait_seconds)
        task_func()

        self.last_exec_date = today
