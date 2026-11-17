"""공식 브랜드 이벤트 게시물 목록."""
from pathlib import Path
import csv
import re
from urllib.parse import urlparse
import streamlit as st

st.set_page_config(page_title="브랜드 이벤트", page_icon="📣", layout="wide")
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "events.csv"
BRANDS = ["컴포즈커피", "메가MGC커피", "빽다방"]


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
                    rows.append(row)
            return rows, ""
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], f"이벤트 자료를 읽지 못했습니다: {exc}"


st.title("📣 저가커피 브랜드 이벤트")
st.caption("공식 사이트 게시물입니다. 진행 여부와 기간·참여 조건은 공식 원문에서 확인하세요.")
st.info("수집 대상: 컴포즈커피 · 메가MGC커피 · 빽다방 (우지커피 제외)")
events, error = read_events()
if error:
    st.warning(error)
elif not events:
    st.info("아직 수집된 이벤트가 없습니다. GitHub Actions 실행 결과를 확인해 주세요.")
else:
    selected = st.multiselect("브랜드", BRANDS, default=BRANDS)
    query = st.text_input("제목 검색", placeholder="예: 할인, 쿠폰, 신메뉴")
    q = re.sub(r"\s+", "", query).casefold()
    visible = [e for e in events if e["brand"] in selected and q in re.sub(r"\s+", "", e["title"]).casefold()]
    visible.sort(key=lambda e: e.get("checked_at", ""), reverse=True)
    if not visible:
        st.info("조건에 맞는 게시물이 없습니다.")
    for event in visible:
        with st.container(border=True):
            st.subheader(f"{event['brand']} · {event['title']}")
            if event.get("snippet"):
                st.write(event["snippet"])
            if event.get("checked_at"):
                st.caption("마지막 확인: " + event["checked_at"])
            st.link_button("공식 게시물 열기", event["url"])
