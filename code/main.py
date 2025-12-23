from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import requests
from .simulate import predict_day, get_model
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import json
from typing import List, Dict, Any
import os

# ======================
# 매칭 모델 설정
# ======================
W_P = 4  # Personality (성격/예민)
W_S = 3  # Sleep (수면)
W_C = 2  # Cleanliness (청결)

weight_A = {
    "sleep_habit": W_S, "wake_up": W_S, "activity_time": W_S, "out_return": W_S,
    "clean_immediate": W_C, "desk_status": W_C, "clean_cycle": W_C, "other_seat_tol": W_C,
    "phone_noise": W_P, "light_sensitivity": W_P, "key_mouse_noise": W_P, "alarm_habit": W_P,
    "social_willingness": W_P, "friend_invite": W_P, "dorm_stay": W_P, "space_privacy": W_P
}

class DormMatchAI_Server:
    def __init__(self, data_path):
        self.data_path = data_path
        self.users_df = None
        self.weighted_features_df = None
        self.weights = weight_A
        self.scaler = MinMaxScaler()
        self.kmeans = KMeans(n_clusters=12, random_state=42)
        
        self.text_map = {
            "sleep_habit": {0: "12시전 취침", 1: "새벽 취침"},
            "wake_up": {0: "늦잠/오후 기상", 1: "아침 기상"},
            "activity_time": {0: "낮 활동(아침형)", 1: "밤 활동(올빼미)"},
            "out_return": {0: "상관없음", 1: "연락/알림 필요"},
            "dorm_stay": {0: "주로 밖에서 보냄", 1: "주로 기숙사에 있음"},
            "clean_cycle": {0: "매일 청소", 1: "3일마다", 2: "1주마다", 3: "1달마다"},
            "clean_immediate": {0: "나중에 치움", 1: "바로바로 치움"},
            "desk_status": {0: "어수선함(인간미)", 1: "깔끔하게 정리"},
            "other_seat_tol": {0: "상관없음", 1: "내 자리 건들지마"},
            "phone_noise": {0: "안에서 통화 OK", 1: "밖에서 통화"},
            "light_sensitivity": {0: "불 켜도 잘 잠", 1: "불 꺼야 잠"},
            "key_mouse_noise": {0: "상관없음", 1: "무소음 선호"},
            "alarm_habit": {0: "잘 못 듣는 편", 1: "바로 끄고 일어남"},
            "space_privacy": {0: "물건 공유 가능", 1: "철저하게 분리"},
            "social_willingness": {0: "개인주의(혼자)", 1: "친목 도모(함께)"},
            "friend_invite": {0: "친구 초대 자제", 1: "친구 초대 환영"},
            "is_smoker": {True: "흡연자", False: "비흡연자"},
            "wants_smoker": {True: "흡연 룸메 OK", False: "비흡연 룸메 선호"},
            "is_drinker": {True: "음주 즐김", False: "비음주"},
            "wants_drinker": {True: "음주 룸메 OK", False: "비음주 룸메 선호"},
            "sensitive_heat": {True: "더위 많이 탐", False: "더위 잘 참음"},
            "sensitive_cold": {True: "추위 많이 탐", False: "추위 잘 참음"}
        }
        
        self.col_name_map = {
            "sleep_habit": "취침시간", "wake_up": "기상시간", "activity_time": "주활동시간",
            "dorm_stay": "기숙사 체류", "out_return": "외출/복귀 연락",
            "clean_cycle": "청소주기", "clean_immediate": "정리습관", 
            "desk_status": "책상상태", "other_seat_tol": "타인영역 허용",
            "phone_noise": "통화소음", "light_sensitivity": "수면 등(Light)", 
            "key_mouse_noise": "타건/마우스 소음", "alarm_habit": "알람 습관",
            "space_privacy": "공용물품/공간",
            "social_willingness": "사회성", "friend_invite": "친구 초대",
            "is_smoker": "흡연여부", "wants_smoker": "흡연룸메 허용",
            "is_drinker": "음주여부", "wants_drinker": "음주룸메 허용",
            "sensitive_heat": "더위 민감도", "sensitive_cold": "추위 민감도"
        }
        
        self.feature_cols = list(self.weights.keys())
    
    def load_and_train(self):
        print("⏳ 데이터 로딩 및 모델 학습 시작...")
        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        required_fields = ['student_id', 'gender'] + self.feature_cols
        valid_data = [record for record in data if all(field in record for field in required_fields)]
        
        print(f"✅ 전체 {len(data)}개 중 유효한 데이터 {len(valid_data)}개 로드")
        
        if len(valid_data) == 0:
            raise ValueError("유효한 데이터가 없습니다.")
        
        self.users_df = pd.DataFrame(valid_data)
        features_norm = self.scaler.fit_transform(self.users_df[self.feature_cols])
        
        weighted_data = features_norm.copy()
        for i, col in enumerate(self.feature_cols):
            weighted_data[:, i] *= self.weights[col]
        
        self.weighted_features_df = pd.DataFrame(weighted_data, columns=self.feature_cols, index=self.users_df.index)
        self.users_df['cluster_id'] = self.kmeans.fit_predict(self.weighted_features_df)
        print("✅ 모델 학습 완료!")
    
    def preprocess_input(self, user_data: dict):
        input_df = pd.DataFrame([user_data])
        norm_data = self.scaler.transform(input_df[self.feature_cols])
        
        weighted_input = norm_data.copy()
        for i, col in enumerate(self.feature_cols):
            weighted_input[:, i] *= self.weights[col]
        
        return pd.DataFrame(weighted_input, columns=self.feature_cols)
    
    def explain_match_detail(self, user_data: dict, partner_row: pd.Series):
        match_items = []
        mismatch_items = []
        
        for col in self.feature_cols:
            val_me = user_data[col]
            val_partner = partner_row[col]
            col_name_kr = self.col_name_map.get(col, col)
            
            if val_me == val_partner:
                match_items.append(col_name_kr)
            else:
                my_val_txt = self.text_map.get(col, {}).get(val_me, str(val_me))
                pt_val_txt = self.text_map.get(col, {}).get(val_partner, str(val_partner))
                mismatch_items.append({
                    "category": col_name_kr,
                    "my_value": my_val_txt,
                    "mate_value": pt_val_txt
                })
        
        return match_items, mismatch_items
    
    def recommend(self, user_data: dict, count=5, page=1):
        target_student_id = user_data['student_id']
        target_gender = user_data['gender']
        
        target_vec = self.preprocess_input(user_data)
        target_cluster = self.kmeans.predict(target_vec)[0]
        
        candidates = self.users_df[
            (self.users_df['student_id'] != target_student_id) &
            (self.users_df['gender'] == target_gender) &
            (self.users_df['cluster_id'] == target_cluster)
        ].copy()
        
        if len(candidates) < count*page:
            candidates = self.users_df[
                (self.users_df['student_id'] != target_student_id) &
                (self.users_df['gender'] == target_gender)
            ].copy()
        
        if len(candidates) == 0:
            return []
        
        candidate_vecs = self.weighted_features_df.loc[candidates.index]
        sims = cosine_similarity(target_vec, candidate_vecs)[0]
        
        candidates['match_score'] = sims * 100
        sorted_candidates = candidates.sort_values(by='match_score', ascending=False)
        
        start_idx = (page - 1) * count
        end_idx = start_idx + count
        top_matches = sorted_candidates.iloc[start_idx:end_idx]
        
        results = []
        for _, row in top_matches.iterrows():
            m_items, mm_items = self.explain_match_detail(user_data, row)
            results.append({
                "student_id": row['student_id'],
                "major": row['major'],
                "match_rate": round(row['match_score'], 1),
                "is_smoker": bool(row['is_smoker']),
                "is_drinker": bool(row['is_drinker']),
                "sensitive_heat": bool(row.get('sensitive_heat', False)),
                "sensitive_cold": bool(row.get('sensitive_cold', False)),
                "match_items": m_items,
                "mismatch_items": mm_items
            })
        
        return results

# Pydantic 모델
class StudentInput(BaseModel):
    student_id: str
    age: int
    gender: str
    major: str
    is_smoker: bool
    wants_smoker: bool
    is_drinker: bool
    wants_drinker: bool
    sensitive_heat: bool
    sensitive_cold: bool
    sleep_habit: int
    wake_up: int
    activity_time: int
    clean_immediate: int
    desk_status: int
    clean_cycle: int
    out_return: int
    other_seat_tol: int
    phone_noise: int
    light_sensitivity: int
    key_mouse_noise: int
    space_privacy: int
    alarm_habit: int
    social_willingness: int
    friend_invite: int
    dorm_stay: int

app = FastAPI(
    title="Dormitory AI Service",
    description="세탁실 혼잡도 예측 + 빨래지수 + 룸메이트 매칭 AI API",
    version="2.0"
)

# 전역 매칭 엔진 및 세탁 모델
matching_engine = None
laundry_model = None

@app.on_event("startup")
def startup_event():
    global matching_engine, laundry_model
    print("🚀 서버 시작 중...")
    
    # 매칭 모델 로드
    dummy_file_path = "data/dormitory_users.json"
    matching_engine = DormMatchAI_Server(dummy_file_path)
    matching_engine.load_and_train()
    
    # 세탁 모델 로드 (lazy loading)
    laundry_model = get_model()
    
    print("✅ 모든 모델 로드 완료!")

# ======================
# 헬스 체크
# ======================
@app.get("/health")
def health_check():
    if matching_engine is None:
        raise HTTPException(status_code=503, detail="Service Unavailable - Model not loaded")
    return {"status": "healthy", "service": "dormitory-ai-service"}

# ======================
# 룸메이트 매칭 API
# ======================
@app.post("/recommend")
def get_recommendation(user_input: StudentInput, count: int = 5, page: int = 1):
    if matching_engine is None:
        raise HTTPException(status_code=500, detail="Model is not loaded")
    
    try:
        user_dict = user_input.dict()
        
        gender_map = {
            "MALE": "남성",
            "FEMALE": "여성",
            "male": "남성",
            "female": "여성"
        }
        
        if user_dict["gender"] in gender_map:
            user_dict["gender"] = gender_map[user_dict["gender"]]
        
        recommendations = matching_engine.recommend(user_dict, count=count, page=page)
        return recommendations
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ======================
# 1️⃣ 혼잡도 예측 API
# ======================
@app.get("/predict")
def predict(date: str):
    if laundry_model is None:
        raise HTTPException(status_code=500, detail="Laundry model is not loaded")
    
    target_date = datetime.strptime(date, "%Y-%m-%d").date()
    result = predict_day(laundry_model, target_date)
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
        return "오늘 빨래하기 안 좋아요 ☔️"

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
    
    # 강수량 파싱 (1.0mm, 2mm 등의 형식 처리)
    pcp_value = weather.get("PCP", "강수없음")
    if pcp_value == "강수없음":
        rain = 0
    else:
        # "mm" 제거하고 숫자만 추출
        rain = float(pcp_value.replace("mm", "").strip())
    
    index = laundry_index(temp, humidity, rain)
    return {
        "laundry_message": laundry_comment(index)
    }

@app.get("/notices")
def get_dorm_notices():
    if not os.path.exists("data/dorm_notices.json"):
        raise HTTPException(status_code=404, detail="공지 데이터가 없습니다.")

    with open("data/dorm_notices.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "count": len(data),
        "notices": data
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)