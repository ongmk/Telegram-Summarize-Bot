import json
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, List


@dataclass
class Headline:
    publisher: str
    time: str
    title: str
    summary: str
    link: str


def to_serializable(obj: Any):
    if is_dataclass(obj):
        return asdict(obj)
    return obj  # For built-in types
