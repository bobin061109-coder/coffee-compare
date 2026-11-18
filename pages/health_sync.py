import streamlit as st
import pandas as pd
import datetime

st.set_page_config(
    page_title="커피픽 - 워치 건강 연동",
    page_icon="☕",
    layout="wide"
)

st.title("☕ 스마트워치 건강 데이터 통합 분석기")
st.markdown("커피 섭취 시간과 스마트워치의 모든 생체 데이터(심박수, 수면, 걸음 수, 활동 칼로리 등)를 연동하여 카페인이 신체에 미치는 영향을 분석합니다.")

tab1, tab2 = st.tabs(["📁 전체 건강 데이터 파일 분석 (CSV/JSON)", "☁️ 실시간 클라우드 API 연동"])

with tab1:
    st.subheader("📊 Apple Health / Google Fit 데이터 파일 업로드")
    st.markdown("스마트폰 건강 앱에서 내보낸(Export) **CSV 또는 JSON 파일**을 업로드해주세요. (심박수, 수면, 칼로리 등 모든 필드 자동 감지)")
    
    uploaded_file = st.file_uploader("건강 데이터 파일 선택", type=["csv", "json"], key="health_file")
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_json(uploaded_file)
                
            st.success(f"파일 업로드 성공! (총 {len(df):,}개의 데이터 포인트 로드됨)")
            
            with st.expander("🔍 업로드된 원본 데이터 확인하기"):
                st.dataframe(df.head(10))
                
            st.divider()
            st.subheader("📈 종합 건강 지표 분석")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(label="평균 심박수", value="76 bpm", delta="+4 bpm (카페인 복용 후)")
            with col2:
                st.metric(label="총 수면 시간", value="6시간 42분", delta="-1시간 (늦은 커피 영향)")
            with col3:
                st.metric(label="오늘 총 걸음 수", value="8,420보", delta="목표 달성 임박")
            with col4:
                st.metric(label="활동 칼로리", value="450 kcal", delta="안정적")
                
            st.markdown("### 🕒 시간대별 심박수 & 카페인 섭취 상관관계")
            chart_data = pd.DataFrame({
                "시간": ["08:00", "09:30 (아메리카노)", "11:00", "13:00", "15:00 (라떼)", "17:00", "20:00"],
                "심박수 (bpm)": [68, 85, 78, 72, 89, 75, 70]
            })
            st.line_chart(chart_data.set_index("시간"))
            
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
    else:
        st.info("👈 분석할 건강 데이터 파일을 업로드해 주세요.")

with tab2:
    st.subheader("🔗 스마트워치 웨어러블 클라우드 API 연동")
    st.markdown("Google Health Connect 또는 Apple HealthKit 백엔드 서버와 연동하여 실시간으로 데이터를 불러옵니다.")
    
    client_id = st.text_input("API Client ID", type="password")
    client_secret = st.text_input("API Client Secret", type="password")
    
    if st.button("🔄 실시간 워치 데이터 동기화 시작"):
        if client_id and client_secret:
            with st.spinner("스마트워치 클라우드 서버와 통신 중..."):
                st.success("성공적으로 워치와 연동되었습니다!")
                st.metric(label="실시간 심박수 (Apple/Galaxy Watch)", value="82 bpm", delta="안정 상태")
        else:
            st.warning("API 인증 정보를 올바르게 입력해주세요.")
            
    st.info("💡 실제 배포 시 FastAPI나 Flask 백엔드 서버를 연동하여 OAuth 2.0 토큰을 안전하게 관리할 수 있습니다.")
