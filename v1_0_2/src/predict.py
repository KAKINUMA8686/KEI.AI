import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

DATA_DIR = Path("..", "data")
MODEL_DIR = DATA_DIR / "03_models"


# def exp_con(x):
#     """
#     指数関数、xの係数が大きいほど引数の大小が返り値の反映される
#     """
#     return (np.exp(8 * x) - 1) / (np.exp(8) - 1)


def predict(
    features: pd.DataFrame,
    model_filepath: Path = MODEL_DIR / "model.pkl",
    config_filepath: Path = "config.yaml",
    input_dir : Path = MODEL_DIR,
    calibration_filename : str = "calibration.pkl",
    ):
    """
    model_filepathからモデル読み込み、config_filepathから変数読み込みをする。
    featuresに予想csvを入れる。
    """
    with open(config_filepath, "r") as f:
        feature_cols = yaml.safe_load(f)["features"]
    with open(model_filepath, "rb") as f:
        model = pickle.load(f)
    prediction_df = features[["race_id", "umaban", "tansho_odds", "popularity"]].copy()
    prediction_df["pred"] = model.predict(features[feature_cols])

    # prediction_df['new_pred'] = prediction_df['pred'].apply(lambda x: exp_con(x=x))* (prediction_df['tansho_odds'] <= 100)
    # prediction_df['pred_true'] = prediction_df.groupby('race_id')['new_pred'].transform(lambda x: x / x.sum())
    # prediction_df["expected_value"] = prediction_df["pred_true"] * prediction_df["tansho_odds"]
    # ir読み込み
    with open(input_dir / calibration_filename, "rb") as f:
        loaded_ir = pickle.load(f)

    prediction_df["calibrated_pred"] = loaded_ir.predict(prediction_df["pred"])
    # prediction_df["expected_value"] = prediction_df["pred"] * prediction_df["tansho_odds"]
    prediction_df["calibrated_expected_value"] = prediction_df["calibrated_pred"] * prediction_df["tansho_odds"]
    prediction_df = prediction_df[["race_id", "umaban", "tansho_odds", "calibrated_pred", "calibrated_expected_value"]]

    return prediction_df.sort_values("calibrated_expected_value", ascending=False)