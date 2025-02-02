import pandas as pd
from pathlib import Path
import yaml
import lightgbm as lgb
import matplotlib.pyplot as plt
import pickle
import numpy as np
from sklearn.metrics import log_loss
from sklearn.isotonic import IsotonicRegression

DATA_DIR = Path("..", "data")
INPUT_DIR = DATA_DIR / "02_features"
OUTPUT_DIR = DATA_DIR / "03_models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def exp_con(x):
    """
    指数関数、xの係数が大きいほど引数の大小が返り値の反映される
    """
    return (np.exp(12 * x) - 1) / (np.exp(12) - 1)

class Trainer:
    def __init__(
        self,
        features_filepath: Path = INPUT_DIR / "features.csv",
        config_filepath: Path = "config.yaml",
        output_dir : Path = OUTPUT_DIR,
    ):
        self.features = pd.read_csv(features_filepath, sep = "\t")
        with open(config_filepath) as f:
            self.feature_cols = yaml.safe_load(f)["features"]
        self.output_dir = output_dir # self.~は()外で一度定義しなくては使えない

    def create_dataset(self, test_start_date : str):
        """
        学習データ、テストデータを作成する
        test_start_dateをyyyy-mm-dd形式で指定すると、その日以前を学習データ、以降をテストデータとする
        """
        #目的変数
        # 1位の場合を評価
        self.features["target"] = (self.features["rank"] == 1).astype(int)
        # 学習データとテストデータに分類
        self.train_df = self.features.query("date < @test_start_date") # 変数はアットマークから入れる
        self.test_df = self.features.query("date >= @test_start_date")

    def create_dataset_mod(self,
                           test_start_date : str = "2024-01-01",
                           valid_start_date : str = "2023-01-01",
                           ):
        """
        学習データ、テストデータを作成する
        test_start_dateとvalid_start_dateをyyyy-mm-dd形式で指定する。
        valid以前を学習データ、以降からtestまでをモニタリングデータとする
        """
        #目的変数、行ったy区とおなじタイムかどうかを見ることにする
        self.features["target"] = (self.features["rank"] == 1).astype(int)
        self.features["target_mod"] = (self.features["time_rank"] == 1).astype(int)
        # 学習データとテストデータに分類
        self.train_df = self.features.query("date < @valid_start_date") # 変数はアットマークから入れる
        self.valid_df = self.features.query("date >= @valid_start_date and date < @test_start_date")
        self.test_df = self.features.query("date >= @test_start_date")

    # train_dfとtest_dfは存在しない可能性があるので引数として明記する
    # 逆にfeature_colsは__init__内部にあるため引数にはしないことにする
    def train(
            self,
            train_df : pd.DataFrame,
            test_df : pd.DataFrame,
            importance_filename : str,
            model_filename : str,
            calibration_filename : str,
            ):

        train_df = self.train_df.copy()
        test_df = self.test_df.copy()
        valid_df = self.valid_df.copy()
        cat_list = ["horse_id","jockey_id","trainer_id","race_type","sex","around", "month"] #config.yamlのcolumnかどうかしっかりチェック
        for col in cat_list:
            train_df[col] = train_df[col].astype("category").cat.codes
            test_df[col] = test_df[col].astype("category").cat.codes
        lgb_train = lgb.Dataset(
            train_df.loc[:, self.feature_cols],  
            train_df.loc[:, "target_mod"],       
            categorical_feature=cat_list
        )
        # lgb_test = lgb.Dataset(
        #     test_df.loc[:, self.feature_cols],  
        #     test_df.loc[:, "target_mod"],         
        #     categorical_feature=cat_list
        # )
        lgb_valid = lgb.Dataset(
            valid_df.loc[:, self.feature_cols],  
            valid_df.loc[:, "target_mod"],         
            categorical_feature=cat_list
        )

        params = {
            "objective" : "binary", #二値分類
            "metric" : "binary_logloss", # 予測誤差
            "random_state": 100, # 実行ごとに同じ結果を得るための設定
            'learning_rate': 0.05,
            'num_leaves': 41,
            'min_data_in_leaf': 15,
            'feature_fraction': 0.9,
            'bagging_fraction': 1.0,
            'bagging_freq': 7,
            'lamda_l1': 1.0,
            'lamda_l2': 1.0
        }
        model = lgb.train(
            params =params,
            train_set=lgb_train,
            valid_sets=[lgb_valid],
            num_boost_round=1000,
            callbacks=[lgb.log_evaluation(20),
                       lgb.early_stopping(stopping_rounds=20)
                       ],
        )

        with open(self.output_dir / model_filename, "wb") as f:
            pickle.dump(model, f)
        # 特徴量重要度の可視化
        lgb.plot_importance(model, importance_type="gain", figsize=(30, 20))
        plt.savefig(self.output_dir / importance_filename)
        plt.close()
        ir = IsotonicRegression(out_of_bounds="clip")
        self.df_ir_train = self.valid_df.copy()
        self.df_ir_train["pred"] = model.predict(
            self.df_ir_train[self.feature_cols], num_iteration = model.best_iteration
        )
        # self.df_ir_train = self.df_ir_train.query("pred > 0.01")
        ir.fit(self.df_ir_train["pred"], self.df_ir_train["target"])
        with open(self.output_dir / calibration_filename, "wb")as f:
            pickle.dump(ir, f)
        #テストデータに対してスコアリング
        evaluation_df = test_df[[
            "race_id",
            "horse_id",
            "target_mod",
            "target",
            "rank",
            "tansho_odds",
            "popularity",
            "race_class",
            "month"
        ]].copy()
        evaluation_df["pred"] = model.predict(
            test_df[self.feature_cols], num_iteration = model.best_iteration
            )
        evaluation_df["calibrated_pred"] = ir.predict(evaluation_df["pred"])
        logloss = log_loss(evaluation_df["target"], evaluation_df["pred"])
        print("-" * 20 + "result" + "-" * 20)
        print(f"logloss = {logloss}")
        # # オッズが150越していたら来る確率0に変更
        # evaluation_df['new_pred'] = evaluation_df['pred'].apply(lambda x: exp_con(x=x))* (evaluation_df['tansho_odds'] <= 200)
        # evaluation_df['pred_true'] = evaluation_df.groupby('race_id')['new_pred'].transform(lambda x: x / x.sum())
        evaluation_df["expected_value"] = evaluation_df["pred"] * evaluation_df["tansho_odds"]
        evaluation_df["calibrated_expected_value"] = evaluation_df["calibrated_pred"] * evaluation_df["tansho_odds"]
        evaluation_df.to_csv(OUTPUT_DIR / "evaluation.csv", sep="\t", index=False)
        # # evaluation_df = evaluation_df.query("race_class != 0")
        # bet_df = (
        #     evaluation_df
        #     .sort_values("expected_value", ascending=False)
        #     .groupby("race_id")
        #     .head(1)
        # )
        # # 的中率
        # print(f'的中率 = {bet_df["target"].mean()}')
        # # 回収率
        # return_ = ((bet_df["target"] == 1) * bet_df["tansho_odds"]).sum()
        # cost_ = len(bet_df)
        # print(f"回収率 = {return_ / cost_}")
        return evaluation_df


    def run(
            self,
            test_start_date : str = "2024-01-01",
            valid_start_date : str = "2023-01-01",
            importance_filename : str = "importance.png",
            model_filename : str = "model.pkl",
            calibration_filename : str = "calibration.pkl"
            ):
        """
        学習がこれのみで実行できる
        test_start_dateをyyyy-mm-dd形式で指定すると、その日以前を学習データ、以降をテストデータとする
        """
        self.create_dataset_mod(
            test_start_date = test_start_date, 
            valid_start_date = valid_start_date
            )
        evaluation_df = self.train(
            self.train_df, 
            self.test_df, 
            importance_filename, 
            model_filename,
            calibration_filename
            )
        return evaluation_df


