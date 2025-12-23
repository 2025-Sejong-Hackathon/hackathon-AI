from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import json
import re
from datetime import datetime, timedelta

# ==========================================
# 1. 설정 및 접속
# ==========================================
BASE_URL = "https://happydorm.sejong.ac.kr/60/6050.do"

options = webdriver.ChromeOptions()
options.add_argument("--window-size=1920,1080")
# options.add_argument("--headless") 

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

try:
    print("🌍 사이트 접속 중...")
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)

    # ==========================================
    # 2. [중요] 화면에서 '월요일' 날짜 직접 읽기
    # ==========================================
    print("📅 사이트에 적힌 기준 날짜 확인 중...")
    
    start_date = None
    try:
        # '월요일'이라는 글자가 포함된 탭 찾기
        mon_tab = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//a[contains(text(), '월') and contains(text(), '/')]")
        ))
        mon_text = mon_tab.text.strip()
        print(f"👉 사이트에서 발견한 텍스트: {mon_text}")

        # 정규식으로 월/일 추출
        match = re.search(r"(\d{1,2})/(\d{1,2})", mon_text)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            
            current_year = datetime.now().year
            
            if datetime.now().month == 1 and month == 12:
                current_year -= 1
            elif datetime.now().month == 12 and month == 1:
                current_year += 1
                
            start_date = datetime(current_year, month, day)
            print(f"✅ 기준일 설정 완료: {start_date.strftime('%Y-%m-%d')} (월요일)")
            
    except Exception as e:
        print(f"⚠️ 날짜 읽기 실패 ({e})")

    if not start_date:
        kst_now = datetime.utcnow() + timedelta(hours=9)
        idx_today = kst_now.weekday()
        start_date = kst_now - timedelta(days=idx_today)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        print(f"⚠️ 화면 읽기 실패하여 한국시간 기준으로 자동 계산: {start_date.strftime('%Y-%m-%d')}")

    # ==========================================
    # 3. '전체보기' 클릭
    # ==========================================
    print("🖱️ [전체보기] 클릭...")
    all_view_btn = wait.until(EC.element_to_be_clickable((By.ID, "tabDayA")))
    all_view_btn.click()
    time.sleep(3) 

    # ==========================================
    # 3.5. 전체보기 상단의 요일 탭들을 다시 확인
    # ==========================================
    print("🔍 전체보기 후 날짜 탭 재확인 중...")
    
    # 전체보기를 누른 후에도 상단에 날짜 탭들이 있을 수 있음
    # 모든 날짜 탭을 찾아서 첫 번째 날짜 확인
    try:
        # 날짜가 포함된 모든 링크 찾기
        date_links = driver.find_elements(By.XPATH, "//a[contains(text(), '/')]")
        
        if date_links:
            # 각 링크의 날짜 추출
            found_dates = []
            for link in date_links[:10]:  # 처음 10개만 확인
                link_text = link.text.strip()
                match = re.search(r"(\d{1,2})/(\d{1,2})", link_text)
                if match:
                    m = int(match.group(1))
                    d = int(match.group(2))
                    
                    year = datetime.now().year
                    if datetime.now().month == 1 and m == 12:
                        year -= 1
                    elif datetime.now().month == 12 and m == 1:
                        year += 1
                    
                    date_obj = datetime(year, m, d)
                    found_dates.append((date_obj, link_text))
            
            if found_dates:
                # 날짜 순으로 정렬
                found_dates.sort(key=lambda x: x[0])
                first_actual_date = found_dates[0][0]
                
                print(f"📍 전체보기에서 발견된 첫 날짜: {first_actual_date.strftime('%Y-%m-%d')} ({found_dates[0][1]})")
                
                # 월요일과 비교
                if first_actual_date < start_date:
                    days_diff = (start_date - first_actual_date).days
                    print(f"⚠️ 첫 날짜가 월요일보다 {days_diff}일 빠름")
                    start_date = first_actual_date
                    print(f"✅ 시작일 조정: {start_date.strftime('%Y-%m-%d')}")
                elif first_actual_date > start_date:
                    days_diff = (first_actual_date - start_date).days
                    print(f"⚠️ 첫 날짜가 월요일보다 {days_diff}일 느림")
                    # start_date는 월요일 그대로 유지
                    print(f"✅ 월요일 {start_date.strftime('%Y-%m-%d')}부터 시작")
                else:
                    print(f"✅ 날짜 일치 확인")
                    
    except Exception as e:
        print(f"⚠️ 날짜 탭 재확인 실패: {e}")
        print("   → 월요일 기준으로 계속 진행합니다.")

    # ==========================================
    # 4. 데이터 수집
    # ==========================================
    results = []
    tables = driver.find_elements(By.TAG_NAME, "table")
    weekdays_kr = ["월", "화", "수", "목", "금", "토", "일"]

    print(f"\n📊 총 {len(tables)}개 테이블 발견...")
    print(f"📅 시작일: {start_date.strftime('%Y-%m-%d (%A)')}\n")

    # 실제로 저장된 메뉴 개수를 카운트
    valid_table_count = 0
    
    for idx, table in enumerate(tables):
        # 메뉴 수집
        rows = table.find_elements(By.TAG_NAME, "tr")
        daily_menu = {}
        
        for tr in rows:
            th = tr.find_elements(By.TAG_NAME, "th")
            tds = tr.find_elements(By.TAG_NAME, "td")
            
            if th and tds:
                meal_type = th[0].text.strip()
                
                # 'te_left' 클래스가 있는 칸이 진짜 메뉴
                target_td = None
                for td in tds:
                    if "te_left" in td.get_attribute("class"):
                        target_td = td
                        break
                if not target_td:
                    target_td = tds[-1]

                real_menu = target_td.text.strip().replace("\n", " ")
                if real_menu:  # 빈 메뉴가 아닌 경우만
                    daily_menu[meal_type] = real_menu
        
        # 메뉴가 실제로 있는 테이블만 처리
        if len(daily_menu) > 0:
            # 이 테이블의 날짜 계산 (valid_table_count 기준)
            current_date = start_date + timedelta(days=valid_table_count)
            weekday_str = weekdays_kr[current_date.weekday()]
            date_str = f"{current_date.strftime('%Y-%m-%d')} ({weekday_str})"
            
            daily_menu["date"] = date_str
            results.append(daily_menu)
            print(f"  ✓ {date_str} 수집 완료 (테이블 #{idx})")
            
            valid_table_count += 1
        else:
            print(f"  ⊗ 테이블 #{idx} 건너뜀 (메뉴 없음)")

    # ==========================================
    # 5. 저장
    # ==========================================
    if results:
        # date를 첫 번째 컬럼으로 재정렬
        df = pd.DataFrame(results)
        if "date" in df.columns:
            cols = ["date"] + [c for c in df.columns if c != "date"]
            df = df[cols]
        
        df.to_csv("cafeteria_menu.csv", index=False, encoding="utf-8-sig")
        
        with open("cafeteria_menu.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print("\n" + "="*60)
        print("✅ 크롤링 완료!")
        print("="*60)
        print(f"📁 저장된 파일:")
        print("   - cafeteria_menu.csv")
        print("   - cafeteria_menu.json")
        print(f"\n📊 수집된 데이터: {len(results)}일치")
        print(f"📅 날짜 범위: {results[0]['date']} ~ {results[-1]['date']}")
        print("\n🔍 미리보기 (처음 3일):")
        print(df.head(3).to_string(index=False))
    else:
        print("\n⚠️ 데이터를 찾지 못했습니다.")

except Exception as e:
    print(f"\n❌ 에러 발생: {e}")
    import traceback
    traceback.print_exc()

finally:
    driver.quit()
    print("\n🏁 브라우저 종료")