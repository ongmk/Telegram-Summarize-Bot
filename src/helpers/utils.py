import datetime
import json
import re
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


class NoCodeBlockFoundError(Exception):
    pass


def capture_code(text, language, multiple=False):
    regex = rf"```(?:{language})?(.*?)```"
    if multiple:
        matches = re.findall(regex, text, re.DOTALL)
        if not matches:
            raise NoCodeBlockFoundError("No code block found.")
        return matches
    else:
        match = re.search(regex, text, re.DOTALL)
        if not match:
            return text.strip()
        return match.group(1)
