"""저가커피 메뉴 비교 + 공식 이벤트 표시용 Streamlit 앱.
이 파일로 기존 app.py를 교체할 수 있습니다. core.py에는 의존하지 않습니다.
CSV 출처와 확인 표시가 없는 데이터는 임의로 채우지 않습니다.
"""
import csv
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BRANDS = ["컴포즈커피", "메가MGC커피", "빽다방"]
MENU_COLUMNS = [
    "brand", "menu_name", "variant", "data_verified", "verified_at",
    "menu_source_url", "price_krw", "price_source_url", "volume_ml",
    "volume_source_url", "rating", "rating_scale", "rating_source_url",
    "taste", "taste_source_url", "review", "review_source_url",
]

st.set_page_config(page_title="저가커피 비교 & 이벤트", page_icon="☕", layout="wide")


def valid_url(value):
    try:
        parsed = urlparse(str(value or "").strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def number(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        result = float(str(value).replace(",", "").strip())
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def read_menus():
    path = DATA_DIR / "menus.csv"
    if not path.exists():
        return [], "메뉴 CSV를 찾을 수 없습니다. data/menus.csv를 확인해 주세요."
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames or not set(MENU_COLUMNS).issubset(reader.fieldnames):
                return [], "메뉴 CSV 열 구성이 맞지 않습니다. 기존 CSV 양식을 확인해 주세요."
            rows = []
            for raw in reader:
                row = {key: (raw.get(key) or "").strip() for key in MENU_COLUMNS}
                if row["brand"] not in BRANDS or not row["menu_name"]:
                    continue
                try:
                    checked = date.fromisoformat(row["verified_at"])
                    is_currently_verified = row["data_verified"].lower() == "true" and checked <= date.today()
                except ValueError:
                    is_currently_verified = False
                if not is_currently_verified or not valid_url(row["menu_source_url"]):
                    continue
                for metric, source in (
                    ("price_krw", "price_source_url"),
                    ("volume_ml", "volume_source_url"),
                    ("rating", "rating_source_url"),
                    ("taste", "taste_source_url"),
                    ("review", "review_source_url"),
                ):
                    if row[metric] and not valid_url(row[source]):
                        row[metric] = ""
                for metric in ("price_krw", "volume_ml", "rating"):
                    if row[metric] and number(row[metric]) is None:
                        row[metric] = ""
                rows.append(row)
            return rows, ""
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], f"메뉴 CSV를 읽지 못했습니다: {exc}"


def read_events():
    path = DATA_DIR / "events.csv"
    if not path.exists():
        return [], "아직 이벤트 파일이 없습니다. data/events.csv를 추가해 주세요."
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames or not {"brand", "title", "url"}.issubset(reader.fieldnames):
                return [], "이벤트 CSV 열 구성이 맞지 않습니다."
            rows = []
            for raw in reader:
                row = {key: (value or "").strip() for key, value in raw.items()}
                if row.get("brand") in BRANDS and row.get("title") and valid_url(row.get("url")):
                    row["title"] = re.sub(r"\s*메가MGC커피$", "", row["title"])
                    rows.append(row)
            return rows, ""
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], f"이벤트 파일을 읽지 못했습니다: {exc}"


OFFICIAL_PAGES = {
    "컴포즈커피": "https://composecoffee.com/event",
    "메가MGC커피": "https://www.mega-mgccoffee.com/bbs/?bbs_category=3",
    "빽다방": "https://paikdabang.com/news/?cate=event",
}
KST = timezone(timedelta(hours=9))
STALE_DAYS = 2  # 이 기간 넘게 새로 확인이 안 되면 경고

# 칸(탭)별 키워드. 제목에 하나라도 들어 있으면 그 칸에 표시합니다.
CATEGORIES = {
    "💸 할인": [r"할인", r"반값", r"\d+\s*%", r"\d[\d,]*\s*원에", r"\d+\s*천\s*원에", r"특가", r"\d[\d,]*\s*원\s*프로모션"],
    "🎟️ 쿠폰·적립": [r"쿠폰", r"적립", r"프리퀀시", r"증정", r"경품", r"스탬프", r"리워드"],
    "🤝 콜라보": [r"콜라보", r"[가-힣A-Za-z0-9\]]\s*[xX×]\s*[가-힣A-Za-z\[]", r"\[[^\]]*\|[^\]]*\]"],
    "🆕 신메뉴": [r"신메뉴", r"출시", r"신제품", r"NEW", r"시즌\s*메뉴", r"한정\s*메뉴"],
}


def parse_checked(value):
    try:
        return datetime.strptime(value.replace(" UTC", ""), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def make_date(year, month, day):
    try:
        return date(year, month, day)
    except ValueError:
        return None


# (8/19~8/21), (6.12~6.21), (~12/14), (1/2~) 같은 제목 속 기간을 찾습니다.
PERIOD = re.compile(r"(?:(\d{1,2})\s*[./]\s*(\d{1,2}))?\s*[~∼-]\s*(?:(\d{1,2})\s*[./]\s*(\d{1,2}))?")


def event_period(title, today):
    for m in PERIOD.finditer(title):
        sm, sd, em, ed = m.groups()
        if not (sm or em):
            continue
        year_match = re.search(r"(20\d{2})\s*년?", title)
        year = int(year_match.group(1)) if year_match else today.year
        start = make_date(year, int(sm), int(sd)) if sm else None
        # 연도가 제목에 없고 시작일이 두 달 넘게 미래면 작년 게시물로 봅니다.
        if start and not year_match and start - today > timedelta(days=60):
            year -= 1
            start = make_date(year, int(sm), int(sd))
        end = None
        if em:
            end = make_date(year, int(em), int(ed))
            if end and start and end < start:  # 12/20~1/5 처럼 해를 넘기는 경우
                end = make_date(year + 1, int(em), int(ed))
            if end and not start and not year_match and end - today > timedelta(days=300):
                end = make_date(year - 1, int(em), int(ed))
        if start or end:
            return start, end
    return None, None


def event_status(title, today):
    start, end = event_period(title, today)
    if not start and not end:
        return "❔ 기간 원문 확인", "gray"
    if start and today < start:
        return f"⏳ 예정 ({start.month}/{start.day}부터)", "blue"
    if end and today > end:
        return f"⛔ 만료 ({end.month}/{end.day} 종료)", "red"
    if end:
        return f"✅ 진행중 ({end.month}/{end.day}까지)", "green"
    # 시작일만 있고 종료일이 없으면 진행중이라고 단정하지 않습니다.
    return f"❔ {start.month}/{start.day} 시작 · 종료일 원문 확인", "gray"


def matches(title, patterns):
    return any(re.search(p, title) for p in patterns)


def show_events(items, today):
    if not items:
        st.info("조건에 맞는 게시물이 없습니다.")
        return
    for event in items:
        label, color = event["_status"]
        with st.container(border=True):
            st.markdown(f":{color}-badge[{label}]  ·  **{event['brand']}**")
            st.subheader(event["title"])
            cats = [name for name, pats in CATEGORIES.items() if matches(event["title"], pats)]
            if cats:
                st.caption(" ".join(cats))
            st.link_button("공식 게시물 열기", event["url"])



def metric_sort_value(row, key):
    return number(row.get(key))


st.title("☕ 저가커피 메뉴 비교")
st.caption("컴포즈커피 · 메가MGC커피 · 빽다방")
st.info("출처와 확인일이 있는 값만 표시합니다. 확인되지 않은 가격·평점·리뷰는 임의로 만들지 않습니다.")
menu_tab, event_tab = st.tabs(["🔎 메뉴 비교", "📣 브랜드 이벤트"])

with menu_tab:
    query = st.text_input("메뉴명 검색", placeholder="예: 아메리카노, 라떼")
    selected_brands = st.multiselect("비교할 브랜드", BRANDS, default=BRANDS)
    sort_label = st.radio("정렬 기준", ["가격 낮은 순", "평점 높은 순"], horizontal=True)
    rows, menu_error = read_menus()
    if menu_error:
        st.warning(menu_error)
    elif not rows:
        st.info("확인된 메뉴 자료가 없습니다. data/menus.csv에 원문 확인 자료를 추가해 주세요.")
    elif not selected_brands:
        st.info("비교할 브랜드를 하나 이상 선택해 주세요.")
    elif not query.strip():
        st.info("메뉴명을 입력하면 브랜드별 메뉴를 비교합니다.")
    else:
        q = re.sub(r"\s+", "", query).casefold()
        matched = [
            row for row in rows
            if row["brand"] in selected_brands
            and q in re.sub(r"\s+", "", row["menu_name"] + row["variant"]).casefold()
        ]
        key = "price_krw" if sort_label == "가격 낮은 순" else "rating"
        matched.sort(
            key=lambda row: (
                metric_sort_value(row, key) is None,
                (metric_sort_value(row, key) or 0) * (1 if key == "price_krw" else -1),
                row["brand"],
            )
        )
        if not matched:
            st.warning("검색 결과가 없습니다. 메뉴명을 바꾸거나 브랜드 선택을 확인해 주세요.")
        else:
            missing = [brand for brand in selected_brands if not any(r["brand"] == brand for r in matched)]
            if missing:
                st.caption("검색된 자료가 없는 브랜드: " + ", ".join(missing))
            for row in matched:
                with st.container(border=True):
                    st.subheader(f"{row['brand']} · {row['menu_name']} {row['variant'] or ''}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("가격", f"{number(row['price_krw']):,.0f}원" if number(row['price_krw']) is not None else "확인 자료 없음")
                    c2.metric("용량", f"{number(row['volume_ml']):,.0f}mL" if number(row['volume_ml']) is not None else "확인 자료 없음")
                    rating = number(row["rating"])
                    scale = number(row["rating_scale"])
                    c3.metric("평점", f"{rating:g}/{scale:g}" if rating is not None and scale is not None else (f"{rating:g}" if rating is not None else "확인 자료 없음"))
                    st.write("**맛 평가:** " + (row["taste"] or "확인 자료 없음"))
                    st.write("**리뷰:** " + (row["review"] or "확인 자료 없음"))
                    st.caption("확인일: " + row["verified_at"])
                    source_fields = [
                        ("메뉴 출처", "menu_source_url", "menu_name"),
                        ("가격 출처", "price_source_url", "price_krw"),
                        ("용량 출처", "volume_source_url", "volume_ml"),
                        ("평점 출처", "rating_source_url", "rating"),
                        ("맛 평가 출처", "taste_source_url", "taste"),
                        ("리뷰 출처", "review_source_url", "review"),
                    ]
                    links = [f"[{label}]({row[url_key]})" for label, url_key, value_key in source_fields if row.get(value_key) and valid_url(row.get(url_key))]
                    if links:
                        st.markdown(" · ".join(links))

with event_tab:
    st.subheader("📣 공식 브랜드 이벤트")
    st.caption("공식 사이트 게시물 제목에 적힌 기간으로 진행중/만료를 표시해요. 정확한 조건은 공식 원문에서 확인하세요.")

    today = datetime.now(KST).date()
    events, error = read_events()

    # 브랜드별 수집 상태
    now_utc = datetime.now(timezone.utc)
    cols = st.columns(len(BRANDS))
    for col, brand in zip(cols, BRANDS):
        times = [t for t in (parse_checked(e.get("checked_at", "")) for e in events if e["brand"] == brand) if t]
        with col:
            if not times:
                st.warning(f"**{brand}**\n\n자동 수집 불가 (공식 사이트가 차단)")
                st.link_button(f"{brand} 이벤트 보러가기", OFFICIAL_PAGES[brand])
            else:
                last = max(times)
                last_kst = last.astimezone(KST).strftime("%m/%d %H:%M")
                if now_utc - last > timedelta(days=STALE_DAYS):
                    st.warning(f"**{brand}**\n\n마지막 확인 {last_kst} — {STALE_DAYS}일 넘게 새로 확인되지 않았어요")
                else:
                    st.success(f"**{brand}**\n\n마지막 확인 {last_kst}")

    if error:
        st.warning(error)
    elif not events:
        st.info("아직 수집된 이벤트가 없습니다. GitHub Actions 실행 결과를 확인해 주세요.")
    else:
        for e in events:
            e["_status"] = event_status(e["title"], today)

        c1, c2 = st.columns([2, 1])
        with c1:
            query = st.text_input("🔍 키워드 검색", placeholder="예: 할인, 쿠폰, 콜라보, 신메뉴", key="ev_query")
        with c2:
            selected = st.multiselect("브랜드", [b for b in BRANDS if any(e["brand"] == b for e in events)],
                                      default=[b for b in BRANDS if any(e["brand"] == b for e in events)], key="ev_brands")
        hide_expired = st.toggle("만료된 이벤트 숨기기", value=False, key="ev_hide")

        q = re.sub(r"\s+", "", query).casefold()
        base = [e for e in events
                if e["brand"] in selected
                and q in re.sub(r"\s+", "", e["title"]).casefold()
                and not (hide_expired and e["_status"][0].startswith("⛔"))]
        # 진행중 → 예정 → 기간 확인 → 만료 순서로 정렬
        order = {"✅": 0, "⏳": 1, "❔": 2, "⛔": 3}
        base.sort(key=lambda e: (order.get(e["_status"][0][0], 9), e["brand"]))

        tab_names = ["전체"] + list(CATEGORIES)
        tabs = st.tabs([f"{name} ({len(base) if name == '전체' else sum(matches(e['title'], CATEGORIES[name]) for e in base)})"
                        for name in tab_names])
        for tab, name in zip(tabs, tab_names):
            with tab:
                items = base if name == "전체" else [e for e in base if matches(e["title"], CATEGORIES[name])]
                show_events(items, today)
