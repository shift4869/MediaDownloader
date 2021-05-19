# coding: utf-8
import configparser
import logging.config
from logging import INFO, getLogger
from pathlib import Path

from MediaDownloader import LSPixiv, LSNijie

logger = getLogger("root")
logger.setLevel(INFO)


def LinkSearchMain(work_kind, work_url, save_path):
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    # 仕組み上CoRを使わなくてもwork_kindで判別できるのでCoRは使わず直接派生クラスを呼ぶ
    lsb = None
    if work_kind == "pixiv" and config["pixiv"]["is_pixiv_trace"]:
        username = config["pixiv"]["username"]
        password = config["pixiv"]["password"]
        lsb = LSPixiv.LSPixiv(username, password, save_path)
    elif work_kind == "nijie" and config["nijie"]["is_pixiv_trace"]:
        email = config["nijie"]["email"]
        password = config["nijie"]["password"]
        lsb = LSNijie.LSNijie(email, password, save_path)
    else:
        pass

    res = -1
    if lsb and lsb.IsTargetUrl(work_url):
        res = lsb.Process(work_url)
    return res


if __name__ == "__main__":
    pass
