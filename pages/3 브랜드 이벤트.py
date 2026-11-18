"""공식 브랜드 이벤트 게시물 목록."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import csv
import re
from urllib.parse import urlparse
import streamlit as st

st.set_page_config(page_title="브랜드 이벤트", page_icon="📣", layout="wide")
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "events.csv"
BRANDS = ["컴포즈커피", "메가MGC커피", "빽다방"]
OFFICIAL_PAGES = {
    "컴포즈커피": "https://composecoffee.com/event",
    "메가MGC커피": "https://www.mega-mgccoffee.com/bbs/?bbs_category=3",
    "빽다방": "https://paikdabang.com/news/?cate=event",
}
KST = timezone(timedelta(hours=9))
STALE_DAYS = 2  # 이 기간 넘게 새로 확인이 안 되면 경고

# 칸(탭)별 키워드. 제목에 하나라도 들어 있으면 그 칸에 표시합니다.
CATEGORIES = {
    "💸 할인": [r"할인", r"반값", r"\d+\s*%", r"\d[\d,]*\s*원에", r"1천원", r"프로모션", r"특가", r"\d[\d,]*원\s*프로모션"],
    "🎟️ 쿠폰·적립": [r"쿠폰", r"적립", r"프리퀀시", r"증정", r"경품", r"스탬프", r"리워드"],
    "🤝 콜라보": [r"콜라보", r"[가-힣A-Za-z0-9\]]\s*[xX×]\s*[가-힣A-Za-z\[]", r"\[[^\]]*\|[^\]]*\]"],
    "🆕 신메뉴": [r"신메뉴", r"출시", r"신제품", r"NEW", r"시즌\s*메뉴", r"한정\s*메뉴"],
}


def read_events():
    if not CSV_PATH.exists():
        return [], "이벤트 데이터 파일이 없습니다."
    try:
        with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or not {"brand", "title", "url"}.issubset(reader.fieldnames):
                return [], "이벤트 CSV 열 구성이 맞지 않습니다."
            rows = []
            for raw in reader:
                row = {k: (v or "").strip() for k, v in raw.items()}
                try:
                    parsed = urlparse(row.get("url", ""))
                    valid_url = parsed.scheme in ("https", "http") and bool(parsed.netloc)
                except ValueError:
                    valid_url = False
                if row.get("brand") in BRANDS and row.get("title") and valid_url:
                    # 메가커피 제목 끝에 붙는 브랜드명 중복 제거
                    row["title"] = re.sub(r"\s*메가MGC커피$", "", row["title"])
                    rows.append(row)
            return rows, ""
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], f"이벤트 자료를 읽지 못했습니다: {exc}"


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
    return "✅ 진행중 (종료일 미표기)", "green"


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


st.title("📣 저가커피 브랜드 이벤트")
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
        query = st.text_input("🔍 키워드 검색", placeholder="예: 할인, 쿠폰, 콜라보, 신메뉴")
    with c2:
        selected = st.multiselect("브랜드", [b for b in BRANDS if any(e["brand"] == b for e in events)],
                                  default=[b for b in BRANDS if any(e["brand"] == b for e in events)])
    hide_expired = st.toggle("만료된 이벤트 숨기기", value=False)

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
