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

    def __hash__(self):
        return hash((type(self), self.title))

    def __eq__(self, other):
        if isinstance(other, Headline):
            return self.title == other.title
        return False


def to_serializable(obj: Any):
    if is_dataclass(obj):
        return asdict(obj)
    return obj  # For built-in types


if __name__ == "__main__":
    a = Headline(
        "Apple Daily", "2021-09-01", "Title 1", "Summary 1", "https://example.com/1"
    )
    b = Headline(
        "Ming Pao", "2021-09-02", "Title 1", "Summary 2", "https://example.com/2"
    )
    print(a == b)
    print(set(list([a, b])))
