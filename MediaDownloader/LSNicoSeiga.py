# coding: utf-8
import configparser
import logging.config
import re
from logging import INFO, getLogger
from pathlib import Path
from time import sleep
import bs4

import emoji
import requests
from bs4 import BeautifulSoup

from MediaDownloader import LinkSearchBase

logger = getLogger("root")
logger.setLevel(INFO)


class LSNicoSeiga(LinkSearchBase.LinkSearchBase):
    def __init__(self, email: str, password: str, base_path: str):
        """ニコニコ静画から画像を取得するためのクラス

        Notes:
            ニコニコ静画の漫画機能には対応していない

        Args:
            base_path (str): 保存先ディレクトリのベースとなるパス

        Attributes:
            base_path (str): 保存先ディレクトリのベースとなるパス
        """
        super().__init__()
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}
        self.email = email
        self.password = password
        self.base_path = base_path

    def IsTargetUrl(self, url: str) -> bool:
        """URLがニコニコ静画のURLかどうか判定する

        Note:
            想定URL形式：https://seiga.nicovideo.jp/seiga/im*******

        Args:
            url (str): 判定対象url

        Returns:
            boolean: ニコニコ静画作品ページURLならTrue、そうでなければFalse
        """
        pattern = r"^https://seiga.nicovideo.jp/seiga/(im)[0-9]+$"
        regex = re.compile(pattern)
        return not (regex.findall(url) == [])

    def GetIllustId(self, url: str) -> int:
        """ニコニコ静画作品ページURLからイラストIDを取得する

        Args:
            url (str): ニコニコ静画作品ページURL

        Returns:
            int: 成功時 イラストID、失敗時 -1
        """
        if not self.IsTargetUrl(url):
            return -1

        tail = Path(url).name
        if tail[:2] != "im":
            return -1

        illust_id = int(tail[2:])
        return illust_id

    def DownloadIllusts(self, url: str, base_path: str) -> int:
        """ニコニコ静画作品ページURLからダウンロードする

        Notes:
            静画画像実体（リダイレクト先）
            http://seiga.nicovideo.jp/image/source?id={illust_id}
            静画情報（xml）
            http://seiga.nicovideo.jp/api/illust/info?id={illust_id}
            ユーザーネーム取得（xml）※user_idは静画情報に含まれる
            https://seiga.nicovideo.jp/api/user/info?id={user_id}

        Args:
            url (str): ニコニコ静画作品ページURL
            base_path (str): 保存先ディレクトリのベースとなるパス

        Returns:
            int: DL成功時0、スキップされた場合1、エラー時-1
        """
        NS_LOGIN_ENDPOINT = "https://account.nicovideo.jp/login"
        NS_LOGIN_REDIRECTOR = "https://account.nicovideo.jp/api/v1/login?show_button_twitter=1&site=niconico&show_button_facebook=1&next_url=&mail_or_tel=1"
        NS_IMAGE_SOUECE_API_ENDPOINT = "http://seiga.nicovideo.jp/image/source?id="
        NS_IMAGE_INFO_API_ENDPOINT = "http://seiga.nicovideo.jp/api/illust/info?id="
        NS_USERNAME_API_ENDPOINT = "https://seiga.nicovideo.jp/api/user/info?id="

        author_name = ""
        author_id = ""
        illust_title = ""
        illust_id = self.GetIllustId(url)

        # セッション開始
        session = requests.session()
        params = {
            "mail_tel": self.email,
            "password": self.password,
        }
        # ログインする
        response = session.post(NS_LOGIN_REDIRECTOR, data=params, headers=self.headers)
        response.raise_for_status()

        # 静画情報を取得する
        info_url = NS_IMAGE_INFO_API_ENDPOINT + str(illust_id)
        response = session.get(info_url, headers=self.headers)
        response.raise_for_status()

        # 静画情報解析
        soup = BeautifulSoup(response.text, "lxml-xml")
        xml_image = soup.find("image")
        author_id = xml_image.find("user_id").text
        illust_title = xml_image.find("title").text

        # 作者情報を取得する
        username_info_url = NS_USERNAME_API_ENDPOINT + str(author_id)
        response = session.get(username_info_url, headers=self.headers)
        response.raise_for_status()

        # 作者情報解析
        soup = BeautifulSoup(response.text, "lxml-xml")
        xml_user = soup.find("user")
        author_name = xml_user.find("nickname").text

        # パスに使えない文字をサニタイズする
        # TODO::サニタイズを厳密に行う
        regex = re.compile(r'[\\/:*?"<>|]')
        author_name = regex.sub("", author_name)
        author_name = emoji.get_emoji_regexp().sub("", author_name)
        author_id = int(author_id)
        illust_title = regex.sub("", illust_title)
        illust_title = emoji.get_emoji_regexp().sub("", illust_title)

        # 画像保存先パスを取得
        save_directory_path = self.MakeSaveDirectoryPath(author_name, author_id, illust_title, illust_id, base_path)
        sd_path = Path(save_directory_path)
        if save_directory_path == "":
            return -1

        # ニコニコ静画ページ取得（画像表示部分のみ）
        source_page_url = NS_IMAGE_SOUECE_API_ENDPOINT + str(illust_id)
        response = session.get(source_page_url, headers=self.headers)
        response.raise_for_status()

        # ニコニコ静画ページ解析して画像直リンクを取得する → source_url
        soup = BeautifulSoup(response.text, "html.parser")
        div_contents = soup.find_all("div", id="content")
        source_url = ""
        for div_content in div_contents:
            div_illust = div_content.find(class_="illust_view_big")
            source_url = div_illust.get("data-src")
            break

        if source_url == "":
            return -1
        
        # {作者名}ディレクトリ作成
        sd_path.parent.mkdir(parents=True, exist_ok=True)

        # ファイル名設定
        ext = ".jpg"
        name = "{}{}".format(sd_path.name, ext)

        # 既に存在しているなら再DLしないでスキップ
        if (sd_path.parent / name).is_file():
            logger.info("Download seiga illust: " + name + " -> exist")
            return 1

        # 画像保存
        response = session.get(source_url, headers=self.headers)
        response.raise_for_status()

        # {作者名}ディレクトリ直下に保存
        with Path(sd_path.parent / name).open(mode="wb") as fout:
            fout.write(response.content)
        logger.info("Download seiga illust: " + name + " -> done")

        return 0

    def MakeSaveDirectoryPath(self, author_name: str, author_id: int, illust_title: str, illust_id: int, base_path: str) -> str:
        """保存先ディレクトリパスを生成する

        Notes:
            保存先ディレクトリパスの形式は以下とする
            ./{作者名}({作者ID})/{イラストタイトル}({イラストID})/
            既に{作者ID}が一致するディレクトリがある場合はそのディレクトリを使用する
            （{作者名}変更に対応するため）

        Args:
            author_name (str): 作者名
            author_id (int): 作者ID
            illust_title (str): 作品名
            illust_id (int): 作者ID
            base_path (str): 保存先ディレクトリのベースとなるパス

        Returns:
            str: 成功時 保存先ディレクトリパス、失敗時 空文字列
        """
        if author_name == "" or author_id == -1 or illust_title == "" or illust_id == "":
            return ""

        # 既に{作者nijieID}が一致するディレクトリがあるか調べる
        IS_SEARCH_AUTHOR_ID = True
        sd_path = ""
        save_path = Path(base_path)
        if IS_SEARCH_AUTHOR_ID:
            filelist = []
            filelist_tp = [(sp.stat().st_mtime, sp.name) for sp in save_path.glob("*") if sp.is_dir()]
            for mtime, path in sorted(filelist_tp, reverse=True):
                filelist.append(path)

            regex = re.compile(r'.*\(([0-9]*)\)$')
            for dir_name in filelist:
                result = regex.match(dir_name)
                if result:
                    ai = result.group(1)
                    if ai == str(author_id):
                        sd_path = "./{}/{}({})/".format(dir_name, illust_title, illust_id)
                        break

        if sd_path == "":
            sd_path = "./{}({})/{}({})/".format(author_name, author_id, illust_title, illust_id)

        save_directory_path = save_path / sd_path
        return str(save_directory_path)

    def Process(self, url: str) -> int:
        res = self.DownloadIllusts(url, self.base_path)
        return 0 if (res in [0, 1]) else -1


if __name__ == "__main__":
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    if config["nico_seiga"].getboolean("is_seiga_trace"):
        ns_cont = LSNicoSeiga(config["nico_seiga"]["email"], config["nico_seiga"]["password"], config["nico_seiga"]["save_base_path"])
        work_url = "https://seiga.nicovideo.jp/seiga/im5360137"
        res = ns_cont.Process(work_url)
    pass