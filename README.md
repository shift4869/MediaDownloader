# MediaDownloader


## 概要
特定の画像投稿サイトから作品を取得するダウンローダ。  
PySimpleGUIを使用してGUIでの操作を前提とする。


## 特徴（できること）
- 以下のサイトに対応している
    - pixiv（一枚絵、漫画、うごイラ）  
    - pixiv（小説）  
    - nijie（一枚絵、複数形式）  
    - ニコニコ静画（一枚絵）  

- サンプルURLは以下の形式
```
"pixiv pic/manga": "https://www.pixiv.net/artworks/xxxxxxxx",
"pixiv novel": "https://www.pixiv.net/novel/show.php?id=xxxxxxxx",
"nijie": "http://nijie.info/view_popup.php?id=xxxxxx",
"seiga": "https://seiga.nicovideo.jp/seiga/imxxxxxxx",
```


## 前提として必要なもの
- Pythonの実行環境(3.9以上)
- 取得したい投稿サイトのアカウント情報


## 使い方
1. config_example.iniを確認して使用するアカウント情報を記載してconfig.iniにリネーム
1. python MediaDownloader.py
1. GUIに従って対象サイト・作品URL・保存先を入力して実行


## License/Author
GNU Lesser General Public License v3.0（PySimpleGUIを使っている）  
Copyright (c) 2021 [shift](https://twitter.com/_shift4869)  


