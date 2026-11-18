"""지금 날씨를 자동으로 가져와서 어울리는 음료를 추천합니다. (입력 없음)"""
import datetime
import random
import re
import sys
from pathlib import Path

import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from menudata import load_menus, menu_card  # noqa: E402

st.set_page_config(page_title="날씨 맞춤 추천", page_icon="🌤️", layout="wide")
KST = datetime.timezone(datetime.timedelta(hours=9))
CITIES = {
    "서울": (37.5665, 126.9780), "수원": (37.2636, 127.0286), "인천": (37.4563, 126.7052),
    "대전": (36.3504, 127.3845), "대구": (35.8714, 128.6014), "광주": (35.1595, 126.8526),
    "부산": (35.1796, 129.0756), "울산": (35.5384, 129.3114), "제주": (33.4996, 126.5312),
}

st.title("🌤️ 날씨 맞춤 추천")
saved = st.query_params.get("city", "서울")
city = st.selectbox("지역", list(CITIES), index=list(CITIES).index(saved) if saved in CITIES else 0)
if city != saved:
    st.query_params["city"] = city  # 즐겨찾기하면 다음에도 이 지역으로 열려요


@st.cache_data(ttl=1800, show_spinner=False)
def weather(lat, lon):
    r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=10, params={
        "latitude": lat, "longitude": lon, "timezone": "Asia/Seoul",
        "current": "temperature_2m,apparent_temperature,precipitation,weather_code,relative_humidity_2m",
    })
    r.raise_for_status()
    return r.json()["current"]


try:
    now = weather(*CITIES[city])
except Exception:
    st.error("날씨 정보를 잠깐 못 불러왔어요. 조금 뒤에 새로고침해 주세요.")
    st.stop()

temp, feel, rain = now["temperature_2m"], now["apparent_temperature"], now["precipitation"]
code = now["weather_code"]
snowy = code in (71, 73, 75, 77, 85, 86)
rainy = rain > 0 or code >= 51
ICON = "❄️" if snowy else "🌧️" if rainy else "☀️" if code <= 1 else "⛅"

c1, c2, c3 = st.columns(3)
c1.metric(f"{ICON} {city} 지금 기온", f"{temp:.0f}°C")
c2.metric("체감 온도", f"{feel:.0f}°C")
c3.metric("습도", f"{now['relative_humidity_2m']}%")

# 날씨 → 추천 규칙
if snowy or (rainy and feel < 18):
    title, why, variant, pat = ("따뜻하고 달달한 한 잔", "비나 눈이 오는 쌀쌀한 날엔 몸을 데워주는 따뜻한 라떼·초코가 좋아요.",
                                "HOT", r"라떼|초코|모카|고구마|쌍화|대추|밀크티")
elif feel < 8:
    title, why, variant, pat = ("뜨끈한 차·라떼", f"체감 {feel:.0f}°C, 꽤 추워요. 따뜻한 차나 라떼로 손부터 녹여요.",
                                "HOT", r"차$|티$|라떼|유자|생강|대추|쌍화")
elif feel < 17:
    title, why, variant, pat = ("선선한 날의 라떼", "선선한 날엔 부드러운 라떼가 잘 어울려요. 따뜻하게도 시원하게도 좋아요.",
                                None, r"라떼|카푸치노|마끼아또|마키아또")
elif feel < 26:
    title, why, variant, pat = ("시원한 커피 한 잔", "활동하기 좋은 날씨예요. 깔끔한 아이스 커피를 추천해요.",
                                "ICE", r"아메리카노|콜드브루|라떼")
else:
    title, why, variant, pat = ("시원하게 쭉 들이킬 음료", f"체감 {feel:.0f}°C, 더워요! 에이드·스무디·프라페로 열을 식혀요.",
                                "ICE", r"에이드|스무디|프라페|주스|쉐이크|빽스치노|소다|아이스티")

st.subheader(f"{ICON} 오늘은 **{title}**")
st.info(why)

rows = [r for r in load_menus() if re.search(pat, r["menu_name"]) and "디카페인" not in r["menu_name"]
        and (variant is None or r.get("variant") in (variant, "전체"))]
seen, uniq = set(), []
for r in rows:
    k = (r["brand"], r["menu_name"])
    if k not in seen:
        seen.add(k)
        uniq.append(r)
# 브랜드별로 골고루, 날짜·지역이 같으면 같은 추천이 나오도록 고정
rng = random.Random(f"{datetime.datetime.now(KST).date()}-{city}-{title}")
picks = []
for brand in ("컴포즈커피", "메가MGC커피", "빽다방"):
    pool = [r for r in uniq if r["brand"] == brand]
    picks += rng.sample(pool, min(2, len(pool)))
if not picks:
    st.warning("어울리는 메뉴를 찾지 못했어요.")
else:
    cols = st.columns(3)
    for i, r in enumerate(picks):
        with cols[i % 3]:
            menu_card(st, r)
st.caption(f"날씨: Open-Meteo · 30분마다 새로 불러와요 · 마지막 측정 {now['time'][-5:]}")
