from dataclasses import dataclass
import re
from typing import ClassVar

import emoji


@dataclass(frozen=True)
class Worktitle:
    _original_title: str
    _title: ClassVar[str]

    def __post_init__(self) -> None:
        if not isinstance(self._original_title, str):
            raise TypeError("title is not string, invalid Worktitle.")
        if self._original_title == "":
            raise ValueError("empty string, invalid Worktitle")

        regex = re.compile(r'[\\/:*?"<>|]')
        trimed_title = regex.sub("", self._original_title)
        non_emoji_title = emoji.replace_emoji(trimed_title, "")
        object.__setattr__(self, "_title", non_emoji_title)

    @property
    def title(self) -> str:
        return self._title


if __name__ == "__main__":
    titles = [
        "作成者1",
        "",
        -1,
    ]

    for title in titles:
        try:
            work_title = Worktitle(title)
            print(work_title)
        except (ValueError, TypeError) as e:
            print(e.args[0])
