import pandas as pd
from pathlib import Path
from tqdm import tqdm
from bs4 import BeautifulSoup
from io import StringIO
import re
import pickle
import chardet

RAWDF_DIR = Path("..","data","rawdf")

def create_results(html_path_list : list[Path],
                   save_dir : Path = RAWDF_DIR,
                   save_filename: str = "results.csv"
                   ) -> pd.DataFrame:
    """
    raceページのHTMLを読み込んで、レース結果テーブルに加工する関数
    引数は基本Pathのみ
    """
    dfs = {}
    for html_path in tqdm(html_path_list):
        with open(html_path, "rb") as f:
            
            race_id = html_path.stem # Pathからrace_idを抽出、bin部分を消している
            response = f.read()
            html = (
                response
                .replace(b"<diary_snap_cut>", b"")
                .replace(b"</diary_snap_cut>", b"")
                )

            # # エンコーディングを自動検出
            # encoding = chardet.detect(response)['encoding']
            # # print(f"検出されたエンコーディング: {encoding}")

            # # 正しいエンコーディングでデコード
            # html = response.decode(encoding)
            # print("html = " + html)
            soup = BeautifulSoup(html, 'html.parser').find(
                "table",class_="race_table_01 nk_tb_common"
            )
            try:
                # レースページのうち、最初の表(レース結果)をdfに追加する
                df = pd.read_html(html)[0]

                # horse_idを追加するコード
                horse_list = soup.find_all("a", href=re.compile(r"^/horse/"))
                # print(horse_list)
                horse_id_list = []

                for a in horse_list:
                    horse_id = re.findall(r"/horse/(\d{10})", a["href"])[0]
                    horse_id_list.append(horse_id)
                df["horse_id"] = horse_id_list

                # jockey_idを追加するコード
                jockey_list = soup.find_all("a", href=re.compile(r"^/jockey/"))
                jockey_id_list = []

                for a in jockey_list:
                    jockey_id = re.findall(r"/jockey/result/recent/(\d{5})", a["href"])[0]
                    jockey_id_list.append(jockey_id)
                df["jockey_id"] = jockey_id_list

                # trainer_idを追加するコード
                trainer_list = soup.find_all("a", href=re.compile(r"^/trainer/"))
                trainer_id_list = []

                for a in trainer_list:
                    trainer_id = re.findall(r"/trainer/result/recent/(\d{5})", a["href"])[0]
                    trainer_id_list.append(trainer_id)
                df["trainer_id"] = trainer_id_list

                # owner_idを追加するコード
                # owner_list = soup.find_all("a", href=re.compile(r"^/owner/"))
                # owner_id_list = []

                # for a in owner_list:
                #     owner_id = re.findall(r"/owner/result/recent/(\d{5})", a["href"])[0]
                #     owner_id_list.append(owner_id)
                # df["owner_id"] = owner_id_list

                df.index = [race_id] * len(df)
                dfs[race_id] = df
            except:
                print(f"tabele not found at {race_id}")
                pass

    concat_df = pd.concat(dfs.values())
    concat_df.index.name = "race_id"
    concat_df.columns = concat_df.columns.str.replace(" ", "")
    concat_df = concat_df.reset_index()
    update_rawdf(concat_df, key = "race_id", save_filename = save_filename)
    return concat_df


def create_horse_results(html_path_list : list[Path],
                save_dir : Path = RAWDF_DIR,
                save_filename: str = "horse_results.csv",
                
                ) -> pd.DataFrame:
    """
    horseページのHTMLを読み込んで、レース結果テーブルに加工する関数
    引数は基本パスのみ
    """
    dfs = {}
    for html_path in tqdm(html_path_list):
        with open(html_path, "rb") as f:
            try:
                horse_id = html_path.stem # Pathからhorse_idを抽出、bin部分を消している

                response = f.read()

                # エンコーディングを自動検出
                encoding = chardet.detect(response)['encoding']
                # print(f"検出されたエンコーディング: {encoding}")

                # 正しいエンコーディングでデコード
                html = response.decode(encoding)
                
                # 先ほどまでBeautifulSoupを使っていたのはhorse_idなどを抜くためである。ここでは必要ない
                
                # レースページのうち、3番目の表(レース結果)をdfに追加する
                # df = pd.read_html(html)[4]
                df = pd.read_html(StringIO(html))[4]

                # コラム数をチェック
                if df.shape[1] < 10:  # 列数が10未満の場合
                    raise ValueError(f"Column count is less than 10 for horse_id: {horse_id}")
                df.index = [horse_id] * len(df)
                dfs[horse_id] = df
            except:
                print(f"table not found at {horse_id}")
                pass
    concat_df = pd.concat(dfs.values())
    concat_df.index.name = "horse_id"
    concat_df.columns = concat_df.columns.str.replace(" ", "")
    save_dir.mkdir(exist_ok=True, parents=True)
    concat_df = concat_df.reset_index()
    update_rawdf(concat_df, key = "horse_id", save_filename = save_filename)
    return concat_df


def create_race_info(
    html_path_list: list[Path],
    save_dir: Path = RAWDF_DIR,
    save_filename: str = "race_info.csv",
    ) -> pd.DataFrame:
    """
    pathのリストを引数とし、指定したパスから開催日時などを読み込む
    加工した表を返す
    """
    dfs = {}
    for html_path in tqdm(html_path_list):
        with open(html_path, "rb") as f:
            try:
                html = f.read()
                soup = BeautifulSoup(html, "lxml").find("div", class_="data_intro")
                info_dict = {}
                info_dict["title"] = soup.find("h1").text
                p_list = soup.find_all("p")
                info_dict["info1"] = re.findall(
                    r"[\w:]+", p_list[0].text.replace(" ", "")
                )
                info_dict["info2"] = re.findall(r"[\w:]+", p_list[1].text)
                df = pd.DataFrame().from_dict(info_dict, orient="index").T

                # ファイル名からrace_idを取得
                race_id = html_path.stem
                df.index = [race_id] * len(df)
                dfs[race_id] = df
            except IndexError as e:
                print(f"table not found at {race_id}")
                continue

    concat_df = pd.concat(dfs.values())
    concat_df.index.name = "race_id"
    concat_df.columns = concat_df.columns.str.replace(" ", "")
    save_dir.mkdir(exist_ok=True, parents=True)
    concat_df = concat_df.reset_index()
    update_rawdf(concat_df, key = "race_id", save_filename = save_filename)
    return concat_df


def create_horse_info(html_path_list : list[Path],
                save_dir : Path = RAWDF_DIR,
                save_filename: str = "horse_info.csv"
                ) -> pd.DataFrame:
    """
    horseページのHTMLを読み込んで、馬の情報テーブルに加工する関数
    引数は基本パスのみ
    """
    # DataFrameに格納する際の列名
    columns = ["芝適正", "距離特性", "逃げ度", "早熟度", "重馬場適正"]
    # テーブルがない場合中間値で補填
    normal = [58,58,58,58,58]

    # 各horse_idについてDataFrameを作成
    data = []
    horse_ids = []

    for html_path in tqdm(html_path_list):
        horse_id = html_path.stem
        with open(html_path, "rb") as f:
            try:
                html = f.read()

                soup = BeautifulSoup(html, "html.parser")

                # すべてのimgタグを検索
                img_tags = soup.find_all("img")

                # `review_bar_blue.png` を含むimgタグを抽出
                target_imgs = [img for img in img_tags if any(keyword in img.get("src", "") for keyword in ["review_bar_blue.png", "review_bar_gray.png"])]

                width_list = []

                # 抽出したimgタグの属性を出力
                for img in target_imgs:
                    # print("Found img tag:")
                    # print("src:", img.get("src"))
                    # print("width:", img.get("width"))
                    # print("height:", img.get("height"))
                    width = img.get("width")
                    width_list.append(width)

                par = [width_list[i] for i in [0, 2, 4, 6, 8] if i < len(width_list)]
                data.append(par)
                horse_ids.append(horse_id)
            except Exception as e:
                print(f"Error processing {horse_id}: {e}")
                data.append(normal)
                horse_ids.append(horse_id)
                continue
    concat_df = pd.DataFrame(data, index=horse_ids, columns=columns)
    concat_df.index.name = "horse_id"
    save_dir.mkdir(exist_ok=True, parents=True)
    concat_df = concat_df.reset_index()
    update_rawdf(concat_df, key = "horse_id", save_filename = save_filename)
    return concat_df




def update_rawdf(
        new_df : pd.DataFrame,
        key : str,
        save_filename : str,
        save_dir : Path = RAWDF_DIR
        ):
    """
    既存のrawdfに新しいデータを追加して保存する関数
    keyに指定したインデックスが同じなら置き換えしない
    """
    if (save_dir / save_filename).exists():
        old_df = pd.read_csv(save_dir / save_filename, sep="\t", dtype={f"{key}" : str})
        # きちんと比較できるよう型を統一
        new_df[f"{key}"] = new_df[f"{key}"].astype(str)
        df = pd.concat([
            old_df[~old_df[f"{key}"].isin(new_df[f"{key}"])],  #既存おデータにいない馬のデータ
            new_df
        ])
        df.to_csv(save_dir / save_filename, sep = "\t", index=False)
    else:
        new_df.to_csv(save_dir / save_filename, sep="\t", index= False)
    # return df