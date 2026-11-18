import streamlit as st
import pandas as pd
import requests
import datetime
import urllib.parse

st.set_page_config(
    page_title="건강기반 추천",
    page_icon="☕",
    layout="wide"
)

st.title("☕ 건강기반 추천")
st.markdown("개인정보 및 건강 데이터 연동에 동의하시면, 본인의 스마트워치(Google Fit / Health Connect) 생체 데이터를 실시간으로 분석해 지금 딱 맞는 음료를 추천해 드립니다.")

# ---------------------------------------------------------
# 1. Google OAuth 2.0 환경 설정 (Streamlit Secrets에서 로드)
# 배포 시 .streamlit/secrets.toml 또는 Streamlit Cloud Secrets에 아래 값을 설정하세요:
# GOOGLE_CLIENT_ID = "발급받은_클라이언트_ID"
# GOOGLE_CLIENT_SECRET = "발급받은_클라이언트_시크릿"
# REDIRECT_URI = "https://본인앱주소.streamlit.app/건강기반_추천"
# ---------------------------------------------------------
CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", "") if hasattr(st, "secrets") else ""
CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", "") if hasattr(st, "secrets") else ""
REDIRECT_URI = st.secrets.get("REDIRECT_URI", "http://localhost:8501") if hasattr(st, "secrets") else "http://localhost:8501"

SCOPES = [
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.sleep.read"
]

# 세션 상태 초기화 (사용자별 토큰 저장)
if "user_access_token" not in st.session_state:
    st.session_state.user_access_token = None
if "privacy_agreed" not in st.session_state:
    st.session_state.privacy_agreed = False

# OAuth 리다이렉트 콜백 처리 (URL의 ?code=... 파라미터 감지)
query_params = st.query_params
if "code" in query_params and st.session_state.user_access_token is None:
    auth_code = query_params["code"]
    if CLIENT_ID and CLIENT_SECRET:
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": auth_code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        res = requests.post(token_url, data=token_data, timeout=10)
        if res.status_code == 200:
            st.session_state.user_access_token = res.json().get("access_token")
            st.session_state.privacy_agreed = True
            st.query_params.clear()
            st.rerun()
        else:
            st.error(f"인증 토큰 발급에 실패했습니다: {res.text}")

# ---------------------------------------------------------
# 2. 개인정보 동의 및 사용자 개별 연동 UI
# ---------------------------------------------------------
if st.session_state.user_access_token is None:
    st.subheader("🔒 개인정보 및 민감정보(건강 데이터) 수집·이용 동의")
    with st.container(border=True):
        st.markdown('''
        **1. 수집 및 이용 목적**: 사용자 맞춤형 카페인 한도 산출 및 음료 추천  
        **2. 수집 항목**: 스마트워치 연동 생체 데이터 (심박수, 걸음 수, 수면 시간)  
        **3. 보유 및 이용 기간**: 서비스 이용 세션 종료 시 즉시 파기 (서버에 영구 저장하지 않음)  
        ''')
        agreed = st.checkbox("위 개인정보 및 건강정보 수집·이용에 동의합니다. (필수)")
        st.session_state.privacy_agreed = agreed

    if st.session_state.privacy_agreed:
        if CLIENT_ID and CLIENT_SECRET:
            # Google OAuth 2.0 로그인 URL 생성
            params = {
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "scope": " ".join(SCOPES),
                "access_type": "offline",
                "prompt": "consent"
            }
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
            st.link_button("🔗 내 Google Fit / 워치 건강 데이터 연동하기", auth_url, type="primary")
        else:
            st.warning("⚠️ 현재 서버에 Google Cloud OAuth 설정(`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`)이 등록되어 있지 않습니다.")
            st.info("관리자가 Streamlit Secrets에 Google OAuth 키를 등록하면, 동의한 모든 사용자가 각자의 워치 데이터를 즉시 연동할 수 있습니다.")
            
            # 개발/테스트 확인용 임시 개인 토큰 입력 옵션 (접이식)
            with st.expander("🛠️ 개발자 테스트: 발급받은 사용자 Access Token 직접 입력"):
                manual_token = st.text_input("OAuth Access Token 입력", type="password")
                if st.button("토큰으로 내 데이터 불러오기") and manual_token:
                    st.session_state.user_access_token = manual_token
                    st.rerun()
    else:
        st.info("👆 위 동의 항목에 체크하시면 스마트워치 연동 버튼이 활성화됩니다.")
    st.stop()

# ---------------------------------------------------------
# 3. 실제 사용자 Google Fitness API 데이터 조회 및 파싱
# ---------------------------------------------------------
def fetch_real_user_health_data(access_token: str):
    now = datetime.datetime.now()
    start_ms = int((now - datetime.timedelta(hours=24)).timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)

    url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    body = {
        "aggregateBy": [
            {"dataTypeName": "com.google.heart_rate.bpm"},
            {"dataTypeName": "com.google.step_count.delta"},
            {"dataTypeName": "com.google.sleep.segment"}
        ],
        "bucketByTime": {"durationMillis": 3600000}, # 1시간 단위 집계
        "startTimeMillis": start_ms,
        "endTimeMillis": end_ms
    }

    res = requests.post(url, headers=headers, json=body, timeout=10)
    if res.status_code != 200:
        return None, f"API 오류 ({res.status_code}): 토큰이 만료되었거나 권한이 없습니다."

    raw_data = res.json()
    buckets = raw_data.get("bucket", [])

    hr_list = []
    hourly_records = []
    total_steps = 0
    sleep_millis = 0

    for b in buckets:
        b_start = int(b.get("startTimeMillis", 0)) / 1000
        time_label = datetime.datetime.fromtimestamp(b_start).strftime("%H:%M")
        bucket_hr = None

        for ds in b.get("dataset", []):
            ds_id = ds.get("dataSourceId", "")
            for pt in ds.get("point", []):
                vals = pt.get("value", [])
                if not vals:
                    continue
                if "heart_rate" in ds_id:
                    val = vals[0].get("fpVal")
                    if val:
                        hr_list.append(val)
                        bucket_hr = round(val, 1)
                elif "step_count" in ds_id:
                    val = vals[0].get("intVal", 0)
                    total_steps += val
                elif "sleep" in ds_id:
                    s_start = int(pt.get("startTimeNanos", 0))
                    s_end = int(pt.get("endTimeNanos", 0))
                    if s_end > s_start:
                        sleep_millis += (s_end - s_start) / 1e6

        if bucket_hr is not None:
            hourly_records.append({"시간대": time_label, "심박수 (bpm)": bucket_hr})

    latest_hr = round(hr_list[-1], 1) if hr_list else None
    sleep_hours = round(sleep_millis / (1000 * 3600), 1) if sleep_millis > 0 else None

    return {
        "timestamp": now.strftime("%H:%M:%S"),
        "heart_rate": latest_hr,
        "steps": total_steps,
        "sleep_hours": sleep_hours,
        "timeline": pd.DataFrame(hourly_records)
    }, None

# ---------------------------------------------------------
# 4. 실제 생체 데이터 기반 맞춤 커피 추천 로직
# ---------------------------------------------------------
def analyze_real_health(health: dict):
    now_hour = datetime.datetime.now().hour
    hr = health["heart_rate"]
    sleep = health["sleep_hours"]
    steps = health["steps"]

    if hr is None and steps == 0 and sleep is None:
        return {
            "status": "info",
            "menu": "싱글 오리진 아메리카노 (기본 추천)",
            "reason": "최근 24시간 동안 스마트워치에서 동기화된 생체 기록이 확인되지 않았습니다. 워치와 스마트폰 건강 앱(Google Fit / 헬스 커넥트) 동기화 상태를 확인해 주세요.",
            "caffeine_limit": "100 ~ 150 mg 권장"
        }

    if now_hour >= 18 or (sleep is not None and sleep < 6.0 and now_hour >= 15):
        sleep_txt = f"전날 수면 시간({sleep}시간)과 " if sleep is not None else ""
        return {
            "status": "warning",
            "menu": "디카페인 아메리카노 / 따뜻한 캐모마일 티",
            "reason": f"{sleep_txt}현재 시각({now_hour}시)을 분석한 결과, 지금 카페인을 섭취하면 오늘 밤 수면 질을 떨어뜨릴 가능성이 높습니다.",
            "caffeine_limit": "0 mg (카페인 휴식 권장)"
        }
    elif hr is not None and hr >= 85:
        return {
            "status": "error",
            "menu": "디카페인 콜드브루 / 시원한 탄산수",
            "reason": f"현재 측정된 심박수가 {hr} bpm으로 다소 높습니다. 추가적인 카페인 섭취는 심박수 상승과 피로감을 유발할 수 있습니다.",
            "caffeine_limit": "최대 50 mg 이하"
        }
    elif steps >= 7000:
        hr_txt = f"심박수({hr} bpm)가 안정적이고 " if hr is not None else ""
        return {
            "status": "success",
            "menu": "아이스 카페 라떼 / 바닐라 라떼",
            "reason": f"최근 24시간 동안 {steps:,}보를 걸으며 에너지를 많이 소모하셨네요! {hr_txt}활동량이 높아 적당한 당분과 카페인이 보충되는 라떼류를 추천합니다.",
            "caffeine_limit": "150 ~ 200 mg 권장"
        }
    else:
        hr_txt = f"심박수({hr} bpm)와 " if hr is not None else ""
        return {
            "status": "info",
            "menu": "싱글 오리진 핸드드립 / 아메리카노",
            "reason": f"{hr_txt}전반적인 생체 컨디션이 안정적입니다. 집중력을 높여주는 깔끔한 블랙 커피가 가장 잘 어울리는 상태입니다.",
            "caffeine_limit": "100 ~ 150 mg 권장"
        }

# ---------------------------------------------------------
# 5. 연동된 사용자 대시보드 출력
# ---------------------------------------------------------
with st.sidebar:
    st.success("✅ 내 워치 데이터 연동 완료")
    if st.button("🔄 최신 데이터 다시 불러오기"):
        st.rerun()
    st.divider()
    if st.button("🔓 연동 해제 및 개인정보 파기"):
        st.session_state.user_access_token = None
        st.session_state.privacy_agreed = False
        st.rerun()

with st.spinner("내 스마트워치 건강 데이터를 실시간으로 불러오는 중..."):
    health_data, err_msg = fetch_real_user_health_data(st.session_state.user_access_token)

if err_msg:
    st.error(err_msg)
    if st.button("다시 로그인하여 연동하기"):
        st.session_state.user_access_token = None
        st.rerun()
    st.stop()

recommendation = analyze_real_health(health_data)

st.caption(f"📡 실시간 사용자 계정 연동됨 | 최근 동기화: {health_data['timestamp']}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("최근 심박수", f"{health_data['heart_rate']} bpm" if health_data['heart_rate'] is not None else "기록 없음")
c2.metric("수면 시간", f"{health_data['sleep_hours']} 시간" if health_data['sleep_hours'] is not None else "기록 없음")
c3.metric("최근 24시간 걸음 수", f"{health_data['steps']:,} 보")
c4.metric("권장 카페인 한도", recommendation["caffeine_limit"])

st.divider()
st.subheader("🎯 내 생체 데이터 기반 맞춤 추천 메뉴")

if recommendation["status"] == "warning":
    st.warning(f"**추천 메뉴: {recommendation['menu']}**\n\n{recommendation['reason']}")
elif recommendation["status"] == "error":
    st.error(f"**추천 메뉴: {recommendation['menu']}**\n\n{recommendation['reason']}")
elif recommendation["status"] == "success":
    st.success(f"**추천 메뉴: {recommendation['menu']}**\n\n{recommendation['reason']}")
else:
    st.info(f"**추천 메뉴: {recommendation['menu']}**\n\n{recommendation['reason']}")

if not health_data["timeline"].empty:
    st.subheader("📊 최근 24시간 내 실제 심박수 추이")
    st.line_chart(health_data["timeline"].set_index("시간대"))
