"""
☕ 건강 기반 커피 추천 대시보드 (Streamlit)

구조: 갤럭시 워치 → 앱 → 구글 시트(웹에 게시 CSV) → (이 앱이 자동으로 읽음) → 추천 표시
- 사용자는 아무것도 입력하지 않는다. 공개된 구글 시트 CSV의 '최신 한 줄'을 읽어 추천.
- 서비스계정/인증키 불필요(시트를 '웹에 게시'했기 때문).

실행:  streamlit run streamlit_app.py
배포:  GitHub 저장소 → share.streamlit.io (Main file path: streamlit/streamlit_app.py)
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------
# 구글 시트 '웹에 게시' CSV 주소 (사용자 시트)
# ----------------------------------------------------------------------
SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vSvj_u0zEzjTK3Va1nRaob1diyaxVN_yWMd3lgQo5aLwg7jJEnT6OhV7derd7c40peutN6eH0cCiZRN/"
    "pub?output=csv"
)

st.set_page_config(page_title="건강 기반 커피 추천", page_icon="☕", layout="centered")

# 60초마다 자동 새로고침 (설치돼 있으면)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60_000, key="auto")
except Exception:
    pass


# ----------------------------------------------------------------------
# 추천 엔진
# ----------------------------------------------------------------------
MENU = [
    {"name": "디카페인 아메리카노", "caffeine_mg": 10,  "sugar_g": 0,  "tags": ["decaf", "low_sugar"]},
    {"name": "아메리카노",         "caffeine_mg": 120, "sugar_g": 0,  "tags": ["low_sugar"]},
    {"name": "콜드브루",           "caffeine_mg": 200, "sugar_g": 0,  "tags": ["strong", "low_sugar"]},
    {"name": "라떼",               "caffeine_mg": 120, "sugar_g": 12, "tags": []},
    {"name": "단백질 쉐이크 라떼",  "caffeine_mg": 90,  "sugar_g": 6,  "tags": ["recovery", "protein"]},
    {"name": "허브티 (카페인프리)", "caffeine_mg": 0,   "sugar_g": 0,  "tags": ["decaf", "calm"]},
]
BASE_DAILY_LIMIT = 400


def compute_caffeine_limit(sleep_h, resting_hr, local_hour) -> int:
    limit = BASE_DAILY_LIMIT
    if sleep_h is not None and sleep_h < 6:
        limit -= 100
    if resting_hr is not None and resting_hr > 80:
        limit -= 80
    if local_hour >= 14:
        limit -= 100
    if local_hour >= 18:
        limit -= 100
    return max(limit, 0)


def recommend_drink(sleep_h, resting_hr, exercise_min, local_hour, caffeine_limit):
    want_tags, reason_parts = [], []
    low_sleep = sleep_h is not None and sleep_h < 6
    high_hr = resting_hr is not None and resting_hr > 80
    post_workout = exercise_min >= 30
    late = local_hour >= 18

    if late or caffeine_limit < 60:
        want_tags.append("decaf")
        reason_parts.append("늦은 시간이라 수면을 지키기 위해 저·무카페인을 권해요")
    elif high_hr:
        want_tags.append("decaf")
        reason_parts.append(f"안정 심박이 높아({int(resting_hr)}bpm) 카페인을 줄이는 게 좋아요")
    elif post_workout:
        want_tags.append("recovery")
        reason_parts.append(f"운동 {exercise_min}분 후라 회복에 좋은 메뉴예요")
    elif low_sleep:
        reason_parts.append(f"어젯밤 수면이 {sleep_h:.1f}시간으로 짧아 적당한 각성을 도와요")
    else:
        reason_parts.append("오늘 컨디션에 무난한 선택이에요")

    candidates = [m for m in MENU if m["caffeine_mg"] <= caffeine_limit] or \
                 [min(MENU, key=lambda m: m["caffeine_mg"])]
    want_awake = "decaf" not in want_tags and "recovery" not in want_tags
    target = 150 if low_sleep else 100

    def score(m):
        s = float(sum(1 for t in want_tags if t in m["tags"]))
        if late and "low_sugar" in m["tags"]:
            s += 1
        if want_awake:
            s += 1.0 / (1 + abs(m["caffeine_mg"] - target) / 50.0)
        return s

    best = max(candidates, key=score)
    return best, " · ".join(reason_parts)


# ----------------------------------------------------------------------
# 공개 구글 시트 CSV 읽기
# ----------------------------------------------------------------------
@st.cache_data(ttl=30)
def load_latest() -> Optional[pd.Series]:
    df = pd.read_csv(SHEET_CSV_URL)
    if df.empty:
        return None
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp")
    return df.iloc[-1]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------
# 화면
# ----------------------------------------------------------------------
st.title("☕ 건강 기반 커피 추천")
st.caption("갤럭시 워치 → 앱 → 구글 시트에 쌓인 최신 데이터로 자동 추천합니다. (수동 입력 없음)")

try:
    row = load_latest()
except Exception as e:
    st.error("구글 시트 CSV를 읽지 못했어요. 시트가 '웹에 게시'되어 있는지 확인하세요.")
    with st.expander("오류 상세"):
        st.code(str(e))
    st.stop()

if row is None:
    st.warning("시트에 데이터가 아직 없어요. 헤더 아래 한 줄이라도 입력해 주세요.")
    st.stop()

sleep_h    = num(row.get("sleepHours"))
avg_hr     = num(row.get("avgHeartRate"))
resting_hr = num(row.get("restingHeartRate"))
steps      = int(num(row.get("steps")) or 0)
exercise   = int(num(row.get("exerciseMinutes")) or 0)
local_hour = dt.datetime.now().hour

st.subheader("📊 워치에서 가져온 오늘 상태")
c1, c2, c3 = st.columns(3)
c1.metric("어젯밤 수면", f"{sleep_h:.1f}h" if sleep_h else "–")
c2.metric("안정 심박", f"{int(resting_hr)}bpm" if resting_hr else "–")
c3.metric("걸음 수", f"{steps:,}")
c4, c5, c6 = st.columns(3)
c4.metric("평균 심박", f"{int(avg_hr)}bpm" if avg_hr else "–")
c5.metric("운동 시간", f"{exercise}분")
c6.metric("현재 시각", f"{local_hour}시")

limit = compute_caffeine_limit(sleep_h, resting_hr, local_hour)
drink, reason = recommend_drink(sleep_h, resting_hr, exercise, local_hour, limit)

st.divider()
st.subheader("✅ 오늘의 추천")
st.success(f"**{drink['name']}**  ·  카페인 {drink['caffeine_mg']}mg / 당 {drink['sugar_g']}g")
st.write(f"💬 {reason}")
st.progress(min(limit / BASE_DAILY_LIMIT, 1.0), text=f"권장 카페인 상한: {limit}mg / {BASE_DAILY_LIMIT}mg")

ts = row.get("timestamp", "")
st.caption(f"마지막 데이터 수신: {ts}  ·  (60초마다 자동 갱신)")
