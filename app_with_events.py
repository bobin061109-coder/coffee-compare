"""기존 CoffeePick 앱을 그대로 실행한 뒤 공식 브랜드 이벤트 목록을 덧붙이는 진입 파일.
저장소의 app.py는 수정하지 않고, Streamlit 시작 파일을 이 파일로 바꿔 실행합니다.
"""
from pathlib import Path
import csv
import runpy
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent

# 기존 메뉴 비교/추천 앱 전체를 먼저 실행합니다.
# app.py를 별도로 보존하므로 기존 디자인과 기능을 덮어쓰지 않습니다.
runpy.run_path(str(BASE_DIR / "app.py"))


def read_events():
    path = BASE_DIR / "data" / "events.csv"
    if not path.exists():
        return [], "data/events.csv 파일을 찾을 수 없습니다."
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required = {"brand", "title", "url"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                return [], "이벤트 CSV의 열 구성이 맞지 않습니다."
            rows = []
            for raw in reader:
                row = {key: (value or "").strip() for key, value in raw.items()}
                url = row.get("url", "")
                if row.get("brand") and row.get("title") and url.startswith(("https://", "http://")):
                    rows.append(row)
            return rows, ""
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], f"이벤트 자료를 읽지 못했습니다: {exc}"


st.divider()
st.header("📣 저가커피 브랜드 이벤트")
st.caption("공식 페이지에서 확인한 게시물 링크를 보여줍니다. 기간·대상·참여 조건은 원문에서 확인하세요.")
events, error = read_events()
if error:
    st.warning(error)
elif not events:
    st.info("아직 수집된 이벤트가 없습니다. GitHub Actions에서 ‘Refresh official coffee events’를 실행해 주세요.")
else:
    brands = ["전체", "컴포즈커피", "메가MGC커피", "우지커피", "빽다방"]
    selected_brand = st.selectbox("브랜드별 이벤트 보기", brands, key="event_brand_filter")
    if selected_brand != "전체":
        events = [row for row in events if row.get("brand") == selected_brand]
    events.sort(key=lambda row: row.get("checked_at", ""), reverse=True)
    if not events:
        st.info("선택한 브랜드의 수집된 이벤트가 없습니다.")
    else:
        for event in events:
            with st.container(border=True):
                st.subheader(f"{event.get('brand', '브랜드')} · {event.get('title', '공식 이벤트')}")
                if event.get("snippet"):
                    st.write(event["snippet"])
                if event.get("checked_at"):
                    st.caption("마지막 확인: " + event["checked_at"])
                st.link_button("공식 게시물 확인", event["url"])
