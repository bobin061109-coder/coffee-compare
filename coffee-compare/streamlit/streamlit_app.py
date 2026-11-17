"""
☕ 건강 기반 커피 추천 대시보드 (Streamlit)

구조: 갤럭시 워치 → Android 앱 → 구글 시트 → (이 앱이 자동으로 읽음) → 추천 표시

- 사용자는 아무것도 입력하지 않는다. 구글 시트에 쌓인 '최신 건강 데이터' 한 줄을
  자동으로 읽어 추천을 계산해 보여준다.
- 자동 새로고침으로 워치 데이터가 갱신되면 화면도 따라 갱신된다.

실행(로컬):
    pip install -r requirements.txt
    streamlit run streamlit_app.py
배포:
    GitHub 저장소에 올리고 share.streamlit.io 에서 Deploy
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------
# 0) 페이지 설정 + 자동 새로고침 (워치 데이터가 바뀌면 화면도 갱신)
# ----------------------------------------------------------------------
st.set_page_config(page_title="건강 기반 커피 추천", page_icon="☕", layout="centered")

# 60초마다 자동 새로고침 (구버전 호환 위해 try)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60_000, key="auto")
except Exception:
    pass


# ----------------------------------------------------------------------
# 1) 추천 엔진 (backend/main.py 와 동일 로직)
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
        reason_parts.append(f"안정 심박이 높아({resting_hr}bpm) 카페인을 줄이는 게 좋아요")
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
# 2) 구글 시트에서 최신 건강 데이터 읽기
#    시트 첫 행(헤더): timestamp | sleepHours | avgHeartRate | restingHeartRate | steps | exerciseMinutes
# ----------------------------------------------------------------------
@st.cache_data(ttl=30)
def load_latest_from_sheet() -> Optional[pd.Series]:
    """st.secrets 에 구글 서비스계정 + 시트 URL 이 설정돼 있으면 최신 1행을 읽는다."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(st.secrets["sheet"]["url"])
        ws = sh.sheet1
        df = pd.DataFrame(ws.get_all_records())
        if df.empty:
            return None
        # timestamp 기준 최신 행
        if "timestamp" in df.columns:
            df = df.sort_values("timestamp")
        return df.iloc[-1]
    except Exception as e:
        st.session_state["sheet_error"] = str(e)
        return None


# ----------------------------------------------------------------------
# 3) 화면
# ----------------------------------------------------------------------
st.title("☕ 건강 기반 커피 추천")
st.caption("갤럭시 워치 → 앱 → 구글 시트에 쌓인 최신 데이터로 자동 추천합니다. (수동 입력 없음)")

row = load_latest_from_sheet()

if row is None:
    st.warning(
        "아직 구글 시트에서 데이터를 읽지 못했어요.\n\n"
        "① `.streamlit/secrets.toml` 에 구글 서비스계정·시트 URL 설정, "
        "② 앱이 시트에 데이터를 올렸는지 확인하세요."
    )
    if "sheet_error" in st.session_state:
        with st.expander("오류 상세"):
            st.code(st.session_state["sheet_error"])
    st.stop()

# 시트 값 파싱 (숫자 변환, 빈 값 허용)
def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

sleep_h     = num(row.get("sleepHours"))
avg_hr      = num(row.get("avgHeartRate"))
resting_hr  = num(row.get("restingHeartRate"))
steps       = int(num(row.get("steps")) or 0)
exercise    = int(num(row.get("exerciseMinutes")) or 0)
local_hour  = dt.datetime.now().hour

# 최신 측정값 표시
st.subheader("📊 워치에서 가져온 오늘 상태")
c1, c2, c3 = st.columns(3)
c1.metric("어젯밤 수면", f"{sleep_h:.1f}h" if sleep_h else "–")
c2.metric("안정 심박", f"{int(resting_hr)}bpm" if resting_hr else "–")
c3.metric("걸음 수", f"{steps:,}")
c4, c5, c6 = st.columns(3)
c4.metric("평균 심박", f"{int(avg_hr)}bpm" if avg_hr else "–")
c5.metric("운동 시간", f"{exercise}분")
c6.metric("현재 시각", f"{local_hour}시")

# 추천 계산
limit = compute_caffeine_limit(sleep_h, resting_hr, local_hour)
drink, reason = recommend_drink(sleep_h, resting_hr, exercise, local_hour, limit)

st.divider()
st.subheader("✅ 오늘의 추천")
st.success(f"**{drink['name']}**  ·  카페인 {drink['caffeine_mg']}mg / 당 {drink['sugar_g']}g")
st.write(f"💬 {reason}")
st.progress(min(limit / BASE_DAILY_LIMIT, 1.0), text=f"권장 카페인 상한: {limit}mg / {BASE_DAILY_LIMIT}mg")

ts = row.get("timestamp", "")
st.caption(f"마지막 데이터 수신: {ts}  ·  (60초마다 자동 갱신)")
