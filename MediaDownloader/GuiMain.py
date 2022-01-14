# coding: utf-8
import logging.config
from logging import INFO, getLogger
from pathlib import Path

import PySimpleGUI as sg

from MediaDownloader import LinkSearchMain

# 対象サイト
target = ["pixiv pic/manga", "pixiv novel", "nijie", "seiga", "skeb"]


def GuiMain():
    # 対象URL例サンプル
    target_url_example = {
        "pixiv pic/manga": "https://www.pixiv.net/artworks/xxxxxxxx",
        "pixiv novel": "https://www.pixiv.net/novel/show.php?id=xxxxxxxx",
        "nijie": "http://nijie.info/view_popup.php?id=xxxxxx",
        "seiga": "https://seiga.nicovideo.jp/seiga/imxxxxxxx",
        "skeb": "https://skeb.jp/@xxxxxxxx/works/xx",
    }

    # ウィンドウのレイアウト
    layout = [
        [sg.Text("MediaDownloader")],
        [sg.Text("対象サイト", size=(18, 1)), sg.Combo(target, key="-TARGET-", enable_events=True, default_value=target[0])],
        [sg.Text("作品ページURL形式", size=(18, 1)), sg.Text(target_url_example[target[0]], key="-WORK_URL_SAMPLE-", size=(40, 1))],
        [sg.Text("作品ページURL", size=(18, 1)), sg.InputText(key="-WORK_URL-", default_text="")],
        [sg.Text("保存先パス", size=(18, 1)), sg.InputText(key="-SAVE_PATH-", default_text=Path(__file__).parent),
         sg.FolderBrowse("参照", initial_folder=Path(__file__).parent, pad=((3, 0), (0, 0)))],
        [sg.Text("", size=(53, 1)), sg.Button("実行", key="-RUN-", pad=((7, 2), (0, 0))), sg.Button("終了", key="-EXIT-")],
        [sg.Output(key="-OUTPUT-", size=(100, 10))],
    ]

    # ウィンドウオブジェクトの作成
    window = sg.Window("MediaDownloader", layout, size=(640, 320), finalize=True)
    # window["-WORK_URL-"].bind("<FocusIn>", "+INPUT FOCUS+")

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    logger = getLogger("root")
    logger.setLevel(INFO)

    print("---ここにログが表示されます---")

    # イベントのループ
    while True:
        # イベントの読み込み
        event, values = window.read()
        # print(event, values)
        # ウィンドウの×ボタンが押されれば終了
        if event in [sg.WIN_CLOSED, "-EXIT-"]:
            break
        if event == "-TARGET-":
            work_kind = values["-TARGET-"]
            # print(target_url_example[work_kind])
            window["-WORK_URL_SAMPLE-"].update(target_url_example[work_kind])
        if event == "-RUN-":
            work_kind = values["-TARGET-"]
            work_url = values["-WORK_URL-"]
            save_path = values["-SAVE_PATH-"]
            # print(work_kind + "_" + work_url + "_" + save_path)

            res = LinkSearchMain.LinkSearchMain(work_kind, work_url, save_path)
            if res == 0:
                logger.info("Process done: success!")
            else:
                logger.info("Process failed...")

    # ウィンドウ終了処理
    window.close()
    return 0


if __name__ == "__main__":
    GuiMain()
