import pandas as pd
from collections import defaultdict
from pathlib import Path
import numpy as np
import seaborn as sns
import math
import matplotlib.pyplot as plt

INPUT_DIR = Path("..", "data", "03_models", "evaluation.csv")



def check(
        input_dir: Path = INPUT_DIR,
        pred_limit : float = 0.01,
        odds_limit : float = 100,
        min_value = 1.0,
        max_value = 4.0,
        ) -> pd.DataFrame:
    """
    calibrated_predとexpected_valueの閾値を決めたときのreturn_rateや残る馬の数をプロット
    min~maxの間でexpected_value閾値を探索する
    """
    df = pd.read_csv(input_dir, sep="\t")
    result = defaultdict(list)
    for exp in np.linspace(min_value, max_value, 100):
        bet_df = df.query(
            f"calibrated_expected_value>{exp}"
            ).query(
                f"calibrated_pred>{pred_limit}"
                ).query(
                    f"tansho_odds<{odds_limit}"
                )
        bet_df = bet_df.copy()
        bet_df.loc[:, "payoff"] = bet_df.loc[:, "target"] * bet_df.loc[:, "tansho_odds"]
        total_payoff = bet_df["payoff"].sum()
        total_bet = len(bet_df)
        if total_bet == 0:
            return_rate =0
        else:
            return_rate = total_payoff / total_bet
        result["calibrated_expected_value"].append(exp)
        result["total_bet"].append(total_bet)
        result["total_payoff"].append(total_payoff)
        result["return_rate"].append(return_rate)

    result_df = pd.DataFrame({
        "calibrated_expected_value": result["calibrated_expected_value"],
        "total_bet": result["total_bet"],
        "total_payoff": result["total_payoff"],
        "return_rate": result["return_rate"]
    })

    # プロット
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # 左側のy軸（total_betとtotal_payoff用）
    ax1.set_xlabel("calibrated_expected_value")
    ax1.set_ylabel("Number", color='tab:blue')
    line1 = ax1.plot(result_df["calibrated_expected_value"], result_df["total_bet"], 
                     color='tab:blue', label="total_bet")
    line2 = ax1.plot(result_df["calibrated_expected_value"], result_df["total_payoff"], 
                     color='tab:orange', label="total_payoff")
    ax1.tick_params(axis='y', labelcolor='tab:blue')

    # 右側のy軸（return_rate用）
    ax2 = ax1.twinx()
    ax2.set_ylabel("Return Rate", color='tab:green')
    line3 = ax2.plot(result_df["calibrated_expected_value"], result_df["return_rate"], 
                     color='tab:green', label="return_rate")
    ax2.tick_params(axis='y', labelcolor='tab:green')

    # グリッドラインを左側の軸に合わせる
    ax1.grid(True)
    
    # 両軸の目盛り数を揃える
    min_y1 = min(result_df["total_bet"].min(), result_df["total_payoff"].min())
    max_y1 = max(result_df["total_bet"].max(), result_df["total_payoff"].max())
    min_y2 = result_df["return_rate"].min()
    max_y2 = result_df["return_rate"].max()

    ax1.set_ylim([min_y1, max_y1])
    ax2.set_ylim([min_y2, max_y2])


    # 凡例を結合して表示
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, 1.0))
    plt.title("Expected Value vs. Metrics")
    plt.tight_layout()  # レイアウトの自動調整
    plt.show()

    return result_df

def check_happy(
        input_dir: Path = INPUT_DIR,
        pred_limit : float = 0.01,
        odds_limit : float = 100,
        min_value = 1.0,
        max_value = 4.0,
        ) -> pd.DataFrame:
    """
    calibrated_predとexpected_valueの閾値を決めたときのreturn_rateや残る馬の数をプロット
    min~maxの間でexpected_value閾値を探索する
    """
    df = pd.read_csv(input_dir, sep="\t")
    result = defaultdict(list)
    for exp in np.linspace(min_value, max_value, 100):
        bet_df = df.query(
            f"calibrated_expected_value>{exp}"
            ).query(
                f"calibrated_pred>{pred_limit}"
                ).query(
                    f"tansho_odds<{odds_limit}"
                )
        bet_df = bet_df.copy()
        bet_df.loc[:, "payoff"] = bet_df.loc[:, "target"] * bet_df.loc[:, "tansho_odds"]
        total_payoff = bet_df["payoff"].sum()
        total_bet = len(bet_df)
        if total_bet == 0:
            return_rate =0
        else:
            return_rate = total_payoff / total_bet
        result["calibrated_expected_value"].append(exp)
        result["total_bet"].append(total_bet)
        result["total_payoff"].append(total_payoff)
        result["return_rate"].append(return_rate)

    result_df = pd.DataFrame({
        "calibrated_expected_value": result["calibrated_expected_value"],
        "total_bet": result["total_bet"],
        "total_payoff": result["total_payoff"],
        "return_rate": result["return_rate"]
    })

    # プロット
    fig, ax1 = plt.subplots(figsize=(8, 6))

    # 右側のy軸（return_rate用）
    ax1.set_ylabel("Return Rate", color='tab:green')
    ax1.set_xlabel("Threshold")
    line3 = ax1.plot(result_df["calibrated_expected_value"], result_df["return_rate"], 
                     color='tab:blue', label="return_rate")
    ax1.tick_params(axis='y', labelcolor='tab:green')

    # グリッドラインを左側の軸に合わせる
    ax1.grid(True)
    
    min_y1 = result_df["return_rate"].min()
    max_y1 = result_df["return_rate"].max()

    ax1.set_ylim([min_y1, max_y1])


    # 凡例を結合して表示
    lines = line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.2, 1.0))
    plt.title("Expected Value vs. Metrics")
    plt.tight_layout()  # レイアウトの自動調整
    plt.show()

    return result_df