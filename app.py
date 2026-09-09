from flask import Flask, jsonify, render_template
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re

app = Flask(__name__)

JSON_FILE = Path(__file__).with_name("timetable.json")


# ==================================================
# 時刻表JSON
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

        "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"

    }


    try:

        # ==========================================
        # JR東日本ページ取得
        # ==========================================

        response = requests.get(

            url,

            headers=headers,

            timeout=10

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
        # ページ内の文字を取得
        # ==========================================

        lines = []

        for line in soup.get_text(
            "\n",
            strip=True
        ).splitlines():

            line = line.strip()

            if line:

                lines.append(line)


        # ==========================================
        # 更新時刻
        # ==========================================

        updated = ""


        update_pattern = re.compile(

            r"\d{4}年\d{1,2}月\d{1,2}日"
            r"\s+\d{1,2}時\d{2}分"
            r"\s+現在"

        )


        for line in lines:

            match = update_pattern.search(line)

            if match:

                updated = match.group(0)

                break


        # ==========================================
        # 「運行情報・運休情報」をすべて探す
        # ==========================================

        operation_indexes = []

        for i, line in enumerate(lines):

            if "運行情報・運休情報" in line:

                operation_indexes.append(i)


        # ==========================================
        # 見つからない場合
        # ==========================================

        if not operation_indexes:

            return jsonify({

                "line": "両毛線",

                "status": "情報取得中",

                "message":
                    "現在、両毛線の運行情報を確認しています。",

                "updated": updated,

                "source": "JR東日本"

            })


        # ==========================================
        # 重要
        #
        # 最後に出てくる
        # 「運行情報・運休情報」を使用する
        #
        # 現在のJR東日本ページでは
        #
        # 運行情報・運休情報
        # ↓
        # 平常運転
        # ↓
        # 振替輸送情報
        #
        # という構造になっている
        # ==========================================

        operation_index = operation_indexes[-1]


        # ==========================================
        # 実際の運行情報だけ取得
        # ==========================================

        operation_lines = []


        for line in lines[operation_index + 1:]:

            # 次のセクション
            if "振替輸送情報" in line:

                break

            if "遅延証明書" in line:

                break

            operation_lines.append(line)


        # ==========================================
        # 不要な文字を除去
        # ==========================================

        clean_lines = []


        for line in operation_lines:

            line = line.strip()


            if not line:

                continue


            if line == "更新":

                continue


            clean_lines.append(line)


        # ==========================================
        # 運行情報を文章にする
        # ==========================================

        operation_text = " ".join(
            clean_lines
        )


        # デバッグ用
        print(
            "=========================================="
        )

        print(
            "JR東日本 運行情報:",
            operation_text
        )

        print(
            "=========================================="
        )


        # ==========================================
        # 平常運転
        # ==========================================

        if "平常運転" in operation_text:

            status = "平常運転"

            message = (
                "両毛線は平常通り運転しています。"
            )


        # ==========================================
        # 運転見合わせ
        # ==========================================

        elif (
            "運転見合わせ" in operation_text
            or
            "運転を見合わせ" in operation_text
        ):

            status = "運転見合わせ"

            message = operation_text


        # ==========================================
        # 運休
        # ==========================================

        elif "運休" in operation_text:

            status = "運休"

            message = operation_text


        # ==========================================
        # 遅延
        # ==========================================

        elif (
            "遅延" in operation_text
            or
            "遅れ" in operation_text
        ):

            status = "遅延"

            message = operation_text


        # ==========================================
        # その他
        # ==========================================

        else:

            status = "情報取得中"

            message = (
                "現在、両毛線の運行情報を確認しています。"
            )


        # ==========================================
        # JSON
        # ==========================================

        return jsonify({

            "line": "両毛線",

            "status": status,

            "message": message,

            "updated": updated,

            "source": "JR東日本"

        })


    # ==========================================
    # 通信エラー
    # ==========================================

    except requests.exceptions.RequestException as e:

        print(
            "JR東日本への接続エラー:",
            e
        )


        return jsonify({

            "line": "両毛線",

            "status": "情報取得中",

            "message":
                "JR東日本の運行情報を取得できません。",

            "updated": "",

            "source": "JR東日本"

        })


    # ==========================================
    # その他のエラー
    # ==========================================

    except Exception as e:

        print(
            "運行情報取得エラー:",
            e
        )


        return jsonify({

            "line": "両毛線",

            "status": "情報取得中",

            "message":
                "運行情報の取得中にエラーが発生しました。",

            "updated": "",

            "source": "JR東日本"

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