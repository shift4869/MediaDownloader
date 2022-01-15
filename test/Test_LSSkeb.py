# coding: utf-8
import asyncio
import configparser
import random
import shutil
import sys
import unittest
import warnings
from contextlib import ExitStack
from logging import WARNING, getLogger
from mock import MagicMock, AsyncMock, PropertyMock, mock_open, patch
from pathlib import Path
from time import sleep

from bs4 import BeautifulSoup

from MediaDownloader import LSSkeb


logger = getLogger("root")
logger.setLevel(WARNING)


class TestLSSkeb(unittest.TestCase):

    def setUp(self):
        """コンフィグファイルからパスワードを取得する
        """
        CONFIG_FILE_NAME = "./config/config.ini"
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_NAME, encoding="utf8")
        self.twitter_id = config["skeb"]["twitter_id"]
        self.twitter_password = config["skeb"]["twitter_password"]

        self.TEST_BASE_PATH = "./test/PG_Skeb"
        self.TBP = Path(self.TEST_BASE_PATH)

        warnings.simplefilter("ignore", ResourceWarning)

    def tearDown(self):
        """後始末：テスト用ディレクトリを削除する
        """
        # shutil.rmtree()で再帰的に全て削除する ※指定パス注意
        if self.TBP.is_dir():
            shutil.rmtree(self.TBP)

    def __GetSkebData(self, author_name: str, work_id: int, type: str) -> dict:
        """テスト用の情報を作成する

        Args:
            author_name (str): 作者名
            work_id (int): 作品ID (0 < work_id < 99999999)
            type (str): リソースタイプ

        Returns:
            dict: 作品IDで示される作品情報を表す辞書（キーはcolsを参照）
        """
        idstr = str(work_id)
        url = ""
        if type == "illust":
            url = "https://skeb.imgix.net/uploads/origins/xxx?yyy"
        if type == "video":
            url = "https://skeb-production.xx.xxxxx.xxxxxxxxx/uploads/outputs/xxx?yyy"

        cols = ["id", "url", "author_name", "type"]
        data = [idstr, url, author_name, type]
        res = {}
        for c, d in zip(cols, data):
            res[c] = d
        return res

    def __MakePyppeteerMock(self, mock: MagicMock, callback_url, selector_response):
        """Pyppeteerの機能を模倣するモックを作成する
        """
        r_launch = AsyncMock()
        r_np = AsyncMock()

        async def ReturnLaunch(headless):
            async def ReturnNewPage(s):
                def ReturnOn(s, event, f=None):
                    r_on = MagicMock()
                    type(r_on).url = callback_url
                    return f(r_on)

                type(r_np).on = ReturnOn

                async def ReturnQuerySelectorAll(s, selector):
                    return selector_response

                type(r_np).querySelectorAll = ReturnQuerySelectorAll
                return r_np

            type(r_launch).newPage = ReturnNewPage
            return r_launch

        mock.side_effect = ReturnLaunch
        return mock, r_launch, r_np

    def __MakeGetTokenMock(self, mock: MagicMock) -> MagicMock:
        """トークン取得機能のモックを作成する

        Note:
            ID/PWが一致すればOKとする
            対象のmockは "MediaDownloader.LSSkeb.LSSkeb.GetToken" にpatchする

        Returns:
            MagicMock: トークン取得機能のside_effectを持つモック
        """
        def GetTokenSideeffect(twitter_id, twitter_password):
            if self.twitter_id == twitter_id and self.twitter_password == twitter_password:
                token = "ok_token"
                return (token, True)
            else:
                return (None, False)

        mock.side_effect = GetTokenSideeffect
        return mock

    def test_LSSkeb(self):
        """Skebページ処理クラス初期状態チェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("MediaDownloader.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)

            # 正常系
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)
            expect_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"
            }
            self.assertEqual(expect_headers, lssk_cont.headers)
            self.assertEqual("https://skeb.jp/", lssk_cont.top_url)
            self.assertEqual("ok_token", lssk_cont.token)
            self.assertTrue(lssk_cont.auth_success)
            self.assertTrue(self.TEST_BASE_PATH, lssk_cont.base_path)

            # 異常系
            with self.assertRaises(SystemExit):
                lssk_cont = LSSkeb.LSSkeb("invalid twitter_id", "invalid twitter_password", self.TEST_BASE_PATH)

    def test_GetTokenFromOAuth(self):
        """ツイッターログインを行いSkebページで使うtokenを取得する機能をチェック
        """
        with ExitStack() as stack:
            mockle = stack.enter_context(patch.object(logger, "error"))
            mockli = stack.enter_context(patch.object(logger, "info"))
            mockpl = stack.enter_context(patch("pyppeteer.launch"))
            mockgt = stack.enter_context(patch("MediaDownloader.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            # 正常系
            expect = "ok_token"
            callback_url = f"https://skeb.jp/callback?path=/&token={expect}"
            selector_mock = AsyncMock()
            mockpl, r_launch, r_np = self.__MakePyppeteerMock(mockpl, callback_url, [None, selector_mock])
            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(lssk_cont.GetTokenFromOAuth(self.twitter_id, self.twitter_password))
            self.assertEqual(expect, actual)

            # 正常系の呼び出し確認
            expect_newPage_call = [
                "goto",
                "waitForNavigation",
                "content",
                "cookies",
                "waitForNavigation",
                "content",
                "cookies",
                "waitFor",
                "type",
                "waitFor",
                "type",
                "waitFor",
                "click",
                "waitForNavigation",
                "waitForNavigation",
                "content",
                "cookies",
            ]
            self.assertEqual(len(expect_newPage_call), len(r_np.mock_calls))
            for enc, npc in zip(expect_newPage_call, r_np.mock_calls):
                self.assertEqual(enc, npc[0])

            # 異常系
            # コールバックURLがキャッチできなかった
            # ツイッターログインに失敗した場合もこちら
            callback_url = f"https://skeb.jp/invalid_url"
            selector_mock = AsyncMock()
            mockpl, r_launch, r_np = self.__MakePyppeteerMock(mockpl, callback_url, [None, selector_mock])
            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(lssk_cont.GetTokenFromOAuth(self.twitter_id, self.twitter_password))
            self.assertEqual("", actual)

            # ログインボタンセレクト失敗
            expect = "ok_token"
            callback_url = f"https://skeb.jp/callback?path=/&token={expect}"
            mockpl, r_launch, r_np = self.__MakePyppeteerMock(mockpl, callback_url, [None, None])
            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(lssk_cont.GetTokenFromOAuth(self.twitter_id, self.twitter_password))
            self.assertEqual("", actual)
            pass

    def test_GetToken(self):
        """トークン取得機能をチェック
        """
        with ExitStack() as stack:
            # open()をモックに置き換える
            mockfin = mock_open(read_data="ok_token")
            mockfp = stack.enter_context(patch("pathlib.Path.open", mockfin))

            # トークンファイルが存在する場合、一時的にリネームする
            SKEB_TOKEN_PATH = "./config/skeb_token.ini"
            stp_path = Path(SKEB_TOKEN_PATH)
            tmp_path = stp_path.parent / "tmp.ini"
            if stp_path.is_file():
                stp_path.rename(tmp_path)

            # トークンファイルが存在しない場合のテスト
            async def GetTokenFromOAuthMock(twitter_id, twitter_password):
                token = ""
                if self.twitter_id == twitter_id and self.twitter_password == twitter_password:
                    token = "ok_token_from_oauth"
                return token

            mockgtfo = stack.enter_context(patch("MediaDownloader.LSSkeb.LSSkeb.GetTokenFromOAuth"))
            mockgtfo.side_effect = GetTokenFromOAuthMock
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)
            expect_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"
            }
            self.assertEqual(expect_headers, lssk_cont.headers)
            self.assertEqual("https://skeb.jp/", lssk_cont.top_url)
            self.assertEqual("ok_token_from_oauth", lssk_cont.token)
            self.assertTrue(lssk_cont.auth_success)
            self.assertTrue(self.TEST_BASE_PATH, lssk_cont.base_path)

            # 一時的にリネームしていた場合は復元する
            # そうでない場合はダミーのファイルを作っておく
            if tmp_path.is_file():
                tmp_path.rename(stp_path)
            else:
                stp_path.touch()

            # トークンファイルが存在する場合のテスト
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)
            expect_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"
            }
            self.assertEqual(expect_headers, lssk_cont.headers)
            self.assertEqual("https://skeb.jp/", lssk_cont.top_url)
            self.assertEqual("ok_token", lssk_cont.token)
            self.assertTrue(lssk_cont.auth_success)
            self.assertTrue(self.TEST_BASE_PATH, lssk_cont.base_path)

            # ダミーファイルがある場合は削除しておく
            if not tmp_path.is_file() and stp_path.stat().st_size == 0:
                stp_path.unlink()

    def test_MakeCallbackURL(self):
        """コールバックURLを生成する機能をチェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("MediaDownloader.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            # 正常系
            # 通常
            e_top_url = "https://skeb.jp/"
            e_path = "ok_path"
            e_token = "ok_token"
            expect = f"{e_top_url}callback?path=/{e_path}&token={e_token}"
            actual = lssk_cont.MakeCallbackURL(e_path, e_token)
            self.assertEqual(expect, actual)

            # pathの先頭と末尾に"/"が含まれていても処理可能かどうか
            expect = f"{e_top_url}callback?path=/{e_path}&token={e_token}"
            actual = lssk_cont.MakeCallbackURL("/" + e_path, e_token)
            self.assertEqual(expect, actual)
            actual = lssk_cont.MakeCallbackURL("/" + e_path + "/", e_token)
            self.assertEqual(expect, actual)
            actual = lssk_cont.MakeCallbackURL(e_path + "/", e_token)
            self.assertEqual(expect, actual)

            # pathが"/"のみの場合
            expect = f"{e_top_url}callback?path=/&token={e_token}"
            actual = lssk_cont.MakeCallbackURL("/", e_token)
            self.assertEqual(expect, actual)

            # 異常系
            # top_urlが壊れている
            del lssk_cont.top_url
            actual = lssk_cont.MakeCallbackURL(e_path, e_token)
            self.assertEqual("", actual)

    def test_IsValidToken(self):
        """トークンが有効かどうか判定する機能をチェック
        """
        with ExitStack() as stack:
            mocksession = stack.enter_context(patch("MediaDownloader.LSSkeb.HTMLSession"))
            mockgt = stack.enter_context(patch("MediaDownloader.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)

            def ReturnSession():
                response = MagicMock()

                def ReturnGet(s, url, headers):
                    r_get = MagicMock()

                    def ReturnFind(key):
                        r_find = MagicMock()
                        if "ok_token" in url:
                            r_find.attrs = {"href": "/account"}
                            r_find.full_text = "アカウント"
                        else:
                            r_find.attrs = {}
                            r_find.full_text = "無効なページ"

                        return [r_find]

                    r_get.html.find = ReturnFind
                    return r_get

                type(response).get = ReturnGet
                return response

            # 正常系
            # トークン指定あり
            mocksession.side_effect = ReturnSession
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)
            actual = lssk_cont.IsValidToken("ok_token")
            expect = True
            self.assertEqual(expect, actual)

            # トークン指定なし（lssk_cont.tokenが使用される）
            actual = lssk_cont.IsValidToken()
            expect = True
            self.assertEqual(expect, actual)

            # 異常系
            # 不正なトークン
            actual = lssk_cont.IsValidToken("invalid token")
            expect = False
            self.assertEqual(expect, actual)

            # lssk_cont.tokenが存在しない
            del lssk_cont.token
            actual = lssk_cont.IsValidToken()
            expect = False
            self.assertEqual(expect, actual)
            pass

    def test_IsTargetUrl(self):
        """URLがSkebのURLかどうか判定する機能をチェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("MediaDownloader.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            # 正常系
            url_s = "https://skeb.jp/@author_name/works/111"
            self.assertEqual(True, lssk_cont.IsTargetUrl(url_s))

            # 全く関係ないアドレス(Google)
            url_s = "https://www.google.co.jp/"
            self.assertEqual(False, lssk_cont.IsTargetUrl(url_s))

            # 全く関係ないアドレス(pixiv)
            url_s = "https://www.pixiv.net/artworks/11111111"
            self.assertEqual(False, lssk_cont.IsTargetUrl(url_s))

            # httpsでなくhttp
            url_s = "http://skeb.jp/@author_name/works/111"
            self.assertEqual(False, lssk_cont.IsTargetUrl(url_s))

            # プリフィックスエラー
            url_s = "ftp:https://skeb.jp/@author_name/works/111"
            self.assertEqual(False, lssk_cont.IsTargetUrl(url_s))

            # サフィックスエラー
            url_s = "https://skeb.jp/@author_name/works/111?rank=1"
            self.assertEqual(False, lssk_cont.IsTargetUrl(url_s))

    def test_GetUserWorkID(self):
        """Skeb作品ページURLから作者アカウント名と作品idを取得する機能をチェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("MediaDownloader.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            # 正常系
            e_author_name = "author_name"
            e_work_id = random.randint(1, 100)
            url_s = f"https://skeb.jp/@{e_author_name}/works/{e_work_id}"
            actual = lssk_cont.GetUserWorkID(url_s)
            self.assertEqual((e_author_name, e_work_id), actual)

            # 異常系
            # 全く関係ないアドレス(Google)
            url_s = "https://www.google.co.jp/"
            actual = lssk_cont.GetUserWorkID(url_s)
            self.assertEqual(("", -1), actual)

    def test_ConvertWebp(self):
        """webp形式の画像ファイルをpngに変換する機能をチェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("MediaDownloader.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

            # 正常系
            actual = lssk_cont.ConvertWebp

    def test_MakeSaveDirectoryPath(self):
        """保存先ディレクトリパスを生成する機能をチェック
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("MediaDownloader.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)

    def test_DownloadSkeb(self):
        """作品作品をダウンロードする機能をチェック
            実際に非公式pixivAPIを通してDLはしない
        """
        with ExitStack() as stack:
            mockgt = stack.enter_context(patch("MediaDownloader.LSSkeb.LSSkeb.GetToken"))
            mockgt = self.__MakeGetTokenMock(mockgt)
            lssk_cont = LSSkeb.LSSkeb(self.twitter_id, self.twitter_password, self.TEST_BASE_PATH)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
