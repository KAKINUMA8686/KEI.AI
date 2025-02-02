import pandas as pd
from collections import defaultdict
from pathlib import Path
import numpy as np
import seaborn as sns
import math
import matplotlib.pyplot as plt

INPUT_DIR = Path("..", "data", "03_models", "evaluation.csv")



def exp_con(
        a , x,
        ):
    """
    指数関数、aが大きいほど引数の大小が返り値の反映される
    """
    return (np.exp(a * x) - 1) / (np.exp(a) - 1)


def plot(input_dir: Path = INPUT_DIR):
    """
    exp_conのaの値を変化させた時のreturn_rateをプロットする
    """
    result = defaultdict(list)
    df = pd.read_csv(input_dir, sep="\t")[["race_id","target","rank","tansho_odds","popularity","pred","new_pred","pred_true"]]
    # df = df[df["tansho_odds"]<10]
    for i in range(1):
        a = 12 + i
        # df['new_pred'] = df['pred'].apply(lambda x: exp_con(a=a, x=x))
        # df['pred_true'] = df.groupby('race_id')['new_pred'].transform(lambda x: x / x.sum())
        df["expected_value"] = df["pred_true"] * df["tansho_odds"]
        for exp in np.linspace(0.8, 4, 100):
            # bet_df = df.query(f"expected_value > {exp}")
            bet_df = df[ (df["expected_value"]>exp)]
            bet_df = bet_df.copy()
            bet_df.loc[:, "payoff"] = bet_df.loc[:, "target"] * bet_df.loc[:, "tansho_odds"]
            total_payoff = bet_df["payoff"].sum()
            total_bet = len(bet_df)
            if total_bet == 0:
                return_rate = 0  # または np.nan
            else:
                return_rate = total_payoff / total_bet


            # a の値ごとに結果を保存
            result[a].append({
                "expected_return": exp,
                "total_bet": total_bet,
                "total_payoff": total_payoff,
                "return_rate": return_rate
            })

    # すべての計算が終わってからDataFrameに変換
    all_results = []
    for a, res_list in result.items():
        df_a = pd.DataFrame(res_list)
        df_a['a'] = a
        all_results.append(df_a)
    result_df = pd.concat(all_results)

    # プロット
    sns.set_style("whitegrid")   # グリッドスタイルを設定
    
    # lineplotの設定を詳細に指定
    sns.lineplot(
        data=result_df, 
        x="expected_return", 
        y="return_rate", 
        hue="a",
        linewidth=1,           # 線の太さを増加
        palette="deep",          # より濃い色のパレットを使用
    )
    return df



def num_horse_check(input_dir: Path = INPUT_DIR):
    """
    return_rateの閾値を決めたときに残る馬の数等をプロット
    """
    df = pd.read_csv(input_dir, sep="\t")
    result = defaultdict(list)
    for exp in np.linspace(1.4, 4.0, 100):
        bet_df = df.query(f"expected_value>{exp}")
        bet_df = bet_df.copy()
        bet_df.loc[:, "payoff"] = bet_df.loc[:, "target"] * bet_df.loc[:, "tansho_odds"]
        total_payoff = bet_df["payoff"].sum()
        total_bet = len(bet_df)
        return_rate = total_payoff / total_bet
        result["expected_value"].append(exp)
        result["total_bet"].append(total_bet)
        result["total_payoff"].append(total_payoff)
        result["return_rate"].append(return_rate)

    result_df = pd.DataFrame({
        "expected_value": result["expected_value"],
        "total_bet": result["total_bet"],
        "total_payoff": result["total_payoff"],
        "return_rate": result["return_rate"]
    })

    # プロット
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # 左側のy軸（total_betとtotal_payoff用）
    ax1.set_xlabel("expected_value")
    ax1.set_ylabel("Number", color='tab:blue')
    line1 = ax1.plot(result_df["expected_value"], result_df["total_bet"], 
                     color='tab:blue', label="total_bet")
    line2 = ax1.plot(result_df["expected_value"], result_df["total_payoff"], 
                     color='tab:orange', label="total_payoff")
    ax1.tick_params(axis='y', labelcolor='tab:blue')

    # 右側のy軸（return_rate用）
    ax2 = ax1.twinx()
    ax2.set_ylabel("Return Rate", color='tab:green')
    line3 = ax2.plot(result_df["expected_value"], result_df["return_rate"], 
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