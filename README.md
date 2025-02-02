# keiba_AI

## 概要
競馬の単勝を予想するpythonコード<br>
commonディレクトリでスクレイピング、HTMLの前処理。<br>
v1_0_2ディレクトリで特徴量csvの作成、学習、予想を行う。<br>
GUIディレクトリのHORSE.pyを実行すればGUI経由で実行することができるが、エラー処理などが不完全なので各ディレクトリ直下のmain.ipynbで一通りの操作を行う。

## インストール
### 実行環境
Python 3.10.16で実行

### 使用ライブラリ
requirements.txtにバージョンごと記載

### インストール方法
$ pip install -r requirements.txt

## ディレクトリ構成
.<br>
├── GUI<br>
│   ├── HORSE.py<br>
│   ├── icon.ico<br>
│   ├── image<br>
│   │   ├── bell_pict.png<br>
│   │   ├── calender_pict.png<br>
│   │   ├── comment_pict.png<br>
│   │   ├── factory_pict.png<br>
│   │   ├── graph_pict.png<br>
│   │   ├── gyakusan.png<br>
│   │   ├── horse_pict.png<br>
│   │   ├── icon.png<br>
│   │   ├── pre_icon.jpg<br>
│   │   ├── predict_pict.png<br>
│   │   ├── process_pict.png<br>
│   │   ├── sankaku.png<br>
│   │   ├── shadow.png<br>
│   │   ├── start_pict.jpg<br>
│   │   ├── start_pict.png<br>
│   │   └── umas_pict.png<br>
│   └── temp_resized_image.png<br>
├── README.md<br>
├── common --どのバージョンでも普遍的に使うデータ(HTML等)とそれをスクレイピングや処理するためのコードを格納するディレクトリ<br>
│   ├── data<br>
│   │   ├── html<br>
│   │   │   ├── horse_java<br>
│   │   │   └── race<br>
│   │   ├── mapping<br>
│   │   │   ├── 1_mapping.ipynb<br>
│   │   │   ├── around.json<br>
│   │   │   ├── ground_state.json<br>
│   │   │   ├── race_class.json<br>
│   │   │   ├── race_type.json<br>
│   │   │   ├── sex.json<br>
│   │   │   └── weather.json<br>
│   │   ├── prediction_population<br>
│   │   │   └── population.csv<br>
│   │   └── rawdf<br>
│   │       ├── horse_info.csv<br>
│   │       ├── horse_results.csv<br>
│   │       ├── horse_results_old.csv<br>
│   │       ├── horse_results_prediction.csv<br>
│   │       ├── race_info.csv<br>
│   │       └── results.csv<br>
│   └── src<br>
│       ├── __pycache__<br>
│       ├── create_prediction_population.py<br>
│       ├── create_rawdf.py<br>
│       ├── dev.ipynb<br>
│       ├── main.ipynb<br>
│       ├── race_id_list.pickle<br>
│       └── scraping.py<br>
├── enshu --仮想環境<br>
│   └── bin<br>
│        ├── Activate.ps1<br>
│        └── activate<br>
├── requirements.txt<br>
└── v1_0_2 --予想のためのディレクトリ<br>
    ├── data<br>
    │   ├── 00_population<br>
    │   │   ├── population.csv<br>
    │   │   └── prediction_population.csv<br>
    │   ├── 01_preprocessed<br>
    │   │   ├── horse_info.csv<br>
    │   │   ├── horse_results.csv<br>
    │   │   ├── horse_results_prediction.csv<br>
    │   │   ├── race_info.csv<br>
    │   │   └── results.csv<br>
    │   ├── 02_features<br>
    │   │   ├── features.csv<br>
    │   │   └── features_prediction.csv<br>
    │   └── 03_models<br>
    │       ├── calibration.pkl<br>
    │       ├── evaluation.csv<br>
    │       ├── importance.png<br>
    │       └── model.pkl<br>
    └── src<br>
        ├── __pycache__<br>
        ├── check_pred.py<br>
        ├── config.yaml<br>
        ├── config_new.yaml<br>
        ├── create_population.py<br>
        ├── dev.ipynb<br>
        ├── feature_engeneering.py<br>
        ├── improve_pred.py<br>
        ├── main.ipynb<br>
        ├── predict.py<br>
        ├── preprocessing.py<br>
        ├── train.py<br>
        └── train_optuna.py<br>


## 使い方
基本的に/commonデイレクトリと/v1_0_2ディレクトリ直下のmain.ipynbで実行を行う。<br>
すでにあるコマンドライン通りに実行すればモデルが完成し、予想までできるようになっている。<br>
以下にそれぞれの実行時のトラブルシューティングを示す。<br>
(2025 2/2現在なし)