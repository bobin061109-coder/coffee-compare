"""취향 맞춤 음료 추천 화면. recommendation.py의 기존 추천 로직 사용."""
import streamlit as st
import recommendation as rec

st.set_page_config(page_title="취향 맞춤 추천", page_icon="🎯", layout="wide")
st.title("🎯 취향 맞춤 음료 추천")
st.caption("선호와 상황을 고르면 추천 메뉴와 이유를 보여드려요.")
st.info("추천 메뉴와 가격은 recommendation.py의 참고용 데이터이며, 브랜드별 실측 가격 비교값은 아닙니다.")
answers = {"taste": {}, "mood": {}, "budget": {}}
with st.form("recommendation_form"):
    st.subheader("맛과 종류")
    c1, c2 = st.columns(2)
    with c1:
        categories = st.multiselect("원하는 음료 종류", list(rec.CATEGORIES), format_func=lambda k: rec.CATEGORIES[k])
        if categories: answers["taste"]["category"] = categories
        flavors = st.multiselect("선호하는 맛", list(rec.FLAVORS), format_func=lambda k: rec.FLAVORS[k])
        if flavors: answers["taste"]["flavor"] = flavors
    with c2:
        answers["taste"]["sweetness"] = st.select_slider("단맛 정도", [0, 1, 2, 3], value=1, format_func=lambda v: ["단맛 없음", "은은하게", "적당히", "많이 달콤"][v])
        answers["taste"]["temperature"] = st.radio("온도", ["any", "ice", "hot"], horizontal=True, format_func=lambda v: {"any":"상관없음", "ice":"ICE", "hot":"HOT"}[v])
    st.subheader("기분과 상황")
    c3, c4 = st.columns(2)
    with c3:
        answers["mood"]["activity"] = st.selectbox("지금 하는 일", ["study", "relax", "work", "dessert", "new"], format_func=lambda v: {"study":"공부/과제", "relax":"휴식", "work":"업무/집중", "dessert":"디저트와 함께", "new":"새 메뉴 도전"}[v])
        answers["mood"]["feeling"] = st.selectbox("현재 기분", ["tired", "refresh", "energetic", "calm"], format_func=lambda v: {"tired":"피곤함", "refresh":"기분전환 필요", "energetic":"활기참", "calm":"차분함"}[v])
    with c4:
        answers["mood"]["caffeine"] = st.radio("카페인", ["any", "high", "low", "none"], format_func=lambda v: {"any":"상관없음", "high":"높게", "low":"낮게", "none":"없음"}[v])
    st.subheader("예산과 용량")
    c5, c6 = st.columns(2)
    with c5:
        answers["budget"]["price"] = st.selectbox("예산", list(rec.BUDGETS.values()), format_func=lambda value: next(label for label, key in rec.BUDGETS.items() if key == value))
    with c6:
        answers["budget"]["size"] = st.radio("사이즈", ["any", "small", "medium", "large"], horizontal=True, format_func=lambda v: {"any":"상관없음", "small":"작게", "medium":"보통", "large":"크게"}[v])
    submitted = st.form_submit_button("내 취향 메뉴 추천받기", use_container_width=True)
if submitted:
    result = rec.recommend(rec.MENU, answers, top_n=6)
    st.subheader("추천 메뉴")
    for start in range(0, len(result.get("results", [])), 3):
        cols = st.columns(3)
        for col, entry in zip(cols, result["results"][start:start + 3]):
            item = entry["item"]
            with col:
                with st.container(border=True):
                    st.markdown(f"### {item['name']}")
                    st.write("종류: " + rec.CATEGORY_LABEL.get(item["category"], item["category"]))
                    st.write(f"참고용 가격: {item['price']:,}원")
                    score = entry.get("score")
                    if score is not None:
                        st.progress(min(1.0, max(0.0, score / 100)))
                        st.caption(f"취향 일치도 {score}%")
                    reasons = entry.get("reasons", [])
                    if reasons:
                        st.write("추천 이유: " + ", ".join(reasons))
