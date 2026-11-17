"""Streamlit 이벤트 화면. 기존 앱/추천 기능은 수정하지 않고 유지합니다."""
from pathlib import Path
import csv
import re
from urllib.parse import urlparse

import streamlit as st

st.set_page_config(page_title="브랜드 이벤트", page_icon="📣", layout="wide")
BASE_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = BASE_DIR / "data" / "events.csv"
BRANDS = ["컴포즈커피", "메가MGC커피", "빽다방"]


def safe_http_url(value):
    try:
        parsed = urlparse(value or "")
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def read_events():
    if not CSV_PATH.exists():
        return [], "이벤트 데이터 파일이 아직 없습니다."
    try:
        with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            needed = {"brand", "title", "url"}
            if not reader.fieldnames or not needed.issubset(reader.fieldnames):
                return [], "이벤트 CSV 형식이 맞지 않습니다."
            rows = []
            for raw in reader:
                row = {key: (value or "").strip() for key, value in raw.items()}
                if row.get("brand") in BRANDS and row.get("title") and safe_http_url(row.get("url")):
                    rows.append(row)
            return rows, ""
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], f"이벤트 정보를 읽지 못했습니다: {exc}"


st.title("📣 저가커피 브랜드 이벤트")
st.caption("공식 사이트 게시물을 모아 보여줍니다. 진행 중인지와 기간·참여 조건은 각 공식 원문에서 확인하세요.")
st.info("수집 대상은 컴포즈커피, 메가MGC커피, 빽다방입니다. 우지커피는 제외했습니다.")
events, error = read_events()
if error:
    st.warning(error)
elif not events:
    st.info("아직 수집된 게시물이 없습니다. GitHub Actions 실행 기록을 확인해 주세요.")
else:
    selected = st.multiselect("브랜드 선택", BRANDS, default=BRANDS)
    query = st.text_input("이벤트 제목 검색", placeholder="예: 할인, 쿠폰, 신메뉴")
    q = re.sub(r"\\s+", "", query).casefold()
    visible = [e for e in events if e["brand"] in selected and q in re.sub(r"\\s+", "", e["title"]).casefold()]
    visible.sort(key=lambda e: e.get("checked_at", ""), reverse=True)
    if not visible:
        st.info("조건에 맞는 이벤트 게시물이 없습니다.")
    else:
        st.caption(f"{len(visible)}개 게시물")
        for event in visible:
            with st.container(border=True):
                st.subheader(f"{event['brand']} · {event['title']}")
                if event.get("snippet"):
                    st.write(event["snippet"])
                if event.get("checked_at"):
                    st.caption("마지막 확인: " + event["checked_at"])
                st.link_button("공식 게시물 열기", event["url"])
