# coding: utf-8
from MediaDownloader.LSNicoSeiga import LSNicoSeiga
import configparser
import logging.config
from logging import INFO, getLogger
from pathlib import Path

import PySimpleGUI as sg

from MediaDownloader import GuiMain, LSPixiv, LSPixivNovel, LSNijie, LSNicoSeiga, LSSkeb

logger = getLogger("root")
logger.setLevel(INFO)


def LinkSearchMain(work_kind, work_url, save_path):
    if work_url == "":
        print("作品ページURLが空欄です。")
        return -1
    if save_path == "":
        print("保存先パスが空欄です。")
        return -1
    if work_kind not in GuiMain.target:
        print("対象サイトが不正です。")
        return -1
    try:
        sp = Path(save_path)
        if not sp.is_dir():
            sp.mkdir(exist_ok=True, parents=True)
        if not sp.is_dir():
            print("保存先ディレクトリの作成に失敗しました。")
            return -1
    except Exception:
        print("保存先ディレクトリの作成に失敗しました。")
        return -1

    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    # 仕組み上CoRを使わなくてもwork_kindで判別できるのでCoRは使わず直接派生クラスを呼ぶ
    lsb = None
    if work_kind == "pixiv pic/manga" and config["pixiv"]["is_pixiv_trace"]:
        username = config["pixiv"]["username"]
        password = config["pixiv"]["password"]
        lsb = LSPixiv.LSPixiv(username, password, save_path)
    if work_kind == "pixiv novel" and config["pixiv"]["is_pixiv_trace"]:
        username = config["pixiv"]["username"]
        password = config["pixiv"]["password"]
        lsb = LSPixivNovel.LSPixivNovel(username, password, save_path)
    elif work_kind == "nijie" and config["nijie"]["is_nijie_trace"]:
        email = config["nijie"]["email"]
        password = config["nijie"]["password"]
        lsb = LSNijie.LSNijie(email, password, save_path)
    elif work_kind == "seiga" and config["nico_seiga"]["is_seiga_trace"]:
        email = config["nico_seiga"]["email"]
        password = config["nico_seiga"]["password"]
        lsb = LSNicoSeiga.LSNicoSeiga(email, password, save_path)
    elif work_kind == "skeb" and config["skeb"]["is_skeb_trace"]:
        twitter_id = config["skeb"]["twitter_id"]
        twitter_password = config["skeb"]["twitter_password"]
        lsb = LSSkeb.LSSkeb(twitter_id, twitter_password, save_path)
    else:
        pass

    res = -1
    if lsb and lsb.IsTargetUrl(work_url):
        res = lsb.Process(work_url)
    return res


if __name__ == "__main__":
    GuiMain.GuiMain()
    pass
