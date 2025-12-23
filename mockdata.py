import pandas as pd
import random

records = []

ROOMS = ["male", "female"]
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

DAY_TO_INT = {
    "mon": 0, "tue": 1, "wed": 2,
    "thu": 3, "fri": 4, "sat": 5, "sun": 6
}

def get_hour_weights(day):
    if day in ["mon", "tue", "wed", "thu", "fri"]:
        return (
            [0.5]*7 +     # 0–6
            [1.5]*5 +     # 7–11
            [2.8]*5 +     # 12–16
            [4.5]*4 +     # 17–20
            [7.5]*3       # 21–23
        )
    else:
        return (
            [0.5]*9 +     # 0–8
            [2.0]*4 +     # 9–12
            [6.0]*4 +     # 13–16
            [4.0]*3 +     # 17–19
            [1.5]*4       # 20–23
        )

for _ in range(4000):
    room = random.choice(ROOMS)
    day = random.choice(DAYS)

    hour = random.choices(
        population=list(range(24)),
        weights=get_hour_weights(day)
    )[0]

    minute = random.choice([0, 10, 20, 30, 40, 50])

    machine_type = random.choices(
        ["wash", "dry"], weights=[2, 1]
    )[0]

    duration = (
        random.randint(40, 60)
        if machine_type == "wash"
        else random.randint(90, 120)
    )

    records.append({
        "room_type": room,
        "day_of_week": DAY_TO_INT[day],
        "hour": hour,
        "minute": minute,
        "machine_type": machine_type,
        "duration_min": duration
    })

df = pd.DataFrame(records)
df.to_csv("data/laundry_usage_mock.csv", index=False)

print("✅ 요일 기반 가상 데이터 생성 완료")