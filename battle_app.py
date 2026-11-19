import streamlit as st

st.set_page_config(
    page_title="저가커피 1:1 메뉴 대결",
    page_icon="☕",
    layout="wide",
)

# 1. 브랜드별 메뉴 데이터 (예시 스펙 — 실제 메뉴판 기준으로 자유롭게 수정하세요!)
MENUS = [
    {
        "id": "compose_americano",
        "brand": "컴포즈커피",
        "name": "아이스 아메리카노",
        "price": 1500,
        "volume_ml": 591,
        "caffeine_mg": 156,
        "sugar_g": 0,
        "kcal": 10,
        "is_hot": False,
        "image_url": "",  # 원하시면 이미지 URL이나 "assets/..." 경로를 넣으세요
    },
    {
        "id": "compose_dolce",
        "brand": "컴포즈커피",
        "name": "돌체라떼",
        "price": 3900,
        "volume_ml": 591,
        "caffeine_mg": 156,
        "sugar_g": 34,
        "kcal": 310,
        "is_hot": False,
        "image_url": "",
    },
    {
        "id": "mega_americano",
        "brand": "메가MGC커피",
        "name": "아이스 아메리카노",
        "price": 2000,
        "volume_ml": 710,
        "caffeine_mg": 203,
        "sugar_g": 0,
        "kcal": 15,
        "is_hot": False,
        "image_url": "",
    },
    {
        "id": "mega_halmega",
        "brand": "메가MGC커피",
        "name": "할메가커피",
        "price": 2900,
        "volume_ml": 710,
        "caffeine_mg": 245,
        "sugar_g": 22,
        "kcal": 210,
        "is_hot": False,
        "image_url": "",
    },
    {
        "id": "paik_wonjo",
        "brand": "빽다방",
        "name": "원조커피",
        "price": 2500,
        "volume_ml": 590,
        "caffeine_mg": 270,
        "sugar_g": 26,
        "kcal": 260,
        "is_hot": False,
        "image_url": "",
    },
    {
        "id": "paik_decaf_latte",
        "brand": "빽다방",
        "name": "디카페인 카페라떼",
        "price": 3500,
        "volume_ml": 473,
        "caffeine_mg": 5,
        "sugar_g": 12,
        "kcal": 185,
        "is_hot": True,
        "image_url": "",
    },
]

MENU_MAP = {f"[{m['brand']}] {m['name']}": m for m in MENUS}
MENU_LABELS = list(MENU_MAP.keys())


def score_menu(menu: dict, condition: str, priority: str, weather_pref: str) -> tuple[float, list[str]]:
    """사용자 상태와 우선순위에 따라 메뉴 점수와 이유를 계산합니다."""
    score = 50.0
    reasons = []

    # 1) 컨디션 반영
    if condition == "졸음 퇴치·집중 필요":
        caffeine_bonus = min(menu["caffeine_mg"] / 10.0, 30.0)
        score += caffeine_bonus
        if menu["caffeine_mg"] >= 200:
            reasons.append(f"카페인 {menu['caffeine_mg']}mg으로 각성 효과가 강해요.")
        elif menu["caffeine_mg"] < 50:
            score -= 15
            reasons.append("카페인이 적어 졸음 깨기엔 약할 수 있어요.")
    elif condition == "저녁/수면 방해 피하기":
        if menu["caffeine_mg"] <= 30:
            score += 30
            reasons.append(f"카페인이 {menu['caffeine_mg']}mg 수준이라 수면 부담이 적어요.")
        else:
            score -= min(menu["caffeine_mg"] / 8.0, 35.0)
            reasons.append(f"카페인이 {menu['caffeine_mg']}mg 들어있어 저녁엔 수면을 방해할 수 있어요.")
    elif condition == "당·칼로리 충전 필요":
        sugar_bonus = min(menu["sugar_g"] * 0.9, 25.0)
        score += sugar_bonus
        if menu["sugar_g"] >= 20:
            reasons.append(f"당류 {menu['sugar_g']}g으로 빠른 에너지 보충에 유리해요.")

    # 2) 최우선 기준 반영
    if priority == "가성비(가격 대비 용량)":
        value_score = (menu["volume_ml"] / max(menu["price"], 1)) * 60
        score += min(value_score, 30.0)
        reasons.append(f"{menu['price']:,}원에 {menu['volume_ml']}ml로 가성비가 좋아요.")
    elif priority == "당류·칼로리 절제":
        penalty = (menu["sugar_g"] * 0.8) + (menu["kcal"] * 0.05)
        score -= min(penalty, 35.0)
        if menu["sugar_g"] <= 5:
            reasons.append(f"당류 {menu['sugar_g']}g, {menu['kcal']}kcal로 부담이 적어요.")
    elif priority == "고카페인 효율":
        eff = (menu["caffeine_mg"] / max(menu["price"], 1)) * 150
        score += min(eff, 30.0)
        reasons.append(f"가격 대비 카페인 효율이 높아요({menu['caffeine_mg']}mg).")

    # 3) 날씨/온도 성향 반영
    if weather_pref == "따뜻한 음료 선호" and menu["is_hot"]:
        score += 12
        reasons.append("따뜻한 메뉴라 쌀쌀한 날씨에 잘 어울려요.")
    elif weather_pref == "시원한 음료 선호" and not menu["is_hot"]:
        score += 12
        reasons.append("시원한 메뉴라 기분 전환에 좋아요.")

    return round(score, 1), reasons


# 세션 기록 초기화
if "battle_history" not in st.session_state:
    st.session_state.battle_history = []

st.title("☕ 저가커피 1:1 메뉴 대결")
st.caption("지금 내 상태에 맞는 메뉴를 2개 고르면, 조건에 더 잘 맞는 쪽을 골라드려요.")

# 1. 내 상태 설정
st.subheader("1. 지금 내 상태 설정")
col_c1, col_c2, col_c3 = st.columns(3)

with col_c1:
    condition = st.selectbox(
        "현재 컨디션",
        ["졸음 퇴치·집중 필요", "저녁/수면 방해 피하기", "당·칼로리 충전 필요", "무난한 일상 컨디션"],
    )
with col_c2:
    priority = st.selectbox(
        "가장 중요한 기준",
        ["가성비(가격 대비 용량)", "당류·칼로리 절제", "고카페인 효율"],
    )
with col_c3:
    weather_pref = st.radio(
        "원하는 온도 느낌",
        ["상관없음", "시원한 음료 선호", "따뜻한 음료 선호"],
        horizontal=True,
    )

st.divider()

# 2. 대결할 메뉴 2개 선택
st.subheader("2. 비교할 메뉴 2개 고르기")
col_m1, col_m2 = st.columns(2)

with col_m1:
    label_a = st.selectbox("후보 A", MENU_LABELS, index=0)
with col_m2:
    default_b_idx = 2 if len(MENU_LABELS) > 2 else 1
    label_b = st.selectbox("후보 B", MENU_LABELS, index=default_b_idx)

if label_a == label_b:
    st.warning("서로 다른 두 메뉴를 선택해 주세요!")
    st.stop()

menu_a = MENU_MAP[label_a]
menu_b = MENU_MAP[label_b]

# 후보 카드 미리보기
card_a, card_b = st.columns(2)
for col, m, tag in [(card_a, menu_a, "후보 A"), (card_b, menu_b, "후보 B")]:
    with col:
        with st.container(border=True):
            st.markdown(f"**{tag} · {m['brand']}**")
            st.markdown(f"### {m['name']}")
            if m.get("image_url"):
                st.image(m["image_url"], use_container_width=True)
            st.write(
                f"가격: **{m['price']:,}원** | 용량: **{m['volume_ml']}ml** | "
                f"카페인: **{m['caffeine_mg']}mg** | 당류: **{m['sugar_g']}g** | 열량: **{m['kcal']}kcal**"
            )

# 3. 대결 실행 및 결과 출력
if st.button("⚔️ 내 상태 기준으로 승자 고르기", type="primary", use_container_width=True):
    score_a, reasons_a = score_menu(menu_a, condition, priority, weather_pref)
    score_b, reasons_b = score_menu(menu_b, condition, priority, weather_pref)

    if score_a >= score_b:
        winner, loser = menu_a, menu_b
        w_score, l_score = score_a, score_b
        w_reasons, l_reasons = reasons_a, reasons_b
        winner_tag = "후보 A"
    else:
        winner, loser = menu_b, menu_a
        w_score, l_score = score_b, score_a
        w_reasons, l_reasons = reasons_b, reasons_a
        winner_tag = "후보 B"

    st.divider()
    st.subheader("3. 대결 결과")

    st.success(
        f"🏆 **추천 메뉴: [{winner['brand']}] {winner['name']}** ({winner_tag} · 적합도 {w_score}점 vs {l_score}점)"
    )

    if w_reasons:
        st.markdown("**왜 이 메뉴가 더 맞을까?**")
        for r in w_reasons:
            st.write(f"- {r}")

    # 스펙 비교 요약
    st.markdown("**두 메뉴 핵심 차이 (승자 기준)**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("가격 차이", f"{winner['price'] - loser['price']:+,}원", f"{winner['price']:,}원")
    c2.metric("용량 차이", f"{winner['volume_ml'] - loser['volume_ml']:+,}ml", f"{winner['volume_ml']}ml")
    c3.metric("카페인 차이", f"{winner['caffeine_mg'] - loser['caffeine_mg']:+,}mg", f"{winner['caffeine_mg']}mg")
    c4.metric("당류 차이", f"{winner['sugar_g'] - loser['sugar_g']:+,}g", f"{winner['sugar_g']}g")

    if l_reasons:
        st.caption(f"💡 참고로 [{loser['brand']}] {loser['name']} 쪽은 이런 점이 있어요: {' / '.join(l_reasons)}")

    # 히스토리 저장
    st.session_state.battle_history.insert(
        0,
        {
            "대결": f"{label_a} vs {label_b}",
            "승자": f"[{winner['brand']}] {winner['name']}",
            "컨디션": condition,
            "기준": priority,
        },
    )

# 4. 오늘의 대결 기록
if st.session_state.battle_history:
    st.divider()
    st.subheader("📜 오늘의 대결 기록")
    st.dataframe(st.session_state.battle_history, use_container_width=True, hide_index=True)
