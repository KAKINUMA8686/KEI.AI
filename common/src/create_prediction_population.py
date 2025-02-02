import re
import lxml
import pandas as pd
import scraping
import time
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.request import Request,urlopen
from pathlib import Path


POPULATION_DIR = Path("..", "data", "prediction_population")
POPULATION_DIR.mkdir(parents=True, exist_ok=True)

def scrape_horse_id_list(race_id : str) -> list[str]:
    """
    予測したいレースに出走する馬のhorse_id一覧を返す
    race_idを引数に取る
    """
    url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}&rf=race_submenu"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    req = Request(url, headers=headers)
    html = urlopen(req).read()
    soup = BeautifulSoup(html, 'lxml')
    td_list = soup.find_all("td", class_ = "HorseInfo")
    horse_id_list = []
    for td in td_list:
        a = re.findall(r"\d{10}", td.find("a")["href"])[0]
        horse_id_list.append(a)
    return horse_id_list

def create(
        kaisai_date : str,
        save_dir : Path  = POPULATION_DIR,
        save_filename : str = "population.csv",
) -> pd.DataFrame:
    """
    開催日(yyyymmdd形式)で指定すると予測集団である
    (date, race_id, horse_id)のDataFrameが帰ってくる関数
    """
    print("scraping race_id_list ...")
    race_id_list = scraping.scrape_race_id_list([kaisai_date])
    print(f"race_id list : {race_id_list}")
    dfs = {}
    print("scraping horse_id_list ...")    
    for race_id in tqdm(race_id_list):
        horse_id_list = scrape_horse_id_list(race_id)
        time.sleep(1)
        df = pd.DataFrame(
            {"date": kaisai_date, "race_id" : race_id, "horse_id" : horse_id_list}
        )
        dfs[race_id] = df
    concat_df = pd.concat(dfs.values())
    concat_df["date"] = pd.to_datetime(concat_df["date"])
    concat_df.to_csv(save_dir / save_filename, index=False, sep="\t")
    return concat_df
    

