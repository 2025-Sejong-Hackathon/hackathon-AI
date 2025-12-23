import pandas as pd
import json

# 데이터 로드
df = pd.read_csv("data/predicted_congestion.csv")

# 요일 매핑
DAY_KR_TO_EN = {
    "월": "mon",
    "화": "tue",
    "수": "wed",
    "목": "thu",
    "금": "fri",
    "토": "sat",
    "일": "sun"
}

# 결과 JSON 기본 구조
result = {
    "unit": "hour",
    "congestion_scale": "1-10",
    "week": {
        "mon": [],
        "tue": [],
        "wed": [],
        "thu": [],
        "fri": [],
        "sat": [],
        "sun": []
    }
}

# 요일별 처리
for day_kr, day_en in DAY_KR_TO_EN.items():
    day_df = df[df["요일"] == day_kr]

    for hour in range(24):
        time_str = f"{hour:02d}:00"

        male_row = day_df[
            (day_df["시간"] == time_str) &
            (day_df["세탁실"] == "남자")
        ]

        female_row = day_df[
            (day_df["시간"] == time_str) &
            (day_df["세탁실"] == "여자")
        ]

        if not male_row.empty and not female_row.empty:
            result["week"][day_en].append({
                "hour": hour,
                "male": int(male_row["예측 혼잡도"].values[0]),
                "female": int(female_row["예측 혼잡도"].values[0])
            })

# JSON 저장
with open("data/weekly_congestion.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("✅ 전 요일 혼잡도 JSON 생성 완료")