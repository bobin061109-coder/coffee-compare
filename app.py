import math
import unicodedata
from pathlib import Path

import streamlit as st
from core import BRANDS, load_data, search


st.set_page_config(
    page_title="커피픽 · 저가커피 메뉴 비교",
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
    "컴포즈커피": "#F2B705",
    "메가MGC커피": "#E85D04",
    "빽다방": "#2563EB",
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
    color = BRAND_COLORS.get(brand, "#F2B705")
    price = number(row.get("price_krw"))
    is_cheapest = cheapest is not None and price == cheapest

    with st.container(border=True):
        badge = "  🏷️ 최저가" if is_cheapest else ""
        st.markdown(
            "<div style='border-left:6px solid " + color + ";padding:2px 0 2px 12px;'>"
            "<div style='font-size:0.8rem;font-weight:700;color:" + color + ";'>"
            + menu + " <span style='font-size:0.8rem;color:#888;'>" + variant
            + "</span></div>".replace(menu + " <span", brand + "</div>"
            "<div style='font-size:1.25rem;font-weight:800;line-height:1.3;color:#222;'>"
            + menu + " <span")
            + "<div style='font-size:1.5rem;font-weight:800;color:#E85D04;'>"
            + price_text(price) + "<span style='font-size:0.85rem;color:#16A34A;"
            "font-weight:700;'>" + badge + "</span></div>"
            "</div>",
            unsafe_allow_html=True,
        )
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
  background: linear-gradient(135deg, #FFF3D6 0%, #FFE0C2 50%, #FFD3E0 100%);
}
.block-container { max-width: 1120px; padding-top: 2rem; }
[data-testid="stVerticalBlockBorderWrapper"] {
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.08);
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("☕ 커피픽")
st.write("컴포즈커피 · 메가MGC커피 · 빽다방, 같은 메뉴를 한눈에 비교해요!")
st.info(
    "확인된 CSV 자료만 표시합니다. 미확인 값은 0점·0원이 아닌 '확인 자료 없음'으로 "
    "표시합니다. 가격은 지점·옵션·시점에 따라 달라질 수 있어요."
)

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
