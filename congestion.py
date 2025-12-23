import pandas as pd
import joblib

# =============================
# 1. 모델 & 데이터 로드
# =============================
model = joblib.load("model/congestion_model.pkl")
slot_df = pd.read_csv("data/slot_df.csv")

FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "room_code",
    "last_1h",
    "last_3h"
]

DAY_NAME = {
    0: "월",
    1: "화",
    2: "수",
    3: "목",
    4: "금",
    5: "토",
    6: "일"
}

# =============================
# 2. slot_df 기반 예측
# (학습 때와 같은 분포의 입력 사용)
# =============================
results = []

for _, row in slot_df.iterrows():
    X_pred = pd.DataFrame([[
        row["hour"],
        row["day_of_week"],
        row["is_weekend"],
        row["room_code"],
        row["last_1h"],
        row["last_3h"]
    ]], columns=FEATURES)

    pred_level = model.predict(X_pred)[0]

    results.append({
        "요일": DAY_NAME[row["day_of_week"]],
        "시간": f'{int(row["hour"]):02d}:00',
        "세탁실": "남자" if row["room_code"] == 0 else "여자",
        "실제 혼잡도(학습용)": row["congestion"],
        "예측 혼잡도": pred_level
    })

pred_df = pd.DataFrame(results)

# =============================
# 3. 결과 확인
# =============================
print("🔍 혼잡도 예측 결과 (상위 20개)")
print(pred_df.head(20))

# 필요하면 저장
pred_df.to_csv("data/predicted_congestion.csv", index=False)

print("✅ slot_df 기반 혼잡도 예측 완료")