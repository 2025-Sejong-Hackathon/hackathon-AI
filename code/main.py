from fastapi import FastAPI
from datetime import datetime
import requests

from simulate import predict_day, model

app = FastAPI(
    title="Laundry AI API",
    description="빨래지수 + 세탁실 혼잡도 예측 API",
    version="1.0"
)

# ======================
# 1️⃣ 혼잡도 예측 API
# ======================
@app.get("/predict")
def predict(date: str):
    target_date = datetime.strptime(date, "%Y-%m-%d").date()

    result = predict_day(model, target_date)

    peak_hour = int(
        result.loc[result["predicted_congestion"].idxmax(), "hour"]
    )
    recommend_hour = int(
        result.loc[result["predicted_congestion"].idxmin(), "hour"]
    )

    return {
        "date": date,
        "peak_message": f"🔥 {peak_hour}시는 매우 혼잡할 예정이에요",
        "recommend_message": f"👍 {recommend_hour}시 이후 이용을 추천해요",
        "timeline": result[
            ["hour", "predicted_congestion"]
        ].to_dict(orient="records")
    }


# ======================
# 2️⃣ 오늘의 빨래지수 API
# ======================
SERVICE_KEY = "5ZtcPG9SqpW07BI98G3LUy3ajs6wkbPtFUU5icGD3JhEFtBxXK2eCfnibYLdFi9oZYXCLAv2K7cBmOjzFjQWjg=="
NX, NY = 61, 126
BASE_TIMES = [200, 500, 800, 1100, 1400, 1700, 2000, 2300]

def laundry_comment(index):
    if index >= 70:
        return "오늘 빨래하기 좋아요 ☀️"
    elif index >= 40:
        return "오늘 빨래하기 보통이에요 🌥️"
    else:
        return "오늘 빨래하기 안 좋아요 ☔"

def laundry_index(temp, humidity, rain):
    score = 100
    score -= humidity * 0.4
    score -= rain * 20
    score += (temp - 20) * 1.5
    return max(0, min(100, score))

@app.get("/laundry/today")
def get_laundry_message():
    now = datetime.now()
    today = now.strftime("%Y%m%d")
    current_time = int(now.strftime("%H%M"))

    base_time = None
    for t in reversed(BASE_TIMES):
        if current_time >= t:
            base_time = f"{t:04d}"
            break
    if base_time is None:
        base_time = "2300"

    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        "serviceKey": SERVICE_KEY,
        "numOfRows": 1000,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": today,
        "base_time": base_time,
        "nx": NX,
        "ny": NY
    }

    res = requests.get(url, params=params).json()
    items = res["response"]["body"]["items"]["item"]

    weather = {}
    for item in items:
        if item["fcstDate"] == today:
            cat = item["category"]
            if cat in ["TMP", "REH", "PCP"] and cat not in weather:
                weather[cat] = item["fcstValue"]

    temp = float(weather.get("TMP", 20))
    humidity = float(weather.get("REH", 50))
    rain = 0 if weather.get("PCP", "강수없음") == "강수없음" else float(weather["PCP"])

    index = laundry_index(temp, humidity, rain)

    return {
        "laundry_message": laundry_comment(index)
    }