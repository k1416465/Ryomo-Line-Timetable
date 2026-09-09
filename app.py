from flask import Flask, jsonify, render_template
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re

app = Flask(__name__)

JSON_FILE = Path(__file__).with_name("timetable.json")


# ==================================================
# 時刻表JSON読み込み
# ==================================================

def load_timetable():

    with open(
        JSON_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ==================================================
# ホーム
# ==================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ==================================================
# 時刻表API
# ==================================================

@app.route("/api/timetable")
def api_timetable():

    data = load_timetable()

    return jsonify(data)


# ==================================================
# 駅別時刻表
# ==================================================

@app.route("/station/<station>")
def station(station):

    station_map = {

        "tochigi": {
            "name": "栃木駅",
            "english": "Tochigi Station"
        },

        "sano": {
            "name": "佐野駅",
            "english": "Sano Station"
        },

        "ashikaga": {
            "name": "足利駅",
            "english": "Ashikaga Station"
        }

    }

    if station not in station_map:

        return "駅が見つかりません", 404

    station_info = station_map[station]

    return render_template(

        "timetable.html",

        station_id=station,

        station_name=station_info["name"],

        station_english=station_info["english"]

    )


# ==================================================
# JR東日本 両毛線 運行情報
# ==================================================

@app.route("/api/operation")
def api_operation():

    url = (
        "https://traininfo.jreast.co.jp/"
        "train_info/line.aspx"
        "?gid=1&lineid=ryomoline"
    )

    headers = {

        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        ),

        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,image/webp,"
            "*/*;q=0.8"
        ),

        "Accept-Language":
            "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",

        "Referer":
            "https://traininfo.jreast.co.jp/"

    }

    try:

        # ==========================================
        # JR東日本ページ取得
        # ==========================================

        response = requests.get(

            url,

            headers=headers,

            timeout=20

        )

        print(
            "JR東日本 HTTP status:",
            response.status_code
        )

        print(
            "JR東日本 response length:",
            len(response.text)
        )

        response.raise_for_status()


        # ==========================================
        # HTML解析
        # ==========================================

        soup = BeautifulSoup(

            response.text,

            "html.parser"

        )


        # ==========================================
        # ページ全体の文字を取得
        # ==========================================

        text = soup.get_text(

            " ",

            strip=True

        )


        print(
            "JR東日本ページ取得成功"
        )


        # ==========================================
        # 更新時刻
        # ==========================================

        updated = ""

        update_pattern = re.compile(

            r"\d{4}年\d{1,2}月\d{1,2}日"
            r"\s*\d{1,2}時\d{2}分"
            r"\s*現在"

        )

        match = update_pattern.search(text)

        if match:

            updated = match.group(0)


        # ==========================================
        # 初期状態
        # ==========================================

        status = "情報取得中"

        message = (
            "現在、両毛線の運行情報を確認しています。"
        )


        # ==========================================
        # 平常運転
        # ==========================================

        if "平常運転" in text:

            status = "平常運転"

            message = (
                "両毛線は平常通り運転しています。"
            )


        # ==========================================
        # 運転見合わせ
        # ==========================================

        if (

            "両毛線" in text

            and

            (
                "運転見合わせ" in text
                or
                "運転を見合わせ" in text
            )

        ):

            status = "運転見合わせ"

            index = text.find("両毛線")

            if index >= 0:

                message = text[
                    index:index + 300
                ]

            else:

                message = (
                    "両毛線は運転を見合わせています。"
                )


        # ==========================================
        # 運休
        # ==========================================

        elif (

            "両毛線" in text

            and

            "運休" in text

        ):

            status = "運休"

            index = text.find("両毛線")

            if index >= 0:

                message = text[
                    index:index + 300
                ]

            else:

                message = (
                    "両毛線で運休が発生しています。"
                )


        # ==========================================
        # 遅延
        # ==========================================

        elif (

            "両毛線" in text

            and

            (
                "遅延" in text
                or
                "遅れ" in text
            )

        ):

            status = "遅延"

            index = text.find("両毛線")

            if index >= 0:

                message = text[
                    index:index + 300
                ]

            else:

                message = (
                    "両毛線の一部列車に遅れが出ています。"
                )


        # ==========================================
        # デバッグログ
        # ==========================================

        print(
            "=========================================="
        )

        print(
            "両毛線 運行情報:",
            status
        )

        print(
            "更新時刻:",
            updated
        )

        print(
            "=========================================="
        )


        # ==========================================
        # JSONを返す
        # ==========================================

        return jsonify({

            "line": "両毛線",

            "status": status,

            "message": message,

            "updated": updated,

            "source": "JR東日本"

        })


    # ==========================================
    # JR東日本への接続エラー
    # ==========================================

    except requests.exceptions.RequestException as e:

        print(
            "JR東日本への接続エラー:",
            repr(e)
        )

        return jsonify({

            "line": "両毛線",

            "status": "情報取得中",

            "message":
                "JR東日本の運行情報を取得できません。",

            "updated": "",

            "source": "JR東日本",

            "error": str(e)

        })


    # ==========================================
    # その他のエラー
    # ==========================================

    except Exception as e:

        print(
            "運行情報取得エラー:",
            repr(e)
        )

        return jsonify({

            "line": "両毛線",

            "status": "情報取得中",

            "message":
                "運行情報の取得中にエラーが発生しました。",

            "updated": "",

            "source": "JR東日本",

            "error": str(e)

        })


# ==================================================
# 起動
# ==================================================

if __name__ == "__main__":

    app.run(

        debug=True,

        host="127.0.0.1",

        port=5000

    )
