import base64
import unicodedata
from html import escape
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

BRAND_COLORS = {
    "컴포즈커피": "#F2B705",
    "메가MGC커피": "#E85D04",
    "빽다방": "#2563EB",
}

NA = "확인 자료 없음"


def normalize_name(value):
    """한글 자모 분리 여부와 관계없이 같은 이름으로 비교합니다."""
    return unicodedata.normalize("NFC", str(value)).strip()


@st.cache_data(show_spinner=False)
def encode_photo(path_string, modified_ns, size):
    """파일 변경 시 캐시가 갱신되도록 수정 시각과 크기도 받습니다."""
    path = Path(path_string)
    ext = path.suffix.lower().lstrip(".")
    mime = MIME.get(ext)

    if mime is None:
        return None

    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return None

    return f"data:{mime};base64,{encoded}"


def photo_uri(brand, menu, variant):
    """
    images/{브랜드}_{메뉴명}_{옵션}.확장자 파일을 찾습니다.

    - 한글 완성형/자모 분리형 파일명 모두 인식
    - 확장자 대소문자 구분 없이 인식
    - 이미지 폴더나 파일이 없으면 None 반환
    """
    if not IMG_DIR.is_dir():
        return None

    target = normalize_name(
        f"{normalize_name(brand)}_{normalize_name(menu)}_"
        f"{normalize_name(variant)}"
    ).casefold()

    try:
        paths = sorted(IMG_DIR.iterdir(), key=lambda p: p.name)

        for path in paths:
            if not path.is_file():
                continue

            ext = path.suffix.lower().lstrip(".")
            if ext not in MIME:
                continue

            if normalize_name(path.stem).casefold() == target:
                stat = path.stat()
                return encode_photo(
                    str(path),
                    stat.st_mtime_ns,
                    stat.st_size,
                )

    except OSError:
        return None

    return None


st.markdown(
    """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

html, body, [class*="st-"], .stMarkdown, button, input, textarea {
  font-family: 'Pretendard', -apple-system, BlinkMacSystemFont,
    'Segoe UI', sans-serif;
}

footer, #MainMenu {visibility: hidden;}

.block-container {
  max-width: 1120px;
  padding-top: 2.2rem;
  padding-bottom: 4rem;
}

.hero {padding: 1.6rem 0 1.2rem 0;}

.hero .eyebrow {
  display: inline-block;
  font-size: .78rem;
  font-weight: 700;
  letter-spacing: .04em;
  padding: .25rem .65rem;
  border-radius: 999px;
  background: rgba(242,183,5,.16);
  color: #C48E00;
}

.hero h1 {
  font-size: 2.5rem;
  font-weight: 800;
  letter-spacing: -.03em;
  margin: .55rem 0 .35rem 0;
  padding: 0;
  line-height: 1.15;
}

.hero p {margin: 0; opacity: .68; font-size: 1.02rem;}

.notice {
  margin: .9rem 0 1.4rem 0;
  padding: .75rem 1rem;
  border-radius: 14px;
  font-size: .86rem;
  line-height: 1.5;
  background: rgba(128,128,128,.08);
  border: 1px solid rgba(128,128,128,.18);
  opacity: .9;
}

.stTextInput input {
  border-radius: 14px !important;
  padding: .85rem 1rem !important;
  font-size: 1.05rem !important;
}

div[data-baseweb="select"] > div {
  border-radius: 12px !important;
}

.stButton > button {
  border-radius: 999px;
  padding: .15rem .95rem;
  font-weight: 600;
  border: 1px solid rgba(128,128,128,.3);
  background: transparent;
}

.stButton > button:hover {
  border-color: #F2B705;
  color: #C48E00;
}

.stats {
  display: flex;
  gap: .75rem;
  margin: 1.1rem 0 1rem 0;
  flex-wrap: wrap;
}

.stat {
  flex: 1;
  min-width: 150px;
  padding: .9rem 1.1rem;
  border-radius: 16px;
  background: rgba(128,128,128,.07);
  border: 1px solid rgba(128,128,128,.16);
}

.stat .k {font-size: .78rem; opacity: .62; font-weight: 600;}

.stat .v {
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: -.02em;
  margin-top: .15rem;
}

.card {
  position: relative;
  padding: 1.15rem 1.2rem 1rem 1.2rem;
  border-radius: 20px;
  margin-bottom: 1rem;
  background: rgba(128,128,128,.07);
  border: 1px solid rgba(128,128,128,.2);
  border-top: 4px solid var(--accent, #F2B705);
  transition: transform .15s ease, box-shadow .15s ease;
}

.card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 28px rgba(0,0,0,.14);
}

.photo {
  aspect-ratio: 1/1;
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
  margin-bottom: .85rem;
}

.photo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.card .top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: .5rem;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  font-size: .82rem;
  font-weight: 700;
  opacity: .85;
}

.dot {
  width: .55rem;
  height: .55rem;
  border-radius: 50%;
  background: var(--accent, #F2B705);
  display: inline-block;
}

.badge {
  font-size: .7rem;
  font-weight: 800;
  padding: .2rem .55rem;
  border-radius: 999px;
  background: #16A34A;
  color: #fff;
  letter-spacing: .02em;
}

.name {
  font-size: 1.2rem;
  font-weight: 800;
  letter-spacing: -.02em;
  margin: .7rem 0 .1rem 0;
  line-height: 1.3;
}

.tag {
  display: inline-block;
  font-size: .72rem;
  font-weight: 700;
  padding: .14rem .55rem;
  border-radius: 999px;
  border: 1px solid rgba(128,128,128,.35);
  opacity: .85;
}

.price {
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -.03em;
  margin: .65rem 0 .2rem 0;
}

.price .unit {
  font-size: 1rem;
  font-weight: 700;
  margin-left: .15rem;
  opacity: .7;
}

.price.na {
  font-size: 1rem;
  font-weight: 600;
  opacity: .5;
  margin: 1.1rem 0 .7rem 0;
}

.meta {
  margin-top: .55rem;
  padding-top: .6rem;
  border-top: 1px dashed rgba(128,128,128,.3);
  font-size: .84rem;
}

.meta .row {
  display: flex;
  justify-content: space-between;
  gap: .8rem;
  padding: .18rem 0;
}

.meta .row span:first-child {opacity: .6;}
.meta .na {opacity: .45;}

.links {
  margin-top: .65rem;
  display: flex;
  flex-wrap: wrap;
  gap: .4rem;
}

.links a {
  font-size: .74rem;
  font-weight: 600;
  text-decoration: none;
  padding: .22rem .6rem;
  border-radius: 999px;
  border: 1px solid rgba(128,128,128,.3);
  color: inherit;
  opacity: .8;
}

.links a:hover {
  border-color: #F2B705;
  color: #C48E00;
  opacity: 1;
}

.verified {margin-top: .6rem; font-size: .72rem; opacity: .5;}

.empty {
  text-align: center;
  padding: 2.6rem 1rem;
  border-radius: 20px;
  margin-top: .8rem;
  border: 1px dashed rgba(128,128,128,.35);
  opacity: .85;
}

.empty .big {font-size: 2.2rem;}
.empty .t {font-weight: 700; margin-top: .3rem;}
.empty .s {font-size: .88rem; opacity: .65; margin-top: .2rem;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
  <span class="eyebrow">COFFEE PICK</span>
  <h1>☕ 커피픽</h1>
  <p>컴포즈커피 · 메가MGC커피 · 빽다방, 같은 메뉴를 한눈에 비교해요.</p>
</div>
<div class="notice">
  확인된 CSV 자료만 표시합니다.
  미확인 항목은 "확인 자료 없음"으로 보이며 0점·0원으로 처리하지 않습니다.
  가격은 지점·옵션·시점에 따라 달라질 수 있어요.
</div>
""",
    unsafe_allow_html=True,
)

rows, warnings = load_data(BASE_DIR / "data" / "menus.csv")

if "q" not in st.session_state:
    st.session_state.q = ""

c_query, c_brand = st.columns([3, 2])

with c_query:
    query = st.text_input(
        "메뉴 검색",
        key="q",
        placeholder="예: 아메리카노, 라떼",
        label_visibility="collapsed",
    )

with c_brand:
    selected = st.multiselect(
        "비교 브랜드",
        BRANDS,
        default=list(BRANDS),
        label_visibility="collapsed",
    )

c_variant, c_sort, c_reload = st.columns([3, 3, 1])

with c_variant:
    variant_label = st.radio(
        "옵션",
        ["전체", "HOT", "ICE"],
        horizontal=True,
        label_visibility="collapsed",
    )

with c_sort:
    sort_label = st.radio(
        "정렬",
        ["가격 낮은 순", "평점 높은 순"],
        horizontal=True,
        label_visibility="collapsed",
    )

with c_reload:
    if st.button(
        "새로고침",
        help="CSV나 이미지를 변경한 후 누르세요.",
    ):
        st.cache_data.clear()
        st.rerun()


def pick(name):
    st.session_state.q = name


if rows:
    names = sorted({r["menu_name"] for r in rows})[:8]
    chips = st.columns(max(len(names), 1))

    for col, name in zip(chips, names):
        col.button(
            name,
            key=f"chip_{name}",
            on_click=pick,
            args=(name,),
            use_container_width=True,
        )


def fmt_price(value):
    return None if value is None else f"{value:,.0f}"


def meta_row(label, value):
    safe_label = escape(str(label))

    if value is None or value == "":
        return (
            f'<div class="row"><span>{safe_label}</span>'
            f'<span class="na">{NA}</span></div>'
        )

    return (
        f'<div class="row"><span>{safe_label}</span>'
        f"<span>{escape(str(value))}</span></div>"
    )


def render_card(r, cheapest):
    color = BRAND_COLORS.get(r["brand"], "#F2B705")
    price = fmt_price(r["price_krw"])

    if price is not None:
        price_html = (
            f'<div class="price">{price}'
            '<span class="unit">원</span></div>'
        )
    else:
        price_html = f'<div class="price na">{NA}</div>'

    badge = ""
    if cheapest is not None and r["price_krw"] == cheapest:
        badge = '<span class="badge">최저가</span>'

    volume = (
        None
        if r["volume_ml"] is None
        else f'{r["volume_ml"]:,.0f}mL'
    )

    rating = None
    if r["rating"] is not None:
        if r.get("rating_scale") is not None:
            rating = f'{r["rating"]:g}/{r["rating_scale"]:g}'
        else:
            rating = f'{r["rating"]:g}'

        if r.get("rating_normalized") is not None:
            rating += f' (5점 환산 {r["rating_normalized"]:.2f})'

    links = []

    source_fields = [
        ("메뉴", "menu_source_url", None),
        ("가격", "price_source_url", "price_krw"),
        ("용량", "volume_source_url", "volume_ml"),
        ("평점", "rating_source_url", "rating"),
        ("맛 평가", "taste_source_url", "taste"),
        ("리뷰", "review_source_url", "review"),
    ]

    for label, field, metric in source_fields:
        url = r.get(field)

        if url and (metric is None or r.get(metric) is not None):
            safe_url = escape(str(url), quote=True)
            links.append(
                f'<a href="{safe_url}" target="_blank" '
                f'rel="noopener noreferrer">{label} 출처</a>'
            )

    photo = photo_uri(
        r["brand"],
        r["menu_name"],
        r["variant"],
    )

    photo_html = ""
    if photo:
        alt = escape(
            f'{r["brand"]} {r["menu_name"]} {r["variant"]}',
            quote=True,
        )
        photo_html = (
            f'<div class="photo">'
            f'<img src="{photo}" alt="{alt}">'
            f"</div>"
        )

    brand = escape(str(r["brand"]))
    menu = escape(str(r["menu_name"]))
    variant = escape(str(r["variant"]))
    verified_at = escape(str(r.get("verified_at") or NA))

    return (
        f'<div class="card" style="--accent:{color}">'
        f"{photo_html}"
        f'<div class="top">'
        f'<span class="brand"><span class="dot"></span>{brand}</span>'
        f"{badge}</div>"
        f'<div class="name">{menu} '
        f'<span class="tag">{variant}</span></div>'
        f"{price_html}"
        f'<div class="meta">'
        f'{meta_row("용량", volume)}'
        f'{meta_row("평점", rating)}'
        f'{meta_row("맛 평가", r.get("taste"))}'
        f'{meta_row("리뷰", r.get("review"))}'
        f"</div>"
        f'<div class="links">{"".join(links)}</div>'
        f'<div class="verified">확인일 {verified_at}</div>'
        f"</div>"
    )


def empty(icon, title, sub=""):
    st.markdown(
        f'<div class="empty">'
        f'<div class="big">{escape(icon)}</div>'
        f'<div class="t">{escape(title)}</div>'
        f'<div class="s">{escape(sub)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


if not rows:
    empty(
        "📭",
        "표시할 확인 데이터가 없어요",
        "data/menus.csv에 확인된 메뉴 자료를 채워 주세요.",
    )

elif not selected:
    empty(
        "🏷️",
        "비교할 브랜드를 선택해 주세요",
        "오른쪽 위 칸에서 하나 이상 고를 수 있어요.",
    )

elif not query.strip():
    empty(
        "🔎",
        "메뉴명을 입력해 보세요",
        "위 버튼으로 바로 검색할 수도 있어요.",
    )

else:
    results = search(
        rows,
        query,
        selected,
        "rating" if sort_label == "평점 높은 순" else "price",
    )

    if variant_label != "전체":
        results = [
            r for r in results
            if str(r["variant"]).strip().upper() == variant_label
        ]

    if not results:
        empty(
            "🥲",
            f""{query}" 검색 결과가 없어요",
            "다른 메뉴명으로 검색하거나 CSV 자료를 확인해 주세요.",
        )

    else:
        prices = [
            r["price_krw"]
            for r in results
            if r["price_krw"] is not None
        ]

        cheapest = min(prices) if prices else None

        best = (
            next(
                (r for r in results if r["price_krw"] == cheapest),
                None,
            )
            if cheapest is not None
            else None
        )

        cheapest_text = (
            f"{fmt_price(cheapest)}원"
            if cheapest is not None
            else NA
        )

        best_text = (
            escape(f'{best["brand"]} {best["variant"]}')
            if best is not None
            else NA
        )

        st.markdown(
            '<div class="stats">'
            '<div class="stat">'
            '<div class="k">검색 결과</div>'
            f'<div class="v">{len(results)}건</div>'
            "</div>"
            '<div class="stat">'
            '<div class="k">최저가</div>'
            f'<div class="v">{cheapest_text}</div>'
            "</div>"
            '<div class="stat">'
            '<div class="k">최저가 메뉴</div>'
            f'<div class="v">{best_text}</div>'
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        missing = [
            brand
            for brand in selected
            if not any(r["brand"] == brand for r in results)
        ]

        if missing:
            st.caption(
                "확인 메뉴 데이터가 없는 브랜드: "
                + ", ".join(missing)
            )

        for start in range(0, len(results), 3):
            cols = st.columns(3)

            for col, r in zip(cols, results[start:start + 3]):
                col.markdown(
                    render_card(r, cheapest),
                    unsafe_allow_html=True,
                )

if warnings:
    with st.expander(f"데이터 확인 안내 
