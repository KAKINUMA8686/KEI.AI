import pandas as pd
from pathlib import Path
import json

COMMON_DATA_DIR = Path("..","..","common","data")
RAWDF_DIR = COMMON_DATA_DIR / "rawdf"
MAPPING_DIR = COMMON_DATA_DIR / "mapping"
INPUT_DIR = COMMON_DATA_DIR / "rawdf"
OUTPUT_DIR = Path("..", "data", "01_preprocessed")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
POPULATION_DIR = Path("..", "data", "00_population")

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



def process_results(
        population_dir : Path = POPULATION_DIR,
        population_filename : str = "population.csv", 
        input_dir : Path = INPUT_DIR,
        output_dir : Path = OUTPUT_DIR,
        save_filename: str = "results.csv",
        sex_mapping : dict = None
        ) -> pd.DataFrame :
    """"
    レース結果テーブルをinput_dirから読み込み、output_dirに出力する。
    レース結果テーブルの各変量の変換を行い、機械学習に入れることのできる表へ加工する。
    v3_0_0とは異なり、上がりハロンのタイムランキングも読み込んでいる
    """
    # population = pd.read_csv(population_dir / population_filename, sep = "\t")
    # df = pd.read_csv(INPUT_DIR / "results.csv", sep = "\t").query(
    #     "race_id in @population['race_id']"
    # )
    df = pd.read_csv(INPUT_DIR / "results.csv", sep = "\t")
    # 表のトリミング、処理
    df["rank"] = pd.to_numeric(df["着順"], errors = "coerce")
    df.dropna(subset=["rank"], inplace=True) # 欠損値の部分を消してくれる
    df["rank"] = df["rank"].astype(int)
    df["wakuban"] = df["枠番"].astype(int)
    df["umaban"] = df["馬番"].astype(int)
    sex_mapping = {"牡" : 0,"牝" : 1, "セ" : 2}
    df["age"] =  df["性齢"].str[1:].astype(int)
    df["sex"] = df["性齢"].str[0].map(sex_mapping)
    df["impost"] = df["斤量"]
    df["tansho_odds"] = df["単勝"].astype(float)
    df["popularity"] = df["人気"].astype(int)
    df["weight"] = df["馬体重"].str.extract(r"(\d+)").astype(int)
    df["weight"] = pd.to_numeric(df["weight"], errors = "coerce")
    df["weight_diff"] = df["馬体重"].str.extract(r"\((.+)\)").astype(int)
    df["weight_diff"] = pd.to_numeric(df["weight_diff"], errors = "coerce")
    df["rank_furlongs"] = df.groupby("race_id")["上り"].rank(ascending=True, method="min")
    df["time"] = pd.to_datetime(df["タイム"], format = "%M:%S.%f")
    df["time"] = (
        df["time"].dt.minute * 60 + df["time"].dt.second + df["time"].dt.microsecond / 1E6
    )
    df["time_rank"] = df.groupby("race_id")["time"].rank(method="min")
    #データが着順に並んでいることにより学習が阻害されないために、各レースを馬番順にソートする
    df = df.sort_values(["race_id","umaban"])
    # 使う行を選択
    df = df[
        [
            "race_id",
             "horse_id",
             "jockey_id",
             "trainer_id",
             "rank_furlongs",
             "rank",
             "wakuban",
             "umaban",
             "sex",
             "age",
             "weight",
             "weight_diff",
             "tansho_odds",
             "popularity",
             "impost",
             "time",
             "time_rank"
        ]
             ]
    df.to_csv(output_dir / save_filename, sep="\t")
    return df


def process_horse_results(
        population_dir : Path = POPULATION_DIR,
        population_filename : str = "population.csv", 
        input_dir : Path = INPUT_DIR,
        output_dir : Path = OUTPUT_DIR,
        save_filename: str = "horse_results.csv",
        input_filename : str = "horse_results.csv",
        race_type_mapping : dict = race_type_mapping,
        weather_mapping : dict = weather_mapping,
        ground_state_mapping : dict = ground_state_mapping,
        race_class_mapping : dict = race_class_mapping
        ) -> pd.DataFrame :
    
    """
    rawdfを読み込んでmappingを通し、使える状態に表を保存
    """
    population = pd.read_csv(population_dir / population_filename, sep = "\t")
    df = pd.read_csv(input_dir / input_filename, sep = "\t").query(
        "horse_id in @population['horse_id']"
    )

    # 表のトリミング、処理
    df["rank"] = pd.to_numeric(df["着順"], errors="coerce").fillna(8)
    # df.dropna(subset=["rank"], inplace=True)
    df["date"] = pd.to_datetime(df["日付"])
    df["weather"] = df["天気"].map(weather_mapping)
    df["race_type"] = df["距離"].str[0].map(race_type_mapping)
    df["course_len"] = df["距離"].str.extract(r"(\d+)").fillna(1800).astype(int)
    df["ground_state"] = df["馬場"].map(ground_state_mapping)
    df["rank_diff"] = df["着差"].map(lambda x :0 if x < 0 else x).fillna(0)
    df["prize"] = df["賞金"].fillna(0)
    regex_race_class = "|".join(race_class_mapping.keys())
    df["race_class"] = (
        df["レース名"].str.extract(rf"({regex_race_class})")[0].map(race_class_mapping).fillna(4)
    )
    df.rename(columns={"頭数": "n_horses"}, inplace=True)
    # 使用する列を選択
    df = df[
        [
            "horse_id",
            "date",
            "rank",
            "prize",
            "rank_diff",
            "weather",
            "race_type",
            "course_len",
            "ground_state",
            "race_class",
            "n_horses",
        ]
            ]
    # レースの規模が特定できない場合は行ごと取り除く
    # この処理はいらないのかも、場合によっては消す
    # df = df.dropna(subset=["race_class"]).reset_index(drop=True) # drop = Trueとすることで削除された行を埋め合わせする
    df.to_csv(output_dir / save_filename, sep="\t")
    return df



def process_race_info(
        # population_dir : Path = POPULATION_DIR,
        # population_filename : str = "population.csv", 
        input_dir : Path = RAWDF_DIR,
        output_dir : Path = OUTPUT_DIR,
        save_filename: str = "race_info.csv",
        race_type_mapping : dict = race_type_mapping,
        weather_mapping : dict = weather_mapping,
        ground_state_mapping : dict = ground_state_mapping,
        race_class_mapping : dict = race_class_mapping,
        around_mapping :dict = around_mapping,
) -> pd.DataFrame :
    """
    未加工のデータフレームをinput_dirから読み込み新しく整えたフレームを作る。
    output_dirに保存する関数
    """
    # population = pd.read_csv(population_dir / population_filename, sep = "\t")
    # df = pd.read_csv(input_dir / "race_info.csv", sep = "\t").query(
    #     "race_id in @population['race_id']"
    # )
    df = pd.read_csv(input_dir / "race_info.csv", sep = "\t")
    df["info1_0"] = df["info1"].map(lambda x : eval(x)[0])
    df["race_type"] =  df["info1_0"].str[0].map(race_type_mapping)
    df["around"] = df["info1_0"].str[1].map(around_mapping).fillna(1)
    df["course_len"] = df["info1_0"].str.extract(r"(\d+)")
    df["weather"] = df["info1"].str.extract(r"天候:(\w+)")[0].map(weather_mapping)
    df["ground_state"] = df["info1"].str.extract(r"(芝|ダート|障害):(\w+)")[1].map(ground_state_mapping)
    df["date"] = pd.to_datetime(
        df["info2"].map(lambda x: eval(x)[0]),format="%Y年%m月%d日"
        )
    regex_race_class = "|".join(race_class_mapping)
    df["race_class"] = (
        df["title"].str.extract(
        rf"({regex_race_class})")
        # タイトルから何も受け取れなかった場合info2から取得する
        .fillna(df["info2"].str.extract(rf"({regex_race_class})"))[0]
        .map(race_class_mapping)
        )
    df["place"] = df["race_id"].astype(str).str[4:6].astype(int)
    df = df[
        [
            "race_id",
            "date",
            "race_type",
            "around",
            "course_len",
            "weather",
            "ground_state",
            "race_class",
            "place",
        ]
    ]
    df.to_csv(output_dir / save_filename, sep="\t", index=False)
    return df

    

def process_horse_info(
        input_dir : Path = RAWDF_DIR,
        output_dir : Path = OUTPUT_DIR,
        save_filename: str = "horse_info.csv",      
) -> pd.DataFrame :
    """
    未加工の馬情報データフレームを読み込み、整えたフレームを作成する(コラム名かえるだけ)
    out_put_dirに保存する関数。
    """
    df = pd.read_csv(input_dir / "horse_info.csv", sep= "\t")
    df["Turf_Suitability"] = df["芝適正"]
    df["Distance_Preference"] = df["距離特性"]
    df["Front-Running"] = df["逃げ度"]
    df["Early_Maturity"] = df["早熟度"]
    df["Heavy_Track"] = df["重馬場適正"]
    df = df[
        [
            "horse_id",
            "Turf_Suitability",
            "Distance_Preference",
            "Front-Running",
            "Early_Maturity",
            "Heavy_Track",
        ]
    ]
    df.to_csv(output_dir / save_filename, sep="\t", index=False)
    return df