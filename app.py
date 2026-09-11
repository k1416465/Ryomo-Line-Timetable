from flask import Flask, jsonify, render_template
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re
from urllib.parse import unquote

app = Flask(__name__)

JSON_FILE = Path(__file__).with_name("timetable.json")


# ==================================================
# 時刻表読み込み
# ==================================================

def load_timetable():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ==================================================
# 列車データを自動補正
# ==================================================

def normalize_train(item):
    """
    timetable.json のデータを自動的に正しい形へ補正する。

    正常なデータ：
        train_number = 484M
        type = 普通
        cars = 4

    崩れたデータ：
        train_number = 普通
        type = ""
        cars = 421M

    のような場合でも正しく処理する。
    """

    train = dict(item)

    train_number = str(
        train.get("train_number", "") or ""
    ).strip()

    train_type = str(
        train.get("type", "") or ""
    ).strip()

    cars = train.get("cars", "")

    # ==================================================
    # 崩れたデータの両数対応表
    # ==================================================

    car_mapping = {
        "421M": 6,
        "423M": 4,
        "425M": 6,
        "427M": 4,
        "429M": 4,
        "431M": 4,
        "433M": 6,
        "437M": 4,
        "439M": 4,
        "441M": 6,
        "443M": 4,
        "445M": 4,
        "447M": 4,
        "449M": 4,
        "451M": 4,
        "453M": 6,
        "455M": 6,
        "459M": 4,
        "461M": 6,
        "463M": 6,
        "465M": 4,
        "467M": 6,
        "469M": 6,
        "471M": 4,
        "475M": 4,
        "479M": 6
    }

    # ==================================================
    # 崩れたデータを修正
    #
    # train_number = 普通
    # cars = 421M
    # ==================================================

    if (
        train_number == "普通"
        and
        isinstance(cars, str)
        and
        re.fullmatch(r"\d+M", cars.strip())
    ):

        # 本当の列車番号
        real_train_number = cars.strip()

        train["train_number"] = real_train_number

        # 種別が空なら普通
        if not train_type:
            train["type"] = "普通"

        # 列車番号から両数を取得
        if real_train_number in car_mapping:

            train["cars"] = car_mapping[
                real_train_number
            ]

        else:

            train["cars"] = None

    else:

        # 正常なデータ
        train["train_number"] = train_number

        if not train_type:
            train["type"] = "普通"

    return train


# ==================================================
# 駅の英語表記
# ==================================================

STATION_ENGLISH = {
    "高崎": "Takasaki",
    "高崎問屋町": "Takasakitonyamachi",
    "井野": "Ino",
    "新前橋": "Shin-Maebashi",
    "前橋": "Maebashi",
    "前橋大島": "Maebashiōshima",
    "駒形": "Komagata",
    "伊勢崎": "Isesaki",
    "国定": "Kunisada",
    "岩宿": "Iwajuku",
    "桐生": "Kiryū",
    "小俣": "Omata",
    "山前": "Yamamae",
    "足利": "Ashikaga",
    "あしかがフラワーパーク": "Ashikaga Flower Park",
    "富田": "Tomita",
    "佐野": "Sano",
    "岩舟": "Iwafune",
    "大平下": "Ōhirashita",
    "栃木": "Tochigi",
    "思川": "Omoigawa",
    "小山": "Oyama"
}


# ==================================================
# 列車番号取得
# ==================================================

def get_train_number(item):

    train = normalize_train(item)

    return str(
        train.get("train_number", "") or ""
    ).strip()


# ==================================================
# トップページ
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

    normalized_trains = []

    for item in data.get("trains", []):

        normalized_trains.append(
            normalize_train(item)
        )

    data["trains"] = normalized_trains

    return jsonify(data)


# ==================================================
# 駅時刻表
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
# 列車詳細
# ==================================================

@app.route("/train/<path:train_number>")
def train_detail(train_number):

    train_number = unquote(
        train_number
    ).strip()

    data = load_timetable()

    trains = data.get(
        "trains",
        []
    )

    train = None

    # ==================================================
    # 列車を検索
    # ==================================================

    for item in trains:

        normalized = normalize_train(item)

        current_number = str(
            normalized.get(
                "train_number",
                ""
            ) or ""
        ).strip()

        if current_number == train_number:

            train = normalized

            break

    # ==================================================
    # 列車が見つからない場合
    # ==================================================

    if train is None:

        print(
            "列車が見つかりません:",
            train_number
        )

        return "列車が見つかりません", 404


    # ==================================================
    # 停車駅
    # ==================================================

    stops = []

    for station_name, station_data in (
        train.get("stops", {}) or {}
    ).items():

        station_data = station_data or {}

        arrival = (
            station_data.get("arrival")
            or ""
        )

        departure = (
            station_data.get("departure")
            or ""
        )

        stops.append({

            "name": station_name,

            "english": STATION_ENGLISH.get(
                station_name,
                station_name
            ),

            "arrival": arrival,

            "departure": departure

        })


    # ==================================================
    # 種別
    # ==================================================

    type_name = (
        train.get("type")
        or
        "普通"
    )

    type_english_map = {

        "普通": "Local",

        "快速": "Rapid",

        "特急": "Limited Express"

    }

    type_english = type_english_map.get(

        type_name,

        type_name

    )


    # ==================================================
    # 行先
    # ==================================================

    destination = (

        train.get("destination")
        or
        ""

    )

    destination_english_map = {

        "高崎": "Takasaki",

        "小山": "Oyama",

        "前橋": "Maebashi",

        "桐生": "Kiryū",

        "伊勢崎": "Isesaki",

        "足利": "Ashikaga",

        "栃木": "Tochigi",

        "佐野": "Sano"

    }

    destination_english = (
        destination_english_map.get(
            destination,
            destination
        )
    )


    # ==================================================
    # 両数
    # ==================================================

    cars = train.get("cars")


    # 数字の場合
    if isinstance(cars, int):

        cars = cars


    # "4" のような文字列の場合
    elif (

        isinstance(cars, str)

        and

        cars.strip().isdigit()

    ):

        cars = int(
            cars.strip()
        )


    # "421M" のような列車番号が
    # 入っていた場合
    elif (

        isinstance(cars, str)

        and

        re.fullmatch(
            r"\d+M",
            cars.strip()
        )

    ):

        cars = None


    else:

        cars = None


    # ==================================================
    # 列車詳細ページを表示
    # ==================================================

    return render_template(

        "train_detail.html",

        train=train,

        train_number=get_train_number(
            train
        ),

        station_id="sano",

        stops=stops,

        type_english=type_english,

        destination_english=destination_english,

        cars=cars

    )


# ==================================================
# 設定
# ==================================================

@app.route("/settings")
def settings():

    return render_template(
        "settings.html"
    )


# ==================================================
# 運行情報
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


        soup = BeautifulSoup(

            response.text,

            "html.parser"

        )


        text = soup.get_text(

            " ",

            strip=True

        )


        print(
            "Yahoo!路線情報ページ取得成功"
        )


        # ==================================================
        # 更新時刻
        # ==================================================

        updated = ""


        update_patterns = [

            re.compile(

                r"\d{1,2}月\d{1,2}日\s*"
                r"\d{1,2}時\d{2}分\s*更新"

            ),

            re.compile(

                r"\d{1,2}月\d{1,2}日\s*"
                r"\d{1,2}時\d{2}分\s*現在"

            )

        ]


        for pattern in update_patterns:

            match = pattern.search(text)

            if match:

                updated = match.group(0)

                break


        # ==================================================
        # 両毛線部分を取得
        # ==================================================

        ryomo_index = text.find(
            "両毛線"
        )


        if ryomo_index == -1:

            return jsonify({

                "line": "両毛線",

                "status": "情報取得中",

                "message":
                    "両毛線の運行情報を確認しています。",

                "updated": updated,

                "source": "Yahoo!路線情報"

            })


        ryomo_text = text[

            ryomo_index:
            ryomo_index + 500

        ]


        status = "情報取得中"


        message = (

            "現在、両毛線の運行情報を"
            "確認しています。"

        )


        # ==================================================
        # 平常運転
        # ==================================================

        if (

            "平常運転" in ryomo_text

            or

            "事故・遅延に関する情報はありません"
            in ryomo_text

        ):

            status = "平常運転"

            message = (

                "両毛線は平常通り"
                "運転しています。"

            )


        # ==================================================
        # 運転見合わせ
        # ==================================================

        elif (

            "運転見合わせ" in ryomo_text

            or

            "運転を見合わせ" in ryomo_text

        ):

            status = "運転見合わせ"

            message = ryomo_text[:300]


        # ==================================================
        # 運休
        # ==================================================

        elif "運休" in ryomo_text:

            status = "運休"

            message = ryomo_text[:300]


        # ==================================================
        # 遅延
        # ==================================================

        elif (

            "遅延" in ryomo_text

            or

            "遅れ" in ryomo_text

            or

            "運転状況" in ryomo_text

        ):

            status = "遅延"

            message = ryomo_text[:300]


        # ==================================================
        # 結果
        # ==================================================

        return jsonify({

            "line": "両毛線",

            "status": status,

            "message": message,

            "updated": updated,

            "source": "Yahoo!路線情報"

        })


    except requests.exceptions.RequestException as e:

        return jsonify({

            "line": "両毛線",

            "status": "情報取得中",

            "message":
                "運行情報を取得できません。",

            "updated": "",

            "source": "Yahoo!路線情報",

            "error": str(e)

        })


    except Exception as e:

        return jsonify({

            "line": "両毛線",

            "status": "情報取得中",

            "message":
                "運行情報の取得中に"
                "エラーが発生しました。",

            "updated": "",

            "source": "Yahoo!路線情報",

            "error": str(e)

        })


# ==================================================
# Flask起動
# ==================================================

if __name__ == "__main__":

    app.run(

        debug=True,

        host="127.0.0.1",

        port=5000

    )