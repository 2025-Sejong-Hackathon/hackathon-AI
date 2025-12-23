from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin
import pandas as pd
import re
import time
import json

BASE_URL = "https://happydorm.sejong.ac.kr/60/6010.do"
DOMAIN = "https://happydorm.sejong.ac.kr"
MAX_RESULTS = 5

options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

wait = WebDriverWait(driver, 10)
driver.get(BASE_URL)

results = []

PAGE_SIZE = 10
MAX_PAGE = 10

for page in range(1, MAX_PAGE + 1):
    print(f"➡ 페이지 {page} 이동 중")

    driver.execute_script(f"getBbsList('{page}', '{PAGE_SIZE}')")
    wait.until(EC.presence_of_element_located((By.ID, "list")))
    time.sleep(0.8)

    rows = driver.find_elements(
        By.CSS_SELECTOR,
        "#list tr.under_l td.li_subject a"
    )

    if not rows:
        break

    for a in rows:
        title = a.text.strip()
        onclick = a.get_attribute("onclick")

        match = re.search(r"getBbs\('(\d+)'\)", onclick)
        if not match:
            continue

        seq = match.group(1)
        link = (
            "https://happydorm.sejong.ac.kr/bbs/getBbsWriteView.do"
            f"?seq={seq}&bbs_locgbn=SJ&bbs_id=notice"
        )

        # 🔽 상세 페이지 이동
        driver.get(link)
        wait.until(EC.presence_of_element_located((By.ID, "contents")))
        time.sleep(0.5)

        imgs = driver.find_elements(By.CSS_SELECTOR, "#contents img")

        image_urls = []
        for img in imgs:
            src = img.get_attribute("src")
            if src:
                image_urls.append(urljoin(DOMAIN, src))

        # ❌ 이미지 없는 글 제외
        if not image_urls:
            driver.back()
            continue

        results.append({
            "title": title,
            "url": link,
            "images": image_urls
        })

        print(f"✅ 수집 ({len(results)}/{MAX_RESULTS}) : {title}")

        # ✅ 5개 채우면 종료
        if len(results) >= MAX_RESULTS:
            break

        driver.back()
        time.sleep(0.5)

    if len(results) >= MAX_RESULTS:
        break

driver.quit()

df = pd.DataFrame(results)

with open("data/dorm_notices.json", "w", encoding="utf-8") as f:
    json.dump(
        df.to_dict(orient="records"),
        f,
        ensure_ascii=False,
        indent=2
    )

print(f"🎉 이미지 있는 공지 {len(df)}개 수집 완료")
print("📦 dorm_notices.json 저장 완료")