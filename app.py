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
# 両毛線 運行情報
#
# JR東日本はRenderから403になるため、
# Yahoo!路線情報を使用
# ==================================================

@app.route("/api/operation")
def api_operation():

    url = (
        "https://transit.yahoo.co.jp/"
        "diainfo/168/0"
    )

    headers = {

        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        ),

        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,"
            "image/avif,image/webp,"
            "*/*;q=0.8"
        ),

        "Accept-Language":
            "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"

    }

    try:

        # ==========================================
        # Yahoo!路線情報を取得
        # ==========================================

        response = requests.get(

            url,

            headers=headers,

            timeout=20

        )

        print(
            "Yahoo!路線情報 HTTP status:",
            response.status_code
        )

        print(
            "Yahoo! response length:",
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
        # ページの文字列
        # ==========================================

        text = soup.get_text(

            " ",

            strip=True

        )


        print(
            "Yahoo!路線情報ページ取得成功"
        )


        # ==========================================
        # 更新時刻
        # ==========================================

        updated = ""

        update_patterns = [

            re.compile(
                r"\d{1,2}月\d{1,2}日"
                r"\s*\d{1,2}時\d{2}分"
                r"\s*更新"
            ),

            re.compile(
                r"\d{1,2}月\d{1,2}日"
                r"\s*\d{1,2}時\d{2}分"
                r"\s*現在"
            )

        ]

        for pattern in update_patterns:

            match = pattern.search(text)

            if match:

                updated = match.group(0)

                break


        # ==========================================
        # 両毛線部分を探す
        # ==========================================

        ryomo_index = text.find("両毛線")


        if ryomo_index == -1:

            print(
                "Yahoo!ページ内に両毛線が見つかりません"
            )

            return jsonify({

                "line": "両毛線",

                "status": "情報取得中",

                "message":
                    "両毛線の運行情報を確認しています。",

                "updated": updated,

                "source":
                    "Yahoo!路線情報"

            })


        # ==========================================
        # 両毛線周辺の文章
        # ==========================================

        ryomo_text = text[
            ryomo_index:
            ryomo_index + 500
        ]


        print(
            "両毛線周辺情報:",
            ryomo_text
        )


        # ==========================================
        # 初期値
        # ==========================================

        status = "情報取得中"

        message = (
            "現在、両毛線の運行情報を確認しています。"
        )


        # ==========================================
        # 平常運転
        # ==========================================

        if (

            "平常運転" in ryomo_text

            or

            "事故・遅延に関する情報はありません"
            in ryomo_text

        ):

            status = "平常運転"

            message = (
                "両毛線は平常通り運転しています。"
            )


        # ==========================================
        # 運転見合わせ
        # ==========================================

        elif (

            "運転見合わせ" in ryomo_text

            or

            "運転を見合わせ" in ryomo_text

        ):

            status = "運転見合わせ"

            message = (
                ryomo_text[:300]
            )


        # ==========================================
        # 運休
        # ==========================================

        elif "運休" in ryomo_text:

            status = "運休"

            message = (
                ryomo_text[:300]
            )


        # ==========================================
        # 遅延
        # ==========================================

        elif (

            "遅延" in ryomo_text

            or

            "遅れ" in ryomo_text

            or

            "運転状況" in ryomo_text

        ):

            status = "遅延"

            message = (
                ryomo_text[:300]
            )


        # ==========================================
        # デバッグ
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
        # JSON
        # ==========================================

        return jsonify({

            "line": "両毛線",

            "status": status,

            "message": message,

            "updated": updated,

            "source":
                "Yahoo!路線情報"

        })


    # ==========================================
    # 通信エラー
    # ==========================================

    except requests.exceptions.RequestException as e:

        print(
            "Yahoo!路線情報への接続エラー:",
            repr(e)
        )

        return jsonify({

            "line": "両毛線",

            "status": "情報取得中",

            "message":
                "運行情報を取得できません。",

            "updated": "",

            "source":
                "Yahoo!路線情報",

            "error":
                str(e)

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

            "source":
                "Yahoo!路線情報",

            "error":
                str(e)

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
