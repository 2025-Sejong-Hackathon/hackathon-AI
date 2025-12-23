import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split
import joblib

# =============================
# 1. 원본 데이터 로드
# =============================
df = pd.read_csv("data/laundry_usage_mock.csv")

# =============================
# 2. 요일 × 시간 slot_df 생성
# =============================
records = []

for room in ["male", "female"]:
    for day in range(7):
        for hour in range(24):
            slot = df[
                (df.room_type == room) &
                (df.day_of_week == day) &
                (df.hour == hour)
            ]

            wash_cnt = slot[slot.machine_type == "wash"].shape[0]
            dry_cnt  = slot[slot.machine_type == "dry"].shape[0]

            weighted_usage = wash_cnt * 50 + dry_cnt * 120

            records.append({
                "room_type": room,
                "day_of_week": day,
                "hour": hour,
                "weighted_usage": weighted_usage
            })

slot_df = pd.DataFrame(records)

# =============================
# 3. 혼잡도 1~10 생성
# =============================
slot_df["congestion"] = (
    pd.qcut(slot_df["weighted_usage"], q=10, labels=False) + 1
)

# =============================
# 4. Feature Engineering
# =============================
slot_df["is_weekend"] = slot_df["day_of_week"].isin([5, 6]).astype(int)
slot_df["room_code"] = slot_df["room_type"].map({"male": 0, "female": 1})

slot_df["last_1h"] = (
    slot_df.groupby("room_type")["weighted_usage"]
    .shift(1)
    .fillna(0)
)

slot_df["last_3h"] = (
    slot_df.groupby("room_type")["weighted_usage"]
    .rolling(3).mean()
    .reset_index(0, drop=True)
    .fillna(0)
)

FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "room_code",
    "last_1h",
    "last_3h"
]

X = slot_df[FEATURES]
y = slot_df["congestion"]

# =============================
# 5. 모델 학습
# =============================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = LGBMClassifier(
    objective="multiclass",
    num_class=10,
    n_estimators=200,
    learning_rate=0.05,
    random_state=42
)

model.fit(X_train, y_train)

# =============================
# 6. 저장
# =============================
slot_df.to_csv("data/slot_df.csv", index=False)
joblib.dump(model, "model/congestion_model.pkl")

print("✅ slot_df 생성 + 혼잡도 모델 학습 완료")