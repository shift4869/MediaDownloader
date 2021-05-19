# coding: utf-8
import logging.config
from logging import INFO, getLogger
from pathlib import Path

import PySimpleGUI as sg

from MediaDownloader import LinkSearchMain


logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
logger = getLogger("root")
logger.setLevel(INFO)


def GuiMain():
    # 対象サイト
    target = ["pixiv", "nijie"]

    # 対象URL例
    target_url_example = {
        "pixiv": "https://www.pixiv.net/artworks/xxxxxxxx",
        "nijie": "http://nijie.info/view_popup.php?id=xxxxxx",
    }

    # ウィンドウのレイアウト
    layout = [
        [sg.Text("MediaDownloader")],
        [sg.Text("")],
        [sg.Text("対象サイト", size=(18, 1)), sg.Combo(target, key="combo1", enable_events=True, default_value=target[0])],
        [sg.Text("作品ページURL形式", size=(18, 1)), sg.Text(target_url_example[target[0]], key="work_url_sample", size=(32, 1))],
        [sg.Text("作品ページURL", size=(18, 1)), sg.InputText(key="work_url", default_text="")],
        [sg.Text("保存先パス", size=(18, 1)), sg.InputText(key="save_path", default_text=Path(__file__).parent), sg.FolderBrowse("参照", initial_folder=Path(__file__).parent, pad=((1, 0), (0, 0)))],
        [sg.Text("", size=(18, 1)), sg.Text("", size=(33, 1)), sg.Button("実行", key="run", pad=((7, 2), (0, 0))), sg.Button("終了", key="exit")],
    ]

    # ウィンドウオブジェクトの作成
    window = sg.Window("MediaDownloader", layout, size=(640, 320), finalize=True)
    # window["work_url"].bind("<FocusIn>", "+INPUT FOCUS+")

    # イベントのループ
    while True:
        # イベントの読み込み
        event, values = window.read()
        print(event, values)
        # ウィンドウの×ボタンが押されれば終了
        if event in [sg.WIN_CLOSED, "exit"]:
            break
        if event == "combo1":
            now_value = values["combo1"]
            print(target_url_example[now_value])
            window["work_url_sample"].update(target_url_example[now_value])
        if event == "run":
            work_kind = values["combo1"]
            work_url = values["work_url"]
            save_path = values["save_path"]
            print(work_kind + "_" + work_url + "_" + save_path)

            if work_url == "" or save_path == "":
                continue
            if work_kind not in target:
                continue
            try:
                sp = Path(save_path)
                if not sp.is_dir():
                    sp.mkdir(exist_ok=True, parents=True)
                if not sp.is_dir():
                    continue
            except Exception:
                continue

            LinkSearchMain.LinkSearchMain(work_kind, work_url, save_path)

    # ウィンドウ終了処理
    window.close()
    return 0


if __name__ == "__main__":
    GuiMain()
