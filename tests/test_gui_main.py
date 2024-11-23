import configparser
import sys
import unittest
from collections import namedtuple
from pathlib import Path

import TkEasyGUI as sg
from mock import call, patch

from media_downloader.gui_main import gui_main
from media_downloader.util import Result


class TestGuiMain(unittest.TestCase):
    def _check_layout(self, e, a):
        """sgオブジェクトは別IDで生成されるため、各要素を比較する"""
        # typeチェック
        self.assertEqual(type(e), type(a))
        # リストならば再起
        if isinstance(e, list) and isinstance(a, list):
            self.assertEqual(len(e), len(a))
            for e1, a1 in zip(e, a):
                self._check_layout(e1, a1)
        else:
            # 要素チェック
            match e, a:
                case (sg.Text(), sg.Text()):
                    self.assertEqual(e.get(), a.get())
                case (sg.InputText(), sg.InputText()):
                    self.assertEqual(e.key, a.key)
                case (sg.Button(), sg.Button()):
                    self.assertEqual(e.get(), a.get())
                    self.assertEqual(e.key, a.key)
                case (sg.Checkbox(), sg.Checkbox()):
                    self.assertEqual(e.key, a.key)
                case (sg.FolderBrowse(), sg.FolderBrowse()):
                    pass
                case (sg.Multiline(), sg.Multiline()):
                    self.assertEqual(e.get(), a.get())
                    self.assertEqual(e.key, a.key)
                case _:
                    raise ValueError(e, a)

    def _make_layout(self, config: configparser.ConfigParser, save_base_path: Path) -> list[list]:
        layout = [
            [sg.Text("MediaDownloader")],
            [
                sg.Text("作品ページURL", size=(18, 1)),
                sg.InputText(key="-WORK_URL-", default_text="", size=(61, 1)),
                sg.Button("実行", key="-RUN-"),
            ],
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
                sg.InputText(key="-SAVE_PATH-", default_text=save_base_path, size=(61, 1)),
                sg.FolderBrowse("参照", initial_folder=save_base_path),
                sg.Button("開く", key="-FOLDER_OPEN-", pad=((7, 2), (0, 0))),
            ],
            [sg.Text("", size=(70, 2))],
            [
                sg.Multiline(
                    key="-OUTPUT-",
                    size=(100, 10),
                    readonly=True,
                    autoscroll=True,
                )
            ],
        ]
        return layout

    def test_gui_main(self):
        CONFIG_FILE_NAME = "./config/config.ini"
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_NAME, encoding="utf8")
        save_base_path = Path(config["save_base_path"]["save_base_path"])
        layout = self._make_layout(config, save_base_path)

        ICON_PATH = "./image/icon.png"
        icon_binary = Path(ICON_PATH).read_bytes()

        mock_print = self.enterContext(patch("media_downloader.gui_main.print"))
        mock_config = self.enterContext(patch("media_downloader.gui_main.configparser.ConfigParser"))
        mock_logging = self.enterContext(patch("media_downloader.gui_main.logging"))
        mock_logger = self.enterContext(patch("media_downloader.gui_main.getLogger"))
        mock_window = self.enterContext(patch("media_downloader.gui_main.sg.Window"))
        mock_link_searcher = self.enterContext(patch("media_downloader.gui_main.LinkSearcher.create"))
        mock_subprocess = self.enterContext(patch("media_downloader.gui_main.subprocess"))

        mock_logging.config.fileConfig.side_effect = lambda f, disable_existing_loggers: True
        mock_logging.root.manager.loggerDict = ["media_downloader", ""]

        def pre_rum(is_valid_config, is_valid_save_path, event):
            mock_config.reset_mock()
            mock_config.return_value.read.side_effect = lambda f, encoding: is_valid_config

            def f(key):
                if not is_valid_save_path and key == "save_base_path":
                    raise ValueError
                return config[key]

            mock_config.return_value.__getitem__.side_effect = f

            mock_window.reset_mock()
            mock_window.return_value.read.side_effect = event

            mock_link_searcher.reset_mock()
            mock_subprocess.reset_mock()
            pass

        def post_rum(is_valid_config, is_valid_save_path, event):
            if not is_valid_config:
                self.assertEqual(
                    [
                        call(),
                        call().read(CONFIG_FILE_NAME, encoding="utf8"),
                    ],
                    mock_config.mock_calls,
                )
                mock_window.assert_not_called()
                mock_link_searcher.assert_not_called()
                mock_subprocess.assert_not_called()
                return

            event_keys = [ele[0] for ele in event]
            expect_call_config = [
                call(),
                call().read(CONFIG_FILE_NAME, encoding="utf8"),
                call().__getitem__("save_base_path"),
                call().__getitem__("pixiv"),
                call().__getitem__("nijie"),
                call().__getitem__("nico_seiga"),
            ]

            actual_layout = mock_window.mock_calls[0][1][1]
            self._check_layout(layout, actual_layout)
            expect_call_window = [call().read()] * len(event)
            expect_call_window.append(call().close())
            self.assertEqual(expect_call_window, mock_window.mock_calls[1:])

            if "-RUN-" in event_keys:
                s_values = [ele[1] for ele in event if ele[0] == "-RUN-"][0]
                if "-WORK_URL-" in s_values:
                    work_url = s_values["-WORK_URL-"]
                    expect_call_config.extend([
                        call().__getitem__("pixiv"),
                        call().__getitem__("nijie"),
                        call().__getitem__("nico_seiga"),
                    ])
                    self.assertEqual(
                        [
                            call(mock_config.return_value),
                            call().fetch(work_url),
                        ],
                        mock_link_searcher.mock_calls,
                    )
                else:
                    mock_link_searcher.assert_not_called()
            if "-FOLDER_OPEN-" in event_keys:
                s_values = [ele[1] for ele in event if ele[0] == "-FOLDER_OPEN-"][0]
                save_path = s_values["-SAVE_PATH-"]
                self.assertEqual(
                    [call.Popen(["explorer", save_path], shell=True)],
                    mock_subprocess.mock_calls,
                )

            self.assertEqual(expect_call_config, mock_config.mock_calls)
            pass

        run_values = {
            "-WORK_URL-": "work_url",
            "-CB_pixiv-": True,
            "-CB_nijie-": True,
            "-CB_nico_seiga-": True,
        }
        error_run_values = {}
        folder_values = {
            "-SAVE_PATH-": "save_path",
        }
        Params = namedtuple("Params", ["is_valid_config", "is_valid_save_path", "event", "result"])
        params_list = [
            Params(True, True, [("-EXIT-", {})], Result.SUCCESS),
            Params(True, True, [("-RUN-", run_values), ("-EXIT-", {})], Result.SUCCESS),
            Params(True, True, [("-FOLDER_OPEN-", folder_values), ("-EXIT-", {})], Result.SUCCESS),
            Params(True, True, [("-RUN-", error_run_values), ("-EXIT-", {})], Result.SUCCESS),
            Params(True, False, [("-EXIT-", {})], Result.SUCCESS),
            Params(False, True, [("-EXIT-", {})], IOError),
        ]
        for params in params_list:
            pre_rum(*params[:-1])
            expect = params[-1]
            if expect == Result.SUCCESS:
                actual = gui_main()
                self.assertEqual(expect, actual)
            else:
                with self.assertRaises(expect):
                    actual = gui_main()
            post_rum(*params[:-1])


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
