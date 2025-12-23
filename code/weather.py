import requests
from datetime import datetime

# 설정
SERVICE_KEY = "5ZtcPG9SqpW07BI98G3LUy3ajs6wkbPtFUU5icGD3JhEFtBxXK2eCfnibYLdFi9oZYXCLAv2K7cBmOjzFjQWjg=="

NX, NY = 61, 126   # 광진구 화양동

now = datetime.now()
today = now.strftime("%Y%m%d")
current_time = int(now.strftime("%H%M"))

# 1. 문서 기준 base_time 선택
BASE_TIMES = [200, 500, 800, 1100, 1400, 1700, 2000, 2300]

base_time = None
for t in reversed(BASE_TIMES):
    if current_time >= t:
        base_time = f"{t:04d}"
        break

# 새벽(00~01시)는 전날 23시 예보
if base_time is None:
    base_time = "2300"

print(f"▶ 사용 base_time: {base_time}")


# 2. API 호출 (문서 명세 그대로)
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

headers = {
    "User-Agent": "Mozilla/5.0 (LaundryAI/1.0)"
}

response = requests.get(url, params=params, headers=headers)
data = response.json()

# 3. 응답 검증 (문서 c)항)
response_root = data.get("response", {})
header = response_root.get("header", {})

if header.get("resultCode") != "00":
    print("❌ API ERROR:", header)
    exit()

body = response_root.get("body")
if body is None:
    print("❌ body 없음 (해당 발표시각 데이터 없음)")
    exit()

items = body["items"]["item"]

# 4. 오늘 예보값 중 하나 추출
weather = {}

for item in items:
    if item["fcstDate"] == today:
        cat = item["category"]
        if cat in ["TMP", "REH", "PCP"] and cat not in weather:
            weather[cat] = item["fcstValue"]

temp = float(weather.get("TMP", 20))
humidity = float(weather.get("REH", 50))

pcp = weather.get("PCP", "강수없음")
rain = 0 if pcp == "강수없음" else float(pcp)

# 5. 빨래지수
def laundry_index(temp, humidity, rain):
    score = 100
    score -= humidity * 0.4
    score -= rain * 20
    score += (temp - 20) * 1.5
    return max(0, min(100, score))

index = laundry_index(temp, humidity, rain)

def laundry_message(index):
    if index >= 70:
        return "오늘 빨래하기 좋아요 ☀️"
    elif index >= 40:
        return "오늘 빨래하기 보통이에요 🌥️"
    else:
        return "오늘 빨래하기 안 좋아요 ☔️"


# 6. 출력
print(f"🧺 빨래지수: {index:.1f}")
print("➡", laundry_message(index))