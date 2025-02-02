import tkinter as tk
import webbrowser
import datetime
import sys
import pandas as pd
from PIL import Image
from tkinter import Toplevel, ttk
from pathlib import Path
from tkcalendar import Calendar
from tkinter import RIGHT, END, DISABLED, NORMAL

# # ディレクトリの定義と有効化
IMAGE_DIR = Path("image")
BEFORE_DIR = Path("..", "common", "src")
AFTER_DIR = Path("..", "..", "v1_0_2")
sys.path.append(str(BEFORE_DIR))
sys.path.append(str(AFTER_DIR))


# 有効化した場所からインポート
from create_prediction_population import create
from scraping import scrape_html_horse
from create_rawdf import create_horse_results, create_horse_info
from preprocessing import process_horse_results
from feature_engeneering import PredictionFeatureCreator

def open_horse_url(url):
    webbrowser.open(url)

class HorseApp:
    def __init__(self):

        self.horse_id_list = ["2019105219", "2019105219"]

        # 最初の画面作成、initで自動実行
        self.start_window = tk.Tk()
        self.start_window.title("Start Screen")
        self.start_window.geometry("1000x700")
        self.start_window.resizable(0, 0)
        self.start_window.configure(bg="white")

        # フォント,色をここで設定
        self.button_font = ("Segoe UI", 12)
        self.button_color = "#89c3eb"
        self.activated_button_color = "#a0d8ef"
        self.umas_button_color = "lightgray"
        self.umas_button_color_activated = "gainsboro"

        # アイコン画像をロード        
        self.logo = self.load_resized_image(IMAGE_DIR / "icon.png", 288, 180)
        self.horseimg = self.load_resized_image(IMAGE_DIR / "horse_pict.png", 45, 45)

        # ロゴ付近の設定、作成
        logo_label = tk.Label(self.start_window, image=self.logo, bg="white")
        logo_text = tk.Label(self.start_window, text="Horse\nLMS  ", 
                           font=("Arial", 21), bg="white", fg=self.button_color)
        logo_label.grid(row=0, column=0, sticky="es", padx=(10,0))
        logo_text.grid(row=0, column=1, sticky="ws", pady = 53)

        # 行列の重み付けを設定
        self.start_window.grid_rowconfigure(0, weight=1)
        self.start_window.grid_rowconfigure(1, weight=1)
        self.start_window.grid_columnconfigure(0, weight=1)
        self.start_window.grid_columnconfigure(1, weight=1)

        # ログインフレームの縁取りがうまく行かなかったので後ろにフレーム作成
        back_login_frame = tk.Frame(
            self.start_window, 
            bg="lightgray", 
            width=804,
            height=174, 
        )
        back_login_frame.grid(row = 1,column = 0, columnspan=2, sticky="n")
        back_login_frame.grid_propagate(False)

        # ログインフレーム作成
        login_frame = tk.Frame(
            self.start_window, 
            bg="white", 
            width=800,
            height=170, 
            highlightbackground="lightgray",
            )
        login_frame.grid(row = 1,column = 0, columnspan=2, sticky="n", pady = 1.5)
        login_frame.grid_propagate(False)


        #ログインフレーム内の文字作成
        login_label = tk.Label(login_frame, bg = "white", font=("Arial", 12), fg = "#3f312b", text = "HORSE スタート")
        login_label.grid(row = 0, column = 0, pady=(10,0))

        # フレーム内のレイアウト調整
        login_frame.grid_rowconfigure(0, weight=1)
        login_frame.grid_columnconfigure(0, weight=1)
        
        # スタートボタンの作成
        start_button = tk.Button(
            login_frame,
            text="スタート", 
            font=("Segoe UI", 20), 
            relief="flat",
            command=self.show_main_window,
            bg = "#007bbb",
            fg = "white",
            activebackground="#2792c3",
            activeforeground="white"
            )
        start_button.grid(ipadx=120, padx=150, pady=(10,30))
        
        # 一旦メインは閉じる
        self.root = None
        self.images = {}  # 写真の辞書型配列作成
        
    def load_resized_image(self, path, width, height):
        img = Image.open(path)
        img = img.resize((width, height), Image.LANCZOS)  # Using LANCZOS instead of deprecated ANTIALIAS
        img.save("temp_resized_image.png")
        return tk.PhotoImage(file="temp_resized_image.png")
    

    def handle_date_selection(self):
        for widget in self.main_frame.winfo_children():
                if widget.grid_info().get("row") == 3 or widget.grid_info().get("row") == 2 :
                    widget.destroy()
        # main_frame の残りの部分 (row=2) にカレンダーを配置
        for widget in self.main_frame.grid_slaves(row=2):
            widget.destroy()  # 他のウィジェットがある場合は削除

        # カレンダーウィジェットを作成
        calendar = Calendar(
            self.main_frame, 
            selectmode="day",  # 日付選択モード
            year=2025,         # 初期表示する年
            month=1,           # 初期表示する月
            day=1              # 初期表示する日
        )
        calendar.grid(row=2, column=0, sticky="nsew", pady=(40,0), padx=20)


        # 選択した日付を取得するボタン
        def get_date():
            try:
                submit_button.config(text="処理中です...", state=DISABLED)
                self.main_frame.update()  # UIを更新
                # カレンダーから選択された日付をyyyy-mm-dd形式に変換
                selected_date = calendar.get_date()
                formatted_date = selected_date.replace("/", "")
                # print(formatted_date)
                # 処理実行
                population_df = create(formatted_date)
                self.horse_id_list = population_df["horse_id"].unique()                
                
            except Exception as e:
                # エラー発生時の処理
                submit_button.config(text=f"エラーが発生しました: {str(e)}", fg="red")
                self.main_frame.update()  # UIを更新
            # 3秒後にメッセージを消す
            self.main_frame.after(3000, submit_button.config(text="選択した日付で開始", fg = "black", state=NORMAL))
            self.main_frame.update()
            

        submit_button = tk.Button(
            self.main_frame, 
            text="選択した日付で開始",
            font=self.button_font,
            bg=self.button_color,
            relief="flat",
            image=self.images["start"],
            compound="left",
            command=get_date,
            activebackground=self.activated_button_color
        )
        submit_button.grid(row=3, column=0, pady=40, ipady=5)
        # print("日付指定ボタンが押されました")


    def fetch_horse_info(self):
        for widget in self.main_frame.winfo_children():
            if widget.grid_info().get("row") in [2, 3]:
                widget.destroy()

        def scrape_horse():
            horse_id_list = self.horse_id_list
            total_horses = len(horse_id_list)
            self.html_paths_horse = []

            # キャンバスの幅から馬の画像の位置を計算するための関数
            def calculate_horse_position(progress):
                canvas_width = progress_canvas.winfo_width()
                return (progress / 100.0) * (canvas_width - horse_image_width)

            for idx, horse_id in enumerate(horse_id_list, start=1):
                html_path_horse = scrape_html_horse(horse_id_list=[horse_id], skip=False)
                self.html_paths_horse.append(html_path_horse)
                progress = (idx / total_horses) * 100
                progress_var.set(progress)
                
                # 進捗率のテキスト更新
                progress_label.config(text=f"進捗率: {progress:.1f}%")
                
                # 馬の画像の位置を更新
                x_pos = calculate_horse_position(progress)
                progress_canvas.coords(horse_image_item, x_pos, horse_y_position)
                
                self.main_frame.update_idletasks()


        progress_label = tk.Label(
            self.main_frame,
            text="進捗率: 0.0%",
            font=self.button_font,
            bg="white"
        )
        progress_label.grid(row=2, column=0, pady=(100,0))

        # プログレスバーとアニメーション用のキャンバス
        canvas_height = 100
        progress_canvas = tk.Canvas(
            self.main_frame,
            height=canvas_height,
            bg="white",
            highlightthickness=0
        )
        progress_canvas.grid(row=3, column=0, pady=(10,100), padx=40, sticky="nwe")

        # プログレスバーの配置を修正
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_canvas,
            variable=progress_var,
            maximum=100,
            mode="determinate"
        )

        # キャンバスが実際に表示された後にプログレスバーを配置
        def configure_progress_bar(event=None):
            canvas_width = progress_canvas.winfo_width()
            progress_canvas.create_window(
                canvas_width//2,  # 中央に配置
                canvas_height//2, 
                anchor="center",
                window=progress_bar,
                width=canvas_width - 20  # 左右に少し余白を持たせる
            )

        # キャンバスのサイズが決定された後にプログレスバーを配置
        progress_canvas.bind('<Configure>', configure_progress_bar)

        # 馬の画像を配置
        horse_image = self.horseimg
        horse_image_width = horse_image.width()
        horse_y_position = canvas_height//2 - 20
        horse_image_item = progress_canvas.create_image(
            0, horse_y_position,
            image=horse_image,
            anchor="w"
        )

        # スクレイピングボタン
        scraping_button = tk.Button(
            self.main_frame,
            text="スクレイピング スタート",
            font=self.button_font,
            bg=self.button_color,
            relief="flat",
            image=self.images["start"],
            compound="left",
            command=scrape_horse,
            activebackground=self.activated_button_color
        )
        scraping_button.grid(row=2, column=0, pady=(100,200), ipady=5, sticky="n")
        
        print("馬情報取得ボタンが押されました")
        


    def create_tables(self):
        for widget in self.main_frame.winfo_children():
            if widget.grid_info().get("row") in [2, 3]:
                widget.destroy()

        def create_rawdf():
            html_paths_horse = self.html_paths_horse
            total_horses = len(html_paths_horse)
            
            # キャンバスの幅から馬の画像の位置を計算するための関数
            def calculate_horse_position(progress):
                canvas_width = progress_canvas.winfo_width()
                return (progress / 100.0) * (canvas_width - horse_image_width)

            for idx, horse_html in enumerate(html_paths_horse, start=1):
                # scrape_html_horse(horse_htmls=[horse_html], skip=False)
                self.horse_results = create_horse_results(
                    html_path_list = [horse_html],
                    save_filename="horse_results_prediction.csv"
                    )
                self.horse_info = create_horse_info(
                    html_path_list = [horse_html],
                    save_filename="horse_info.csv"
                )
                progress = (idx / total_horses) * 100
                progress_var.set(progress)
                
                # 進捗率のテキスト更新
                progress_label.config(text=f"進捗率: {progress:.1f}%")
                
                # 馬の画像の位置を更新
                x_pos = calculate_horse_position(progress)
                progress_canvas.coords(horse_image_item, x_pos, horse_y_position)
                
                self.main_frame.update_idletasks()


        progress_label = tk.Label(
            self.main_frame,
            text="進捗率: 0.0%",
            font=self.button_font,
            bg="white"
        )
        progress_label.grid(row=2, column=0, pady=(100,0))

        # プログレスバーとアニメーション用のキャンバス
        canvas_height = 100
        progress_canvas = tk.Canvas(
            self.main_frame,
            height=canvas_height,
            bg="white",
            highlightthickness=0
        )
        progress_canvas.grid(row=3, column=0, pady=(10,100), padx=40, sticky="nwe")

        # プログレスバーの配置を修正
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_canvas,
            variable=progress_var,
            maximum=100,
            mode="determinate"
        )

        # キャンバスが実際に表示された後にプログレスバーを配置
        def configure_progress_bar(event=None):
            canvas_width = progress_canvas.winfo_width()
            progress_canvas.create_window(
                canvas_width//2,  # 中央に配置
                canvas_height//2, 
                anchor="center",
                window=progress_bar,
                width=canvas_width - 20  # 左右に少し余白を持たせる
            )

        # キャンバスのサイズが決定された後にプログレスバーを配置
        progress_canvas.bind('<Configure>', configure_progress_bar)

        # 馬の画像を配置
        horse_image = self.horseimg
        horse_image_width = horse_image.width()
        horse_y_position = canvas_height//2 - 20
        horse_image_item = progress_canvas.create_image(
            0, horse_y_position,
            image=horse_image,
            anchor="w"
        )
        # 表加工ボタン
        scraping_button = tk.Button(
            self.main_frame,
            text="表加工 スタート",
            font=self.button_font,
            bg=self.button_color,
            relief="flat",
            image=self.images["start"],
            compound="left",
            command=create_rawdf,
            activebackground=self.activated_button_color
        )
        scraping_button.grid(row=2, column=0, pady=(100,200), ipady=5, sticky="n")
        print("表加工ボタンが押されました")

    def processing_info(self):
        for widget in self.main_frame.winfo_children():
            if widget.grid_info().get("row") in [2, 3]:
                widget.destroy()

        def create_rawdf():
            html_paths_horse = self.html_paths_horse
            total_horses = len(html_paths_horse)
            
            # キャンバスの幅から馬の画像の位置を計算するための関数
            def calculate_horse_position(progress):
                canvas_width = progress_canvas.winfo_width()
                return (progress / 100.0) * (canvas_width - horse_image_width)

            for idx, horse_html in enumerate(html_paths_horse, start=1):
                # scrape_html_horse(horse_htmls=[horse_html], skip=False)
                self.horse_results = create_horse_results(
                    html_path_list = [horse_html],
                    save_filename="horse_results_prediction.csv"
                    )
                self.horse_info = create_horse_info(
                    html_path_list = [horse_html],
                    save_filename="horse_info.csv"
                )
                progress = (idx / total_horses) * 100
                progress_var.set(progress)
                
                # 進捗率のテキスト更新
                progress_label.config(text=f"進捗率: {progress:.1f}%")
                
                # 馬の画像の位置を更新
                x_pos = calculate_horse_position(progress)
                progress_canvas.coords(horse_image_item, x_pos, horse_y_position)
                
                self.main_frame.update_idletasks()

            self.horse_results_preprocessed = process_horse_results(
                save_filename="horse_results_prediction.csv",
                input_filename="horse_results_prediction.csv",
                population_filename="prediction_population.csv"
            )

        progress_label = tk.Label(
            self.main_frame,
            text="進捗率: 0.0%",
            font=self.button_font,
            bg="white"
        )
        progress_label.grid(row=2, column=0, pady=(100,0))

        # プログレスバーとアニメーション用のキャンバス
        canvas_height = 100
        progress_canvas = tk.Canvas(
            self.main_frame,
            height=canvas_height,
            bg="white",
            highlightthickness=0
        )
        progress_canvas.grid(row=3, column=0, pady=(10,100), padx=40, sticky="nwe")

        # プログレスバーの配置を修正
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_canvas,
            variable=progress_var,
            maximum=100,
            mode="determinate"
        )

        # キャンバスが実際に表示された後にプログレスバーを配置
        def configure_progress_bar(event=None):
            canvas_width = progress_canvas.winfo_width()
            progress_canvas.create_window(
                canvas_width//2,  # 中央に配置
                canvas_height//2, 
                anchor="center",
                window=progress_bar,
                width=canvas_width - 20  # 左右に少し余白を持たせる
            )

        # キャンバスのサイズが決定された後にプログレスバーを配置
        progress_canvas.bind('<Configure>', configure_progress_bar)

        # 馬の画像を配置
        horse_image = self.horseimg
        horse_image_width = horse_image.width()
        horse_y_position = canvas_height//2 - 20
        horse_image_item = progress_canvas.create_image(
            0, horse_y_position,
            image=horse_image,
            anchor="w"
        )
        # 前処理ボタン
        scraping_button = tk.Button(
            self.main_frame,
            text="前処理 スタート",
            font=self.button_font,
            bg=self.button_color,
            relief="flat",
            image=self.images["start"],
            compound="left",
            command=create_rawdf,
            activebackground=self.activated_button_color
        )
        scraping_button.grid(row=2, column=0, pady=(100,200), ipady=5, sticky="n")
        print("前処理ボタンが押されました")

    def prediction(self):
        for widget in self.main_frame.winfo_children():
            if widget.grid_info().get("row") in [2, 3]:
                widget.destroy()
        print("予想ボタンが押されました")
    
    def show_main_window(self):
        self.start_window.withdraw()
        if self.root is None:
            self.create_main_window()
        self.root.deiconify()
    
    def create_main_window(self):
        self.root = Toplevel(self.start_window)
        self.root.title("HORSE")
        self.root.geometry("1000x700")
        self.root.resizable(0, 0)
        
        # 画像のロード
        self.images = {
            'calendar': self.load_resized_image(IMAGE_DIR / "calender_pict.png", 35, 35),
            'factory': self.load_resized_image(IMAGE_DIR / "factory_pict.png", 35, 35),
            'horse': self.load_resized_image(IMAGE_DIR / "horse_pict.png", 35, 35),
            'predict': self.load_resized_image(IMAGE_DIR / "predict_pict.png", 35, 35),
            'process': self.load_resized_image(IMAGE_DIR / "process_pict.png", 35, 35),
            'start': self.load_resized_image(IMAGE_DIR / "start_pict.png", 35, 35),
            'umas': self.load_resized_image(IMAGE_DIR / "umas_pict.png", 35, 35),
            'bell': self.load_resized_image(IMAGE_DIR / "bell_pict.png", 40, 27),
            'comment': self.load_resized_image(IMAGE_DIR / "comment_pict.png", 36, 27),
            'triangle1': self.load_resized_image(IMAGE_DIR / "sankaku.png", 10, 10),
            'triangle2': self.load_resized_image(IMAGE_DIR / "gyakusan.png", 10, 10),
            'logo': self.load_resized_image(IMAGE_DIR / "icon.png", 150, 90),
            'shadow': self.load_resized_image(IMAGE_DIR / "shadow.png", 800, 10),
        }
        
        # フォント,色をここで設定
        self.button_font = ("Segoe UI", 12)
        self.button_color = "#89c3eb"
        self.activated_button_color = "#a0d8ef"
        self.umas_button_color = "lightgray"
        self.umas_button_color_activated = "gainsboro"

        
        # メニューフレーム作成
        self.menu_frame = tk.Frame(self.root, bg="white", width=200, height=700)
        self.menu_frame.pack(fill="both", side="left")
        
        # メニューのlogo追加
        logo_label = tk.Label(self.menu_frame, image=self.images['logo'], bg="white")
        logo_text = tk.Label(self.menu_frame, text="Horse\nLMS  ", 
                           font=("Arial", 10), bg="white", fg=self.button_color)
        logo_label.grid(row=0, column=0, sticky="w", padx=(10,0), pady=20)
        logo_text.grid(row=0, column=1, sticky="w")
        
        # 境目のフレーム追加
        thin_frame = tk.Frame(self.root, bg="gainsboro", width=10, height=700)
        thin_frame.pack(fill="both", side="left")
        
        # 三角形追加
        tk.Label(thin_frame, image=self.images['triangle1']).pack()
        tk.Label(thin_frame, image=self.images['triangle2']).pack(side="bottom")
        
        # メインフレーム作成
        self.main_frame = tk.Frame(self.root, bg="white", width=900, height=700)
        self.main_frame.pack(fill="both", side="right")
        
        # 各columnの重み設定
        self.main_frame.grid_rowconfigure(0, weight=0)
        self.main_frame.grid_rowconfigure(1, weight=0)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # ヘッダーの作成
        self.create_header(self.main_frame)
        
        # 影作る
        shadow_main = tk.Label(self.main_frame, image=self.images['shadow'], bg="white")
        shadow_main.grid(row=1, column=0, sticky="we")
        
        # ボタン作る
        self.create_menu_buttons()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_header(self, main_frame):
        header_frame = tk.Frame(main_frame, bg="white", height=50)
        header_frame.grid(row=0, column=0, sticky="we")
        
        for i in range(4):
            header_frame.grid_columnconfigure(i, weight=0 if i != 2 else 1)
        
        tk.Label(header_frame, image=self.images['comment'], bg="white").grid(
            row=0, column=0, padx=(20, 0), pady=10)
        tk.Label(header_frame, image=self.images['bell'], bg="white").grid(
            row=0, column=1, padx=5, pady=10)
        tk.Label(header_frame, text="ver1_0_2", bg="white").grid(
            row=0, column=3, sticky="e", padx=10)
    
    def create_menu_buttons(self):
        buttons = [
            ("日付指定", 'calendar', self.handle_date_selection),
            ("馬情報取得", 'horse', self.fetch_horse_info),
            ("表加工", 'factory', self.create_tables),
            ("前処理", 'process', self.processing_info),
            ("予想", 'predict', self.prediction)
        ]
        
        for idx, (text, img_key, command) in enumerate(buttons, start=1):
            btn = tk.Button(
                self.menu_frame,
                text=text,
                font=self.button_font,
                bg=self.button_color,
                relief="flat",
                anchor="w",
                image=self.images[img_key],
                compound="left",
                command=command,
                activebackground=self.activated_button_color
            )
            btn.grid(row=idx, column=0, columnspan=2, sticky="we", 
                    pady=1, ipadx=30)
        
        # UMASのボタン作成
        umas_btn = tk.Button(
            self.menu_frame,
            text="UMAS",
            font=self.button_font,
            bg=self.umas_button_color,
            relief="flat",
            anchor="w",
            image=self.images['umas'],
            compound="left",
            activebackground=self.umas_button_color_activated,
            command=lambda : open_horse_url("https://db.netkeiba.com/horse/2019105346/"), 
        )
        umas_btn.grid(row=6, column=0, columnspan=2, sticky="we", 
                     pady=(20,1), ipadx=30)
    
    def on_closing(self):
        self.root.destroy()
        self.start_window.destroy()
    
    def run(self):
        self.start_window.mainloop()

if __name__ == "__main__":
    app = HorseApp()
    app.run()