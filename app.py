import math
import unicodedata
from html import escape
from pathlib import Path

import streamlit as st
from core import BRANDS, load_data, search
import recommendation as rec


st.set_page_config(
    page_title="CoffeePick · 저가커피 메뉴 비교 & 추천",
    page_icon="☕",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "images"

MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

NA = "확인 자료 없음"

BRAND_COLORS = {
    "컴포즈커피": "#C8961E",
    "메가MGC커피": "#A14314",
    "빽다방": "#5B7FB5",
}


def normalize(value):
    return unicodedata.normalize("NFC", str(value)).strip().casefold()


@st.cache_data(show_spinner=False)
def read_photo(path_string, modified_ns, size):
    path = Path(path_string)
    mime = MIME.get(path.suffix.lower().lstrip("."))
    if mime is None:
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def find_photo(brand, menu, variant):
    target = normalize(str(brand) + "_" + str(menu) + "_" + str(variant))
    try:
        if not IMG_DIR.is_dir():
            return None
        for path in sorted(IMG_DIR.iterdir(), key=lambda item: item.name):
            if not path.is_file():
                continue
            if path.suffix.lower().lstrip(".") not in MIME:
                continue
            if normalize(path.stem) == target:
                info = path.stat()
                return read_photo(str(path), info.st_mtime_ns, info.st_size)
    except OSError:
        return None
    return None


def number(value):
    if value is None or value == "":
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def price_text(value):
    value = number(value)
    return NA if value is None else format(value, ",.0f") + "원"


def rating_text(row):
    value = number(row.get("rating"))
    if value is None:
        return NA
    scale = number(row.get("rating_scale"))
    text = format(value, "g")
    if scale is not None and scale > 0:
        text += "/" + format(scale, "g")
    normalized = number(row.get("rating_normalized"))
    if normalized is not None:
        text += " (5점 환산 " + format(normalized, ".2f") + ")"
    return text


def pick_menu(name):
    st.session_state["q"] = name


def render_card(row, cheapest):
    brand = str(row.get("brand") or "")
    menu = str(row.get("menu_name") or "")
    variant = str(row.get("variant") or "")
    color = BRAND_COLORS.get(brand, "#8B5E3C")
    price = number(row.get("price_krw"))
    is_cheapest = cheapest is not None and price == cheapest
    badge = "<span style='font-size:0.8rem;color:#2E7D32;font-weight:800;margin-left:8px;'>🏷️ 최저가</span>" if is_cheapest else ""

    with st.container(border=True):
        header = (
            "<div style='border-left:6px solid " + color + ";padding:2px 0 6px 12px;'>"
            "<div style='font-size:0.8rem;font-weight:700;color:" + color + ";'>"
            + escape(brand) + "</div>"
            "<div style='font-size:1.25rem;font-weight:800;line-height:1.3;color:#3E2723;'>"
            + escape(menu)
            + " <span style='font-size:0.8rem;color:#8D6E63;'>" + escape(variant) + "</span></div>"
            "<div style='font-size:1.5rem;font-weight:800;color:#6F4E37;'>"
            + escape(price_text(price)) + badge + "</div>"
            "</div>"
        )
        st.markdown(header, unsafe_allow_html=True)
        photo = find_photo(brand, menu, variant)
        if photo is not None:
            st.image(photo, use_container_width=True)
        else:
            st.caption("📷 등록된 이미지가 없습니다")
        volume = number(row.get("volume_ml"))
        volume_label = NA if volume is None else format(volume, ",.0f") + "mL"
        st.write("🥤 용량: " + volume_label)
        st.write("⭐ 평점: " + rating_text(row))
        st.write("👅 맛 평가: " + str(row.get("taste") or NA))
        st.write("💬 리뷰: " + str(row.get("review") or NA))
        source_fields = [
            ("메뉴", "menu_source_url", None),
            ("가격", "price_source_url", "price_krw"),
            ("용량", "volume_source_url", "volume_ml"),
            ("평점", "rating_source_url", "rating"),
            ("맛 평가", "taste_source_url", "taste"),
            ("리뷰", "review_source_url", "review"),
        ]
        for label, field, metric in source_fields:
            url = str(row.get(field) or "").strip()
            if not url.startswith(("https://", "http://")):
                continue
            if metric is not None and row.get(metric) in (None, ""):
                continue
            st.link_button(label + " 출처", url)
        st.caption("확인일 " + str(row.get("verified_at") or NA))


st.markdown(
    """
<style>
.stApp {
  background: #F7F1E3;
  color: #3E2723;
}
.block-container { max-width: 1120px; padding-top: 2rem; }
h1, h2, h3, p, label, .stMarkdown { color: #3E2723 !important; }

[data-testid="stVerticalBlockBorderWrapper"] {
  background: #FFFDF8;
  border: 1px solid #E4D8C2;
  border-radius: 22px;
  box-shadow: 0 6px 20px rgba(111,78,55,0.14);
}

.stButton > button, .stLinkButton > a {
  background: #6F4E37 !important;
  color: #FFF8EF !important;
  font-weight: 800 !important;
  border: none !important;
  border-radius: 999px !important;
  padding: 0.5rem 1.1rem !important;
  box-shadow: 0 4px 0 #4E3626 !important;
  transition: transform .08s ease, box-shadow .08s ease !important;
}
.stButton > button:hover, .stLinkButton > a:hover {
  transform: translateY(2px) !important;
  box-shadow: 0 2px 0 #4E3626 !important;
  background: #855C40 !important;
}
.stButton > button:active {
  transform: translateY(4px) !important;
  box-shadow: 0 0 0 #4E3626 !important;
}

[data-testid="stHorizontalBlock"] .stButton > button {
  background: #C9A27A !important;
  color: #3E2723 !important;
  box-shadow: 0 4px 0 #A9825B !important;
}
[data-testid="stHorizontalBlock"] .stButton > button:hover {
  background: #D8B890 !important;
  box-shadow: 0 2px 0 #A9825B !important;
}

.stTextInput input, div[data-baseweb="select"] > div {
  background: #FFFDF8 !important;
  color: #3E2723 !important;
  border-radius: 14px !important;
  border: 1px solid #6F4E37 !important;
}

span[data-baseweb="tag"] {
  background: #8B5E3C !important;
  color: #FFF8EF !important;
}
span[data-baseweb="tag"] svg { fill: #FFF8EF !important; }

[data-baseweb="radio"] div[aria-checked="true"] > div:first-child {
  background: #6F4E37 !important;
  border-color: #6F4E37 !important;
}
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #3E2723 !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("☕ CoffeePick")
st.write("컴포즈커피 · 메가MGC커피 · 빽다방, 같은 메뉴를 한눈에 비교하고 추천받으세요!")
st.info(
    "확인된 CSV 자료만 표시합니다. 미확인 값은 0점·0원이 아닌 '확인 자료 없음'으로 "
    "표시합니다. 가격은 지점·옵션·시점에 따라 달라질 수 있어요."
)

# 메인 탭 구성 (기존 비교 기능 + 신규 추천 기능)
tab_search, tab_recommend = st.tabs(["🔍 메뉴 검색 및 비교", "🎯 취향 맞춤 추천"])

# ==========================================
# 탭 1: 기존 메뉴 검색 및 비교 (100% 동일)
# ==========================================
with tab_search:
    if "q" not in st.session_state:
        st.session_state["q"] = ""

    query_col, brand_col = st.columns([3, 2])
    with query_col:
        query = st.text_input("메뉴 검색", key="q", placeholder="예: 아메리카노, 라떼")
    with brand_col:
        selected = st.multiselect("비교 브랜드", list(BRANDS), default=list(BRANDS))

    variant_col, sort_col, reload_col = st.columns([3, 3, 1])
    with variant_col:
        variant_label = st.radio("옵션", ["전체", "HOT", "ICE"], horizontal=True)
    with sort_col:
        sort_label = st.radio("정렬", ["가격 낮은 순", "평점 높은 순"], horizontal=True)
    with reload_col:
        if st.button("새로고침", help="CSV나 이미지를 변경한 후 누르세요."):
            st.cache_data.clear()
            st.rerun()

    rows, warnings = load_data(BASE_DIR / "data" / "menus.csv")

    if rows:
        names = sorted({str(row["menu_name"]) for row in rows})[:8]
        for start in range(0, len(names), 4):
            chip_cols = st.columns(4)
            for col, name in zip(chip_cols, names[start:start + 4]):
                col.button(
                    name,
                    key="chip_" + name,
                    on_click=pick_menu,
                    args=(name,),
                    use_container_width=True,
                )

    if not rows:
        st.warning(
            "표시할 확인 데이터가 없어요. data/menus.csv와 아래 데이터 확인 안내를 "
            "확인해 주세요."
        )
    elif not selected:
        st.info("비교할 브랜드를 하나 이상 선택해 주세요.")
    elif not query.strip():
        st.info("메뉴명을 입력하거나 위 메뉴 버튼을 눌러 주세요.")
    else:
        sort_key = "rating" if sort_label == "평점 높은 순" else "price"
        results = search(rows, query, selected, sort_key)
        if variant_label != "전체":
            results = [
                row
                for row in results
                if str(row.get("variant", "")).strip().upper() == variant_label
            ]
        if not results:
            st.info(query + " 검색 결과가 없어요. 다른 메뉴명으로 검색해 주세요.")
        else:
            prices = [number(row.get("price_krw")) for row in results]
            prices = [value for value in prices if value is not None]
            cheapest = min(prices) if prices else None
            best = next(
                (
                    row
                    for row in results
                    if cheapest is not None
                    and number(row.get("price_krw")) == cheapest
                ),
                None,
            )
            stat_cols = st.columns(3)
            stat_cols[0].metric("검색 결과", str(len(results)) + "건")
            stat_cols[1].metric("최저가", price_text(cheapest))
            best_label = NA if best is None else str(best["brand"]) + " " + str(best["variant"])
            stat_cols[2].metric("최저가 메뉴", best_label)
            missing = [
                brand
                for brand in selected
                if not any(row["brand"] == brand for row in results)
            ]
            if missing:
                st.caption("확인 메뉴 데이터가 없는 브랜드: " + ", ".join(missing))
            for start in range(0, len(results), 3):
                card_cols = st.columns(3)
                for col, row in zip(card_cols, results[start:start + 3]):
                    with col:
                        render_card(row, cheapest)

    if warnings:
        with st.expander("데이터 확인 안내 (" + str(len(warnings)) + "건)"):
            for warning in warnings:
                st.warning(str(warning))


# ==========================================
# 탭 2: 신규 추가된 음료 맞춤 추천 섹션
# ==========================================
with tab_recommend:
    st.subheader("💡 어떤 음료를 마실지 고민되시나요?")
    st.write("아래 설문 항목을 선택하시면 딱 맞는 음료를 추천해 드립니다.")

    answers = {"taste": {}, "mood": {}, "budget": {}}

    with st.form("recommendation_form"):
        # 설문 섹션 1: 취향
        st.markdown("### 1. 👅 맛과 취향")
        c1, c2 = st.columns(2)
        with c1:
            cat_selected = st.multiselect(
                "선호하는 음료 종류",
                options=list(rec.CATEGORIES.keys()),
                format_func=lambda x: rec.CATEGORIES[x],
            )
            if cat_selected:
                answers["taste"]["category"] = cat_selected

            flav_selected = st.multiselect(
                "선호하는 맛",
                options=list(rec.FLAVORS.keys()),
                format_func=lambda x: rec.FLAVORS[x],
            )
            if flav_selected:
                answers["taste"]["flavor"] = flav_selected

        with c2:
            answers["taste"]["sweetness"] = st.select_slider(
                "단맛 정도",
                options=[0, 1, 2, 3],
                format_func=lambda x: ["단맛 없음", "은은하게", "적당히", "많이 달콤"][x],
                value=1,
            )
            answers["taste"]["temperature"] = st.radio(
                "음료 온도",
                options=["any", "ice", "hot"],
                format_func=lambda x: {"any": "상관없음", "ice": "ICE (차가움)", "hot": "HOT (따뜻함)"}[x],
                horizontal=True,
            )

        st.divider()

        # 설문 섹션 2: 기분 및 카페인
        st.markdown("### 2. ⚡ 기분 & 카페인")
        m1, m2 = st.columns(2)
        with m1:
            answers["mood"]["activity"] = st.selectbox(
                "현재 상황/활동",
                options=["study", "relax", "work", "dessert", "new"],
                format_func=lambda x: {
                    "study": "공부/과제 중",
                    "relax": "휴식/기분전환",
                    "work": "업무/집중",
                    "dessert": "디저트와 함께",
                    "new": "새로운 메뉴 도전을 위해",
                }[x],
            )
            answers["mood"]["feeling"] = st.selectbox(
                "현재 기분",
                options=["tired", "refresh", "energetic", "calm"],
                format_func=lambda x: {
                    "tired": "피곤하고 졸림 😴",
                    "refresh": "기분 전환 필요 🌿",
                    "energetic": "활기차고 상쾌함 ⚡",
                    "calm": "편안하고 차분함 ☕",
                }[x],
            )

        with m2:
            answers["mood"]["caffeine"] = st.radio(
                "카페인 필요도",
                options=["any", "high", "low", "none"],
                format_func=lambda x: {
                    "any": "상관없음",
                    "high": "높음 (잠깨기/집중)",
                    "low": "낮음 (적당히)",
                    "none": "디카페인/없음",
                }[x],
                horizontal=True,
            )

        st.divider()

        # 설문 섹션 3: 예산 및 사이즈
        st.markdown("### 3. 💰 예산 & 사이즈")
        b1, b2 = st.columns(2)
        with b1:
            answers["budget"]["price"] = st.selectbox(
                "원하는 가격대",
                options=list(rec.BUDGETS.values()),
                format_func=lambda x: [k for k, v in rec.BUDGETS.items() if v == x][0],
            )
        with b2:
            answers["budget"]["size"] = st.radio(
                "음료 용량",
                options=["any", "small", "medium", "large"],
                format_func=lambda x: {"any": "상관없음", "small": "작음", "medium": "보통", "large": "대용량"}[x],
                horizontal=True,
            )

        submit_btn = st.form_submit_button("🎯 맞춤 음료 추천받기", use_container_width=True)

    if submit_btn or st.session_state.get("rec_run"):
        st.session_state["rec_run"] = True
        rec_result = rec.recommend(rec.MENU, answers, top_n=6)

        st.markdown("### ✨ 추천 메뉴 결과")
        results = rec_result.get("results", [])

        if not results:
            st.warning("조건에 부합하는 추천 메뉴를 찾지 못했습니다.")
        else:
            for start in range(0, len(results), 3):
                rec_cols = st.columns(3)
                for col, res in zip(rec_cols, results[start:start + 3]):
                    item = res["item"]
                    score = res["score"]
                    reasons = res.get("reasons", [])

                    with col:
                        with st.container(border=True):
                            st.markdown(f"### {item['name']}")
                            st.markdown(f"**카테고리:** {rec.CATEGORY_LABEL.get(item['category'], item['category'])}")
                            st.markdown(f"**가격:** `{item['price']:,}원`")
                            if score is not None:
                                st.progress(int(score) / 100)
                                st.caption(f"🎯 일치도: **{score}%**")

                            if reasons:
                                st.markdown("**추천 이유:** " + ", ".join([f"`{r}`" for r in reasons]))

                            # 메인 검색으로 연동시키는 버튼
                            if st.button(f"🔍 '{item['name']}' 검색해보기", key=f"rec_search_{item['name']}"):
                                st.session_state["q"] = item["name"]
                                st.rerun()
