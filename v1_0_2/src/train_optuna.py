import pandas as pd
from pathlib import Path
import yaml
import lightgbm as lgb
import matplotlib.pyplot as plt
import pickle
import optuna
import numpy as np
from sklearn.metrics import log_loss
from sklearn.isotonic import IsotonicRegression
from IPython.display import clear_output

DATA_DIR = Path("..", "data")
INPUT_DIR = DATA_DIR / "02_features"
OUTPUT_DIR = DATA_DIR / "03_models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class Trainer:
    def __init__(
        self,
        features_filepath: Path = INPUT_DIR / "features.csv",
        config_filepath: Path = "config_new.yaml",
        output_dir : Path = OUTPUT_DIR,
    ):
        self.features = pd.read_csv(features_filepath, sep = "\t")
        with open(config_filepath) as f:
            self.feature_cols = yaml.safe_load(f)["features"]
        self.output_dir = output_dir # self.~は()外で一度定義しなくては使えない


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

    def objective(self, trial):
        """
        Optuna の目的関数
        """
        train_df = self.train_df.copy()
        valid_df = self.valid_df.copy()
        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "boosting_type": "gbdt",
            "learning_rate": trial.suggest_float("learning_rate", 0.05, 0.05),
            "num_leaves": trial.suggest_int("num_leaves", 41, 41),
            "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 5, 100, step=5),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.9, 0.9, step = 0.01),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 1.0, 1.0, step = 0.1),
            "bagging_freq": trial.suggest_int("bagging_freq", 7, 7),
            "lamda_l1" : trial.suggest_float("lamda_l1", 1, 1),
            "lamda_l2" : trial.suggest_float("lamda_l2", 1, 1),
            "verbosity": -1,
            "random_state": 100,
        }
        train_data = lgb.Dataset(
            train_df[self.feature_cols],
            label = train_df["target_mod"],
        )
        valid_data = lgb.Dataset(
            valid_df[self.feature_cols],
            label = valid_df["target_mod"],
        )
        model = lgb.train(
            params =params,
            train_set=train_data,
            valid_sets=[valid_data],
            num_boost_round=500,
            callbacks=[
                    #lgb.log_evaluation(5),
                    lgb.early_stopping(stopping_rounds=30)
                       ],
        )
        valid_df["pred"] = model.predict(valid_df[self.feature_cols])
        logloss = log_loss(valid_df["target"], valid_df["pred"])
        return logloss


    # train_dfとtest_dfは存在しない可能性があるので引数として明記する
    # 逆にfeature_colsは__init__内部にあるため引数にはしないことにする
    def train(
            self,
            train_df : pd.DataFrame,
            test_df : pd.DataFrame,
            ):

        train_df = self.train_df.copy()
        test_df = self.test_df.copy()
        valid_df = self.valid_df.copy()


        study = optuna.create_study(direction="minimize")
        study.optimize(self.objective, n_trials = 30)

        print("Best trial:", study.best_trial.params)
        self.best_params = study.best_trial.params

        cat_list = ["horse_id","jockey_id","trainer_id","race_type","sex","around", "month"] #config.yamlのcolumnかどうかしっかりチェック
        for col in cat_list:
            train_df[col] = train_df[col].astype("category").cat.codes
            test_df[col] = test_df[col].astype("category").cat.codes
        lgb_train = lgb.Dataset(
            train_df.loc[:, self.feature_cols],  
            train_df.loc[:, "target_mod"],       
            categorical_feature=cat_list
        )
        lgb_valid = lgb.Dataset(
            valid_df.loc[:, self.feature_cols],  
            valid_df.loc[:, "target_mod"],         
            categorical_feature=cat_list
        )
        # ここまで一旦クリア
        clear_output()        
        params = self.best_params

        model = lgb.train(
            params =params,
            train_set=lgb_train,
            valid_sets=[lgb_valid],
            num_boost_round=500,
            callbacks=[lgb.log_evaluation(5),
                       lgb.early_stopping(stopping_rounds=30)
                       ],
        )

        ir = IsotonicRegression(out_of_bounds="clip")
        self.df_ir_train = self.valid_df.copy()
        self.df_ir_train["pred"] = model.predict(
            self.df_ir_train[self.feature_cols], num_iteration = model.best_iteration
        )
        self.df_ir_train = self.df_ir_train.query("pred > 0.01")
        ir.fit(self.df_ir_train["pred"], self.df_ir_train["target"])
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
        evaluation_df["expected_value"] = evaluation_df["pred"] * evaluation_df["tansho_odds"]
        evaluation_df["calibrated_expected_value"] = evaluation_df["calibrated_pred"] * evaluation_df["tansho_odds"]
        return evaluation_df


    def run(
            self,
            test_start_date : str = "2024-01-01",
            valid_start_date : str = "2023-01-01",
            ):
        """
        学習がこれのみで実行できる
        test_start_dateをyyyy-mm-dd形式で指定すると、その日以前を学習データ、以降をテストデータとする
        """
        self.create_dataset_mod(
            test_start_date = test_start_date, 
            valid_start_date = valid_start_date,
            )
        evaluation_df = self.train(
            train_df=self.train_df, 
            test_df=self.test_df, 
            )
        return evaluation_df


