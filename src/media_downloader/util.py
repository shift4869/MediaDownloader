from enum import Enum, auto
from logging import Logger
from typing import Any

from TkEasyGUI import Multiline, Window

window_cache: Window = None


class CustomLogger(Logger):
    def info(self, msg: str, window: Window = None, *args, **kwargs):
        # コンソールとファイル出力
        if "stacklevel" not in kwargs:
            # 呼び出し元の行番号を採用するためにstacklevelを設定
            kwargs["stacklevel"] = 2
        super().info(msg, *args, **kwargs)

        # GUI画面表示
        global window_cache
        if window:
            # windowが指定されていたらキャッシュとして保存
            if not window_cache:
                window_cache = window
        else:
            # windowが指定されていない場合
            if window_cache:
                # キャッシュがあるならそれを採用
                window = window_cache
            else:
                # そうでない場合、画面更新は何もせず終了
                return
        multiline: Multiline = window["-OUTPUT-"]
        old_text = multiline.get_text()
        multiline.set_text(old_text + msg + "\n")
        multiline.update()
        window.refresh()


class Result(Enum):
    SUCCESS = auto()
    FAILED = auto()


def find_values(
    obj: Any,
    key: str,
    is_predict_one: bool = False,
    key_white_list: list[str] = None,
    key_black_list: list[str] = None,
) -> list | Any:
    if not key_white_list:
        key_white_list = []
    if not key_black_list:
        key_black_list = []

    def _inner_helper(inner_obj: Any, inner_key: str, inner_result: list) -> list:
        if isinstance(inner_obj, dict) and (inner_dict := inner_obj):
            for k, v in inner_dict.items():
                if k == inner_key:
                    inner_result.append(v)
                if key_white_list and (k not in key_white_list):
                    continue
                if k in key_black_list:
                    continue
                inner_result.extend(_inner_helper(v, inner_key, []))
        if isinstance(inner_obj, list) and (inner_list := inner_obj):
            for element in inner_list:
                inner_result.extend(_inner_helper(element, inner_key, []))
        return inner_result

    result = _inner_helper(obj, key, [])
    if not is_predict_one:
        return result

    if len(result) < 1:
        raise ValueError(f"Value of key='{key}' is not found.")
    if len(result) > 1:
        raise ValueError(f"Value of key='{key}' are multiple found.")
    return result[0]


if __name__ == "__main__":
    pass
