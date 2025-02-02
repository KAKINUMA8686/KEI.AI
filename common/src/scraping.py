import pandas as pd
import time
import re
import chardet
import traceback
import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from tqdm import tqdm
from pathlib import Path

HTML_DIR = Path("..", "data", "html")
HTML_RACE_DIR = Path(HTML_DIR, "race")
HTML_HORSE_DIR = Path(HTML_DIR, "horse")
HTML_HORSE_JAVA_DIR = Path(HTML_DIR, "horse_java")

def scrape_kaisai_date(from_, to_) -> list[str]:
  """
  from_とto_をyyyy-mm(ex:2024-01)の形で設定すると開催日時を取ってくる
  引数を””で囲うのまじで注意
  """
  kaisai_date_list = []
  # tqdm()とすることで進捗をバーで表示
  for date in tqdm(pd.date_range(from_, to_, freq="MS")):
    year_ = date.year
    month_ = date.month 
    #url = "https://race.netkeiba.com/top/calendar.html?year="+str(year_)+"&month="+str(month_)
    url = f"https://race.netkeiba.com/top/calendar.html?year={year_}&month={month_}"
    #print(url)
    headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }

    #urlから情報を取る。headerないとエラー
    req = Request(url, headers=headers)
    response = urlopen(req).read()
    #今後の処理のためhtmlをデコードする
    encoding = chardet.detect(response)['encoding']
    html = response.decode(encoding)
    time.sleep(1)
    #要素取り出すためにbeautiful soupライブラリを用いる
    soup = BeautifulSoup(html, 'html.parser')
    #Calender_Tablerのなかからa要素を抜く
    a_list = soup.find("table",class_="Calendar_Table").find_all("a")
    for a in a_list:
      kaisai_date = re.findall(r"kaisai_date=(\d{8})", a["href"])[0]
      kaisai_date_list.append(kaisai_date)

  print(kaisai_date_list)
  return kaisai_date_list

# scrape_kaisai_date(from_ = "2023-01",to_ = "2023-12")


def scrape_race_id_list(kaisai_date_list: list[str]) -> list[str]:
    """
    開催日の一覧からレーズID一覧を返す関数
    listはyyyymmdd(20230101)のような形のstrで与える
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless") # 新しいウィンドウが開かなくなる
    chrome_options.add_argument("no-sandbox")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument('--disable-gpu')  
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-desktop-notifications')
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument('--lang=ja')
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--proxy-server="direct://"')
    chrome_options.add_argument('--proxy-bypass-list=*')    
    chrome_options.add_argument('--start-maximized')
    chrome_options.binary_location = "/usr/bin/google-chrome"
    driver_path = ChromeDriverManager().install()
    #print(driver_path)

    driver = webdriver.Chrome(service = Service(driver_path), options = chrome_options)
    race_id_list = []

    with webdriver.Chrome(service = Service(driver_path), options = chrome_options) as driver:
        for kaisai_date in tqdm(kaisai_date_list):
            url = f"https://race.netkeiba.com/top/race_list.html?kaisai_date={kaisai_date}"
            # print(url)

            # タイムアウトを設定（秒単位)
            driver.set_page_load_timeout(15)
            try:
                driver.get(url)  # URLにアクセス
                time.sleep(1)
            except:
                pass
            li_list = driver.find_elements(By.CLASS_NAME, "RaceList_DataItem")
            for li in li_list:
                href = li.find_element(By.TAG_NAME, "a").get_attribute("href")
                race_id = re.findall(r"race_id=(\d{12})", href)[0]
                race_id_list.append(race_id)
            # except:
            #     print(f"stopped at {url}")
            #     print(traceback.format_exc())
            #     break
    return race_id_list



def scrape_html_race(race_id_list: list[str], save_dir : Path = HTML_RACE_DIR) ->list[Path] :
    """
    race_id_listに示されたレース結果をnetkeibaから読み込み、save_dirに指定されたパスに保存する関数。
    すでにHTMLが存在する場合はスキップされ、新しく取得されたHTMLのPathのみ返す。
    """
    html_path_list = []
    save_dir.mkdir(parents=True, exist_ok=True)
    for race_id in tqdm(race_id_list):
        # パスを指定してbinary型htmlを保存
        file_path = HTML_RACE_DIR / f"{race_id}.bin"
        # エラー原因となるrace_idをはじく
        if race_id == "201805010304":
            print("race_id 201805010304はレースが行われていません")
            pass        
        # ファイルがすでに存在している場合はスキップをする
        elif file_path.is_file():
            print(f"skipped : {race_id}")
            pass
        else:
            try:
                url = f"https://db.netkeiba.com/race/{race_id}/"
                headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
                }
                # req = Request(url, headers=headers)
                # response = urlopen(req).read()
                response = requests.get(url, headers=headers, timeout=20)
                time.sleep(1)
                with open(file_path, "wb") as f:
                    f.write(response.content)
                
                html_path_list.append(file_path)

            except:
                print(f"Error fetching {race_id}")
            
    return html_path_list


def scrape_html_horse(
        horse_id_list: list[str],
        save_dir: Path = HTML_HORSE_JAVA_DIR,
        skip: bool = True,
) -> list[Path]:
    """
    horse_id_listに示されたレース結果をnetkeibaから読み込み、save_dirに指定されたパスにHTML(JAVA)を保存する関数。
    skip = TrueのときすでにHTMLが存在する場合はスキップされ、新しく取得されたHTMLのPathのみ返す。
    """
    html_path_list = []
    save_dir.mkdir(parents=True, exist_ok=True)
    remaining_horse_ids = horse_id_list.copy()  # 再試行用のリスト

    while len(remaining_horse_ids) > 0:  # リストが空でないかを確認
    # 処理が終わっていない馬がいる限りループ
        failed_horse_ids = []  # 再試行が必要な馬のリスト

        for horse_id in tqdm(remaining_horse_ids):
            # パスを指定してbinary型htmlを保存
            file_path = save_dir / f"{horse_id}.bin"
            # ファイルがすでに存在し、skip=Trueの場合はスキップをする
            if file_path.is_file() and skip:
                # print(f"skipped : {horse_id}")
                continue
            else:
                try:
                    chrome_options = Options()
                    chrome_options.add_argument("--headless")  # 新しいウィンドウが開かなくなる
                    chrome_options.add_argument("no-sandbox")
                    chrome_options.add_argument("--disable-extensions")
                    chrome_options.add_argument('--disable-gpu')
                    chrome_options.add_argument('--ignore-certificate-errors')
                    chrome_options.add_argument('--allow-running-insecure-content')
                    chrome_options.add_argument('--disable-web-security')
                    chrome_options.add_argument('--disable-desktop-notifications')
                    chrome_options.add_argument('--lang=ja')
                    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    chrome_options.add_argument('--proxy-server="direct://"')
                    chrome_options.add_argument('--proxy-bypass-list=*')
                    chrome_options.add_argument('--start-maximized')
                    chrome_options.binary_location = "/usr/bin/google-chrome"
                    driver_path = ChromeDriverManager().install()
                    url = f"https://db.netkeiba.com/horse/{horse_id}/"

                    with webdriver.Chrome(service=Service(driver_path), options=chrome_options) as driver:
                        driver.implicitly_wait(10)
                        driver.set_page_load_timeout(10)
                        try:
                            driver.get(url)  # URLにアクセス

                        except Exception as e:
                            # print(f"Error fetching {horse_id}: {e}")
                            failed_horse_ids.append(horse_id)  # 再試行対象として追加
                            continue
                        # ページのHTMLを取得
                        html = driver.page_source
                        # HTMLを保存
                        with open(file_path, "wb") as f:
                            f.write(html.encode("utf-8"))

                        # ファイルサイズが小さい場合、再試行リストに追加
                        if os.path.getsize(file_path) < 300000:
                            print(f"File too small, retrying: {horse_id}")
                            file_path.unlink()  # ファイルを削除
                            failed_horse_ids.append(horse_id)  # 再試行リストに追加
                            continue
                        html_path_list.append(file_path)
                except Exception as e:
                    # print(f"Error fetching {horse_id}: {e}")
                    failed_horse_ids.append(horse_id)  # 再試行リストに追加

        remaining_horse_ids = failed_horse_ids  # 再試行リストを更新

        if not remaining_horse_ids:  # 再試行が不要になったらループ終了
            break

    return html_path_list
