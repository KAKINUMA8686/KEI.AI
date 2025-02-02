from pathlib import Path
import pandas as pd
import chardet
import re
import preprocessing
import json
import time
# import html5lib
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# commonのパス
COMMON_DATA_DIR = Path("..", "..", "common", "data")
POPULATION_DIR_PREDICTION = COMMON_DATA_DIR / "prediction_population"
MAPPING_DIR = COMMON_DATA_DIR / "mapping"
#v3_0_0のパス
DATA_DIR = Path(".." , "data")
INPUT_DIR = DATA_DIR / "01_preprocessed"
OUTPUT_DIR = DATA_DIR / "02_features"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
POPULATION_DIR = DATA_DIR / "00_population"

# マッピングのインポート
with open(MAPPING_DIR / "sex.json", "r") as f:
    sex_mapping = json.load(f)
with open(MAPPING_DIR / "race_type.json", "r") as f:
    race_type_mapping = json.load(f)
with open(MAPPING_DIR / "ground_state.json", "r") as f:
    ground_state_mapping = json.load(f)
with open(MAPPING_DIR / "weather.json", "r") as f:
    weather_mapping = json.load(f)
with open(MAPPING_DIR / "ground_state.json", "r") as f:
    ground_state_mapping = json.load(f)
with open(MAPPING_DIR / "race_class.json", "r") as f:
    race_class_mapping = json.load(f)
with open(MAPPING_DIR / "around.json", "r") as f:
    around_mapping = json.load(f)

def interceptor(request):
    # Block PNG, JPEG and GIF images
    if request.path.endswith(('.png', '.jpg', '.gif')):
        request.abort()


class FeatureCreater:
    def __init__(
            self,
            results_filepath : Path = INPUT_DIR / "results.csv",
            race_info_filepath : Path = INPUT_DIR / "race_info.csv",
            horse_results_filepath : Path = INPUT_DIR / "horse_results.csv",
            horse_info_filepath : Path = INPUT_DIR / "horse_info.csv",
            output_dir : Path = OUTPUT_DIR,
            population_filepath : Path = POPULATION_DIR / "population.csv",
    ):
        self.population = pd.read_csv(population_filepath, sep = "\t")
        self.results = pd.read_csv(results_filepath, sep = "\t")
        self.race_info = pd.read_csv(race_info_filepath, sep = "\t")
        self.horse_results = pd.read_csv(horse_results_filepath, sep = "\t")
        self.horse_info = pd.read_csv(horse_info_filepath, sep="\t")
        self.output_dir = output_dir
        # horse_id, horse_date, rank_furlongsのみのグラフの作成
        self.furlongs = pd.merge(
            self.results, self.race_info, on="race_id", how="inner"
            )[
                [
                "rank_furlongs", 
                "horse_id", 
                "date"]
                ].rename(columns={"date": "date_horse"})
        self.dist = pd.merge(
            self.results, self.horse_info, on = "horse_id"
        )[["horse_id", "race_id", "Distance_Preference", "Front-Running"]]


        dist_std = (
            self.dist
            .groupby("race_id")[["Distance_Preference", "Front-Running"]]
            .std()
            .rename(columns={
                "Distance_Preference": "Distance_Preference_std",
                "Front-Running": "Front-Running_std"
            })
        )

        # 標準偏差を元のDataFrameに結合
        self.dist = pd.merge(self.dist, dist_std, on="race_id", how="left")

        # 各馬のDistance Preferenceとレース全体の平均の差を標準偏差で割る
        self.dist['relative_distance'] = (
            (
            self.dist['Distance_Preference'] - self.dist.groupby('race_id')['Distance_Preference'].transform('mean')
        ) / self.dist['Distance_Preference_std']
        ).fillna(0)

        self.dist['relative_front'] = (
            (
            self.dist['Front-Running'] - self.dist.groupby('race_id')['Front-Running'].transform('mean')
        ) / self.dist['Front-Running_std']
        ).fillna(0)
        

        self.dist = self.dist[["horse_id", "race_id", "relative_distance", "relative_front"]]
        
    def agg_horse_n_races(self, n_races: list[int] = [1, 3, 5, 10, 1000]):
        """
        直近nレースの着順と賞金の平均を算出する関数
        """
        self.grouped_df = (
            self.population.merge(
                self.horse_results, on=["horse_id"], suffixes=("", "_horse")
            )
            .merge(
                self.furlongs, on=["horse_id", "date_horse"], suffixes=("_pop", "_furlongs")
            )
            .query("date > date_horse")
            .sort_values("date_horse", ascending=False)
            .groupby(["race_id", "horse_id"])
        )
        merged_df = self.population.copy()
        
        for n_race in tqdm(n_races):
            df = (
                self.grouped_df.head(n_race)
                .groupby(["race_id", "horse_id"])[["rank", "prize", "rank_diff", "race_class", "rank_furlongs"]]
                .agg(["mean", "median", "max", "min"])
            )
            df.columns = [f"{col}_{stat}_{n_race}races_relative" for col, stat in df.columns]

            df_2 = (
                self.grouped_df.head(n_race)
                .groupby(["race_id", "horse_id"])[["rank", "prize", "rank_diff", "race_class", "rank_furlongs"]]
                .mean()
                .add_suffix(f"_{n_race}races_mean")  # 列名のユニーク化
            )

            relative_df = (df - df.groupby("race_id").mean()) / df.groupby("race_id").std()
            
            merged_df = merged_df.merge(
                relative_df,
                on=["race_id", "horse_id"],
                how="left",
            ).fillna(0)

            merged_df = merged_df.merge(
                df_2,
                on=["race_id", "horse_id"],
                how="left",
            ).fillna(0)

        self.agg_horse_n_races_df = merged_df



    def create_features(self):
        """
        特徴量作成処理を実行し、populationテーブルに全ての特徴量を結合する
        """
        self.agg_horse_n_races()
        features = (
            self.population.merge(self.results, on = ["race_id", "horse_id"])
            .merge(self.dist, on = ["horse_id", "race_id"])
            .merge(self.horse_info, on = ["horse_id"])
            .merge(self.race_info, on=["race_id", "date"])
            .merge(
                self.agg_horse_n_races_df,
                on = ["race_id", "date", "horse_id"],
                how = "left",
            )
            .drop(columns=["Unnamed: 0"], errors="ignore")
        )
        features["month"] = pd.to_datetime(features["date"]).dt.month
        features.to_csv(self.output_dir / "features.csv", sep="\t", index = False)
        # print("反映されてる？")
        return features
    


class PredictionFeatureCreator:
    def __init__(
        self,
        population_dir : Path = POPULATION_DIR_PREDICTION,
        population_filename : str = "population.csv",
        horse_results_dir : Path = INPUT_DIR,
        horse_results_filename : str = "horse_results_prediction.csv",
        horse_info_filepath : Path = INPUT_DIR / "horse_info.csv",
        output_dir : Path = OUTPUT_DIR,
        output_filename : str = "features_prediction.csv",
        results_filepath : Path = INPUT_DIR / "results.csv",
        race_info_filepath : Path = INPUT_DIR / "race_info.csv",
    ):
        self.population = pd.read_csv(population_dir / population_filename, sep="\t")
        self.horse_results = pd.read_csv(horse_results_dir / horse_results_filename, sep="\t")
        self.horse_info = pd.read_csv(horse_info_filepath, sep="\t")
        self.results_furlongs = pd.read_csv(results_filepath, sep = "\t")
        self.race_info = pd.read_csv(race_info_filepath, sep = "\t")
        self.output_dir = output_dir
        self.output_filename = output_filename
        self.htmls = {}
        self.furlongs = pd.merge(
            self.results_furlongs, self.race_info, on="race_id", how="inner"
            )[
                [
                "rank_furlongs", 
                "horse_id", 
                "date"]
                ].rename(columns={"date": "date_horse"})

        


    def agg_horse_n_races(self, n_races: list[int] = [1, 3, 5, 10, 1000]):
        """
        直近nレースの着順と賞金の平均を算出する関数
        """
        self.grouped_df = (
            self.population.merge(
                self.horse_results, on=["horse_id"], suffixes=("", "_horse")
            ).merge(
                self.furlongs, on=["horse_id", "date_horse"], suffixes=("_pop", "_furlongs")
            )
            .query("date > date_horse")
            .sort_values("date_horse", ascending=False)
            .groupby(["race_id", "horse_id"])
        )
        merged_df = self.population.copy()

        for n_race in tqdm(n_races):
            df = (
                self.grouped_df.head(n_race)
                .groupby(["race_id", "horse_id"])[["rank", "prize", "rank_diff", "race_class", "rank_furlongs"]]
                .agg(["mean", "median", "max", "min"])
            )
            df.columns = [f"{col}_{stat}_{n_race}races_relative" for col, stat in df.columns]

            df_2 = (
                self.grouped_df.head(n_race)
                .groupby(["race_id", "horse_id"])[["rank", "prize", "rank_diff", "race_class", "rank_furlongs"]]
                .mean()
                .add_suffix(f"_{n_race}races_mean")  # 列名のユニーク化
            )

            relative_df = (df - df.groupby("race_id").mean()) / df.groupby("race_id").std()
            
            merged_df = merged_df.merge(
                relative_df,
                on=["race_id", "horse_id"],
                how="left",
            ).fillna(0)

            merged_df = merged_df.merge(
                df_2,
                on=["race_id", "horse_id"],
                how="left",
            ).fillna(0)

        self.agg_horse_n_races_df = merged_df




    def fetch_shutuba_table_html(self, race_id : str) -> str:
        """
        レースIDを指定すると出馬表ページのHTMLをスクレイピングする関数
        """
        options = Options()
        # バックグラウンドで実行
        options.add_argument("--headless") 
        # その他のクラッシュ対策
        options.add_argument("--no-sandbox") 
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument('--disable-gpu')  
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-desktop-notifications')
        options.add_argument("--disable-extensions")
        options.add_argument('--lang=ja')
        options.add_argument('--blink-settings=imagesEnabled=false')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--proxy-server="direct://"')
        options.add_argument('--proxy-bypass-list=*')    
        options.add_argument('--start-maximized') 
        driver_path = ChromeDriverManager().install()
        url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
        with webdriver.Chrome(service = Service(driver_path), options = options) as driver:
            driver.implicitly_wait(10)
            driver.request_interceptor = interceptor
            driver.set_page_load_timeout(15)
            try:
                driver.get(url)
            except:
                pass
            self.htmls[race_id] =  driver.page_source



        
    def fetch_results(
            self,
            html : str,
            race_id : str,
            sex_mapping : dict = sex_mapping
            ) -> pd.DataFrame:
        """
        出馬表ページのhtmlを受け取るとレース結果テーブルを取得して、
        学習時と同じ形に加工する関数
        """
        # print('THIS IS HTML')
        # print(html)
        df = pd.read_html(html)[0]
        df.columns = df.columns.get_level_values(1)
        soup = BeautifulSoup(html,"lxml").find("table", class_= "Shutuba_Table")

        horse_list = soup.find_all("a", href=re.compile(r"/horse/"))
        horse_id_list = []

        for a in horse_list:
            horse_id = re.findall(r"/horse/(\d{10})", a["href"])[0]
            horse_id_list.append(horse_id)
        df["horse_id"] = horse_id_list
        df["horse_id"] = df["horse_id"].astype(int)

        # jockey_idを追加するコード
        jockey_list = soup.find_all("a", href=re.compile(r"/jockey/"))
        jockey_id_list = []

        for a in jockey_list:
            jockey_id = re.findall(r"/jockey/result/recent/(\d{5})", a["href"])[0]
            jockey_id_list.append(jockey_id)
        df["jockey_id"] = jockey_id_list
        df["jockey_id"] = df["jockey_id"].astype(int)

        # trainer_idを追加するコード
        trainer_list = soup.find_all("a", href=re.compile(r"/trainer/"))
        trainer_id_list = []

        for a in trainer_list:
            match = re.findall(r"/trainer/result/recent/(\d{5})", a["href"])
            if match:
                trainer_id = match[0]
            else:
                trainer_id = 0
            trainer_id_list.append(trainer_id)
        df["trainer_id"] = trainer_id_list
        df["trainer_id"] = df["trainer_id"].astype(int)

        # "--" が含まれる行を削除、馬が直前で欠場になったらこれが起こる
        df = df[df.iloc[:, 9] != "--"]

        df["wakuban"] = df.iloc[:,0].astype(int)
        df["umaban"] = df.iloc[:, 1].astype(int)
        df["age"] =  df.iloc[:, 4].str[1:].astype(int)
        df["sex"] = df.iloc[:, 4].str[0].map(sex_mapping)
        df["impost"] = df.iloc[:, 5]
        df["tansho_odds"] = df.iloc[:, 9].astype(float)
        df["popularity"] = df.iloc[:, 10].astype(int)
        df["weight"] = df.iloc[:, 8].str.extract(r"(\d+)").astype(int)
        # df["weight"] = pd.to_numeric(df.iloc[:, 8], errors = "coerce")
        df["weight_diff"] = (
            df.iloc[:, 8]
            .str.extract(r"\((.+)\)")
            .fillna(0)
            .replace("前計不", "0")
            .astype(int)
            )
        df["weight_diff"] = pd.to_numeric(df["weight_diff"], errors = "coerce")
        df["race_id"] = int(race_id)

        #データが着順に並んでいることにより学習が阻害されないために、各レースを馬番順にソートする
        df = df.sort_values(["race_id","umaban"])
        # 使う行を選択
        df = df[
            [
                "race_id",
                "horse_id",
                "jockey_id",
                "trainer_id",
                "wakuban",
                "umaban",
                "sex",
                "age",
                "weight",
                "weight_diff",
                "tansho_odds",
                "popularity",
                "impost"
            ]
                ]

        self.results = df
        self.dist = pd.merge(
            self.results, self.horse_info, on = "horse_id"
        )[["horse_id", "race_id", "Distance_Preference", "Front-Running"]]

        # dist_std = (
        #     self.dist
        #     .groupby("race_id")["Distance Preference"]
        #     .std()
        #     .rename("Distance_Preference_std")
        # )
        dist_std = (
            self.dist
            .groupby("race_id")[["Distance_Preference", "Front-Running"]]
            .std()
            .rename(columns={
                "Distance_Preference": "Distance_Preference_std",
                "Front-Running": "Front-Running_std"
            })
        )

        # 標準偏差を元のDataFrameに結合
        self.dist = pd.merge(self.dist, dist_std, on="race_id", how="left")

        self.dist['relative_distance'] = (
            (
            self.dist['Distance_Preference'] - self.dist.groupby('race_id')['Distance_Preference'].transform('mean')
        ) / self.dist['Distance_Preference_std']
        ).fillna(0)

        self.dist['relative_front'] = (
            (
            self.dist['Front-Running'] - self.dist.groupby('race_id')['Front-Running'].transform('mean')
        ) / self.dist['Front-Running_std']
        ).fillna(0)
        
        self.dist = self.dist[["horse_id", "race_id", "relative_distance", "relative_front"]]


    def fetch_race_info(
            self,
            html : str,
            race_id : str,
            race_type_mapping : dict = race_type_mapping,
            weather_mapping : dict = weather_mapping,
            ground_state_mapping : dict = ground_state_mapping,
            race_class_mapping : dict = race_class_mapping,
            around_mapping : dict = around_mapping
            ) -> pd.DataFrame:
        """
        出馬表ページのHTMLを受け取ると
        レース情報テーブルを取得して学習時と同じ形式に前処理する関数
        """
        info_dict = {}
        info_dict["race_id"] = int(race_id)
        soup = BeautifulSoup(html, "lxml").find("div", class_="RaceList_Item02")
        title = soup.find("h1").text.strip()
        divs = soup.find_all("div")
        div1 = divs[0].text.replace(" ", "")
        info1 = re.findall(r"[\w:]+", div1)

        info_dict["race_type"] = race_type_mapping[info1[1][0]]
        # info_dict["around"] = (
        #     around_mapping[info1[2][0]] if info_dict["race_type"] != 2 else None
        # ).fillna(0)
        info_dict["around"] = (
            around_mapping.get(info1[2][0], None) if info_dict["race_type"] != 2 else None
        )

        # None の場合は 0 を代入
        if info_dict["around"] is None:
            info_dict["around"] = 0
        info_dict["course_len"] = int(re.findall(r"\d+", info1[1])[0])
        info_dict["weather"] = weather_mapping[re.findall(r"天候:(\w+)", div1)[0]]
        info_dict["ground_state"] = ground_state_mapping[
            re.findall(r"馬場:(\w+)", div1)[0]
        ]

        # レース階級情報の取得
        regex_race_class = "|".join(race_class_mapping)
        race_class_title = re.findall(regex_race_class, title)
        # タイトルからレース階級情報が取れない場合
        race_class = re.findall(regex_race_class, divs[1].text)
        if len(race_class_title) != 0:
            info_dict["race_class"] = race_class_mapping[race_class_title[0]]
        elif len(race_class) != 0:
            info_dict["race_class"] = race_class_mapping[race_class[0]]
        else:
            info_dict["race_class"] = None

        info_dict["place"] = int(race_id[4:6])
        self.race_info = pd.DataFrame(info_dict, index=[0])


    def create_features(self, race_id, skip_agg_horse : bool = False) -> pd.DataFrame:
        """
        特徴量作成処理を実行し、populationテーブルにすべての特徴量を結合する
        事前にagg_horse_n_racesを実行していたらskip_agg_horse = Trueとしてスキップできる
        """
        # 馬の過去成績集計
        # 先に実行していた場合はスキップできる
        if not skip_agg_horse:
            self.agg_horse_n_races()
        # 各種テーブルの取得
        print("shutuba")
        self.fetch_shutuba_table_html(race_id)
        print("results")
        self.fetch_results(html = self.htmls[race_id], race_id = race_id,)
        print("race_info")
        self.fetch_race_info(html = self.htmls[race_id], race_id = race_id)

        self.features = (
            self.population.merge(self.results, on = ["race_id", "horse_id"])
            .merge(self.dist, on = ["horse_id", "race_id"])
            .merge(self.horse_info, on = ["horse_id"])
            .merge(self.race_info, on=["race_id"])
            .merge(
                self.agg_horse_n_races_df,
                on = ["race_id", "date", "horse_id"],
                how = "left",
            )
            .drop(columns=["Unnamed: 0"], errors="ignore")
        )
        self.features["month"] = pd.to_datetime(self.features["date"]).dt.month
        self.features.to_csv(self.output_dir / self.output_filename, sep="\t", index = False)
        # print("反映されてる？")
        return self.features

