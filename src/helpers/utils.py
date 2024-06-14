import datetime
import json
from typing import Any, List


def save_as_json(data: Any, filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_json(filename: str) -> List[Any]:
    with open(filename, "r", encoding="utf-8") as f:
        data_dicts = json.load(f)
    return data_dicts


def datetime_to_str(date_time: datetime.datetime) -> str:
    return date_time.strftime("%Y-%m-%d %H:%M:%S")


def str_to_datetime(date_time: str) -> datetime.datetime:
    return datetime.datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
