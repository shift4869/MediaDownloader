import configparser
import logging
import logging.config
import subprocess
from logging import INFO, getLogger
from pathlib import Path

import PySimpleGUI as sg

from media_downloader.link_search.link_searcher import LinkSearcher
from media_downloader.util import Result


def gui_main() -> Result:
    # 対象URL例サンプル
    # target_url_example = {
    #     "pixiv pic/manga": "https://www.pixiv.net/artworks/xxxxxxxx",
    #     "pixiv novel": "https://www.pixiv.net/novel/show.php?id=xxxxxxxx",
    #     "nijie": "http://nijie.info/view_popup.php?id=xxxxxx",
    #     "seiga": "https://seiga.nicovideo.jp/seiga/imxxxxxxx",
    # }

    # configファイルロード
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    if not config.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    save_base_path = Path(__file__).parent
    try:
        save_base_path = Path(config["save_base_path"]["save_base_path"])
    except Exception:
        save_base_path = Path(__file__).parent
    save_base_path.mkdir(parents=True, exist_ok=True)

    # ウィンドウのレイアウト
    layout = [
        [sg.Text("MediaDownloader")],
        [sg.Text("作品ページURL", size=(18, 1)), sg.InputText(key="-WORK_URL-", default_text="")],
        [
            sg.Text("チェック対象", size=(18, 1)),
            sg.Checkbox("pixiv", default=config["pixiv"].getboolean("is_pixiv_trace"), key="-CB_pixiv-"),
            sg.Checkbox("nijie", default=config["nijie"].getboolean("is_nijie_trace"), key="-CB_nijie-"),
            sg.Checkbox(
                "nico_seiga", default=config["nico_seiga"].getboolean("is_seiga_trace"), key="-CB_nico_seiga-"
            ),
        ],
        [
            sg.Text("保存先パス", size=(18, 1)),
            sg.InputText(key="-SAVE_PATH-", default_text=save_base_path),
            sg.FolderBrowse("参照", initial_folder=save_base_path, pad=((3, 0), (0, 0))),
            sg.Button("開く", key="-FOLDER_OPEN-", pad=((7, 2), (0, 0))),
        ],
        [sg.Text("", size=(53, 2)), sg.Button("実行", key="-RUN-", pad=((7, 2), (0, 0)))],
        [
            sg.Multiline(
                key="-OUTPUT-",
                size=(100, 10),
                auto_refresh=True,
                autoscroll=True,
                reroute_stdout=True,
                reroute_stderr=True,
            )
        ],
    ]

    # アイコン画像取得
    ICON_PATH = "./image/icon.png"
    icon_binary = Path(ICON_PATH).read_bytes()

    # ウィンドウオブジェクトの作成
    window = sg.Window("MediaDownloader", layout, icon=icon_binary, size=(640, 320), finalize=True)
    # window["-WORK_URL-"].bind("<FocusIn>", "+INPUT FOCUS+")

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    for name in logging.root.manager.loggerDict:
        # 自分以外のすべてのライブラリのログ出力を抑制
        if "media_downloader" not in name:
            getLogger(name).disabled = True
    logger = getLogger(__name__)
    logger.setLevel(INFO)

    print("---ここにログが表示されます---")

    while True:
        event, values = window.read()
        if event in [sg.WIN_CLOSED, "-EXIT-"]:
            break
        if event == "-RUN-":
            try:
                work_url = values["-WORK_URL-"]
                print("初期化中...")
                config["pixiv"]["is_pixiv_trace"] = "True" if values["-CB_pixiv-"] else "False"
                config["nijie"]["is_nijie_trace"] = "True" if values["-CB_nijie-"] else "False"
                config["nico_seiga"]["is_seiga_trace"] = "True" if values["-CB_nico_seiga-"] else "False"
                link_searcher = LinkSearcher.create(config)
                print("初期化完了！")

                link_searcher.fetch(work_url)
            except Exception:
                logger.info("Process failed...")
            else:
                logger.info("Process done: success!")
        if event == "-FOLDER_OPEN-":
            save_path = values["-SAVE_PATH-"]
            subprocess.Popen(["explorer", save_path], shell=True)

    # ウィンドウ終了処理
    window.close()
    return Result.SUCCESS


if __name__ == "__main__":
    gui_main()
