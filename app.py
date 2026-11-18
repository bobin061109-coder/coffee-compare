"""저가커피 메뉴 비교 + 공식 이벤트 표시용 Streamlit 앱.
이 파일로 기존 app.py를 교체할 수 있습니다. core.py에는 의존하지 않습니다.
CSV 출처와 확인 표시가 없는 데이터는 임의로 채우지 않습니다.
"""
import csv
import math
import re
from datetime import date
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
                    rows.append(row)
            return rows, ""
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], f"이벤트 파일을 읽지 못했습니다: {exc}"


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
    st.caption("수집된 공식 게시물로 이동해 행사 기간·대상·참여 조건을 확인하세요.")
    events, event_error = read_events()
    if event_error:
        st.info(event_error)
    elif not events:
        st.info("아직 수집된 이벤트가 없습니다. GitHub Actions에서 이벤트 확인 작업을 실행해 주세요.")
    else:
        event_brands = st.multiselect("이벤트 브랜드", BRANDS, default=BRANDS, key="event_brands")
        events = [event for event in events if event.get("brand") in event_brands]
        events.sort(key=lambda event: event.get("checked_at", ""), reverse=True)
        if not events:
            st.info("선택한 브랜드의 이벤트 자료가 없습니다.")
        else:
            for event in events:
                with st.container(border=True):
                    st.markdown(f"**{event['brand']} · {event['title']}**")
                    if event.get("snippet"):
                        st.write(event["snippet"])
                    if event.get("checked_at"):
                        st.caption("마지막 확인: " + event["checked_at"])
                    st.link_button("공식 게시물 확인", event["url"])
