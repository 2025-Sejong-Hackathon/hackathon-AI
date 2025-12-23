import random
import pandas as pd
import numpy as np
from datetime import date

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# ======================
# 파라미터
# ======================
SIM_DAYS = 31
MINUTES = SIM_DAYS * 24 * 60

MEN_POP = 358
WOMEN_POP = 358

WASHERS = 10
DRYERS = 5

WASHES_PER_PERSON_PER_WEEK = 1.5
PEAK_MULTIPLIER = 2.0

WASH_TIME_MEAN = 45
WASH_TIME_SD = 5
DRY_TIME_MEAN = 100
DRY_TIME_SD = 10

P_USE_DRYER_AFTER_WASH = 0.8
P_FORGET = 0.3
FORGET_TIME_MEAN = 10
FORGET_TIME_SD = 5

MAX_DRY_QUEUE = 10
P_BAIL_BASE = 0.05
P_BAIL_PER_PERSON = 0.02

# ======================
# 유틸 함수
# ======================
def wash_duration():
    return max(10, int(random.gauss(WASH_TIME_MEAN, WASH_TIME_SD)))

def dry_duration():
    return max(20, int(random.gauss(DRY_TIME_MEAN, DRY_TIME_SD)))

def forget_duration():
    return max(0, int(random.gauss(FORGET_TIME_MEAN, FORGET_TIME_SD)))

def peak_weight(minute):
    hour = (minute // 60) % 24
    if hour < 18 or hour > 23:
        return 1.0
    x = (hour - 18) / 5.0
    return 1.0 + PEAK_MULTIPLIER * np.exp(-((x - 0.5) ** 2) / 0.08)

# ======================
# 시뮬레이션
# ======================
def simulate(room, pop):
    washers = [0] * WASHERS
    dryers = [0] * DRYERS

    wash_queue = 0
    dry_queue = 0
    records = []

    daily_arrivals = (pop * WASHES_PER_PERSON_PER_WEEK) / 7.0
    base_arrival_prob = daily_arrivals / (24 * 60)

    for t in range(MINUTES):
        day = t // 1440
        hour = (t // 60) % 24
        day_of_week = day % 7          # ✅ 추가
        is_weekend = 1 if day_of_week >= 5 else 0

        if random.random() < base_arrival_prob * peak_weight(t):
            wash_queue += 1

        for i in range(WASHERS):
            if washers[i] > 0:
                washers[i] -= 1
                if washers[i] == 0 and random.random() < P_USE_DRYER_AFTER_WASH:
                    dry_queue += 1

        for i in range(DRYERS):
            if dryers[i] > 0:
                dryers[i] -= 1

        if dry_queue > MAX_DRY_QUEUE:
            excess = dry_queue - MAX_DRY_QUEUE
            bail_prob = min(P_BAIL_BASE + excess * P_BAIL_PER_PERSON, 0.9)
            bailed = sum(1 for _ in range(dry_queue) if random.random() < bail_prob)
            dry_queue = max(0, dry_queue - bailed)

        for i in range(WASHERS):
            if washers[i] == 0 and wash_queue > 0:
                wash_queue -= 1
                washers[i] = wash_duration()
                if random.random() < P_FORGET:
                    washers[i] += forget_duration()

        for i in range(DRYERS):
            if dryers[i] == 0 and dry_queue > 0:
                dry_queue -= 1
                dryers[i] = dry_duration()
                if random.random() < P_FORGET:
                    dryers[i] += forget_duration()

        records.append({
            "hour": hour,
            "day_of_week": day_of_week,   # ✅ 추가
            "is_weekend": is_weekend,
            "running_washers": sum(w > 0 for w in washers),
            "room": room
        })

    return pd.DataFrame(records)

# ======================
# 혼잡도 라벨링
# ======================
def label_congestion(running):
    if running <= 2:
        return 0
    elif running <= 5:
        return 1
    elif running <=7:
        return 2
    else:
        return 3


# ======================
# 1️⃣ 데이터 생성
# ======================
print("▶ 시뮬레이션 중...")
df = pd.concat([
    simulate("men", MEN_POP),
    simulate("women", WOMEN_POP)
], ignore_index=True)

df["congestion"] = df["running_washers"].apply(label_congestion)

# ======================
# 2️⃣ 모델 학습 (미래 예측용)
# ======================
X = df[["hour", "day_of_week", "is_weekend"]]
y = df["congestion"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
model = Pipeline([
    ("scaler", StandardScaler()),
    ("mlp", MLPClassifier(
        hidden_layer_sizes=(64, 32),  # ⭐ 핵심
        activation="relu",
        solver="adam",
        alpha=0.001,                  # L2 regularization
        max_iter=500,
        early_stopping=True,
        random_state=42
    ))
])

print("▶ 모델 학습 중 (MLP)...")
model.fit(X_train, y_train)

from sklearn.metrics import classification_report

print("\n▶ 평가 결과")
print(classification_report(y_test, model.predict(X_test)))

# ======================
# 3️⃣ 날짜 선택 → 하루 전체 예측
# ======================
def predict_day(model, target_date: date):
    day_of_week = target_date.weekday()
    is_weekend = 1 if day_of_week >= 5 else 0

    rows = []
    for hour in range(24):
        rows.append({
            "hour": hour,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend
        })

    X_pred = pd.DataFrame(rows)
    preds = model.predict(X_pred)
    X_pred["predicted_congestion"] = preds
    return X_pred

# ======================
# 4️⃣ UI 출력용
# ======================
result = predict_day(model, date(2025, 12, 23))

peak_hour = result.loc[result["predicted_congestion"].idxmax(), "hour"]
recommend_hour = result.loc[result["predicted_congestion"].idxmin(), "hour"]

print("\n▶ UI 출력용 결과")
print(f"🔥 {peak_hour}시는 매우 혼잡할 예정이에요")
print(f"👍 {recommend_hour}시 이후 이용을 추천해요")


