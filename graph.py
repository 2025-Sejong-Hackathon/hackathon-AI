import pandas as pd
import matplotlib.pyplot as plt

# 데이터 로드
df = pd.read_csv("predicted_congestion.csv")

# 요일 선택
DAY = "월"
day_df = df[df["요일"] == DAY]

# 시간 정렬
day_df["시간"] = day_df["시간"].str.slice(0, 2).astype(int)

male = day_df[day_df["세탁실"] == "남자"]
female = day_df[day_df["세탁실"] == "여자"]

# 그래프
plt.figure(figsize=(14, 6))

plt.bar(
    male["시간"] - 0.2,
    male["예측 혼잡도"],
    width=0.4,
    label="남자 세탁실"
)

plt.bar(
    female["시간"] + 0.2,
    female["예측 혼잡도"],
    width=0.4,
    label="여자 세탁실"
)

plt.xticks(range(24))
plt.ylim(0, 10)
plt.xlabel("시간대")
plt.ylabel("혼잡도 (1~10)")
plt.title(f"{DAY}요일 시간대별 세탁실 혼잡도")
plt.legend()
plt.grid(axis="y", alpha=0.3)

plt.show()