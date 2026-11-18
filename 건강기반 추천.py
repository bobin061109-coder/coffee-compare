"""건강기반 추천: 스마트워치 데이터를 자동으로 불러와 음료를 추천합니다. (직접 입력 없음)
흐름: 워치 → 삼성 헬스 → Health Connect → 'Health Data Export' 앱이 구글 시트에 자동 기록 → 이 페이지가 시트를 읽음
(Google Fit API는 2024년 5월부터 신규 신청이 막혀 있어 이 방식을 씁니다.)
불러온 값은 이 화면에서만 쓰고 어디에도 저장하지 않습니다."""
import datetime
import io
import re
import sys
from urllib.parse import urlparse

import requests
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    from core import load_data
except Exception:  # core.py가 없어도 추천 문구는 보여줌
    load_data = None

st.set_page_config(page_title="건강기반 추천", page_icon="☕", layout="wide")
KST = datetime.timezone(datetime.timedelta(hours=9))

st.title("☕ 건강기반 추천")
st.markdown("스마트워치에 쌓인 심박수·수면·걸음 수를 **자동으로 불러와서** 지금 마시기 좋은 음료를 추천해 드려요.")

# ---------------------------------------------------------------
# 1. 동의
# ---------------------------------------------------------------
with st.container(border=True):
    st.markdown(
        "**🔒 건강 정보 이용 안내**  \n"
        "· 목적: 카페인 섭취 가이드와 음료 추천  \n"
        "· 항목: 스마트워치의 심박수, 수면 시간, 걸음 수  \n"
        "· 보관: 이 앱 서버에는 저장하지 않음 (본인 구글 시트에서 그때그때 읽기만 해요)"
    )
    agreed = st.checkbox("위 내용을 확인했고 건강 정보 이용에 동의합니다. (필수)")
if not agreed:
    st.info("👆 동의하시면 입력 화면이 열려요.")
    st.stop()


# ---------------------------------------------------------------
# 2. 파일 읽기 (삼성 헬스 내보내기 CSV 또는 간단한 양식 CSV)
# ---------------------------------------------------------------
def read_any_csv(raw: bytes) -> pd.DataFrame:
    """삼성 헬스 CSV는 첫 줄이 설명 줄이라 건너뛰어야 할 때가 있어요."""
    text = raw.decode("utf-8-sig", errors="ignore")
    best = pd.DataFrame()
    skips = (1, 0) if text.lstrip().startswith("com.samsung") else (0, 1)
    for skip in skips:
        try:
            df = pd.read_csv(io.StringIO(text), skiprows=skip, index_col=False)
        except Exception:
            continue
        df.columns = [str(c).strip() for c in df.columns]
        known = sum(bool(re.search(r"심박|걸음|수면|시간|heart|step|sleep|time|date", c, re.IGNORECASE))
                    for c in df.columns)
        if df.shape[1] >= 2 and (known >= 2 or skip == skips[0] and skips[0] == 1):
            return df
        if best.empty and df.shape[1] >= 2:
            best = df
    return best


def find_col(df, *patterns):
    for p in patterns:
        for c in df.columns:
            if re.search(p, c, re.IGNORECASE):
                return c
    return None


def to_time(series):
    return pd.to_datetime(series, errors="coerce")


def extract(df: pd.DataFrame) -> dict:
    """올린 파일에서 심박수·걸음 수·수면 시간을 찾아냅니다. 못 찾은 값은 None."""
    out = {"heart_rate": None, "steps": None, "sleep_hours": None, "timeline": pd.DataFrame()}
    if df.empty:
        return out
    time_col = find_col(df, r"^시간$|^날짜$|start_time|create_time|day_time|date|time")

    # 간단한 양식: 시간, 심박수, 걸음수, 수면시간
    hr_col = find_col(df, r"심박", r"heart_rate$", r"\.heart_rate$", r"heart.?rate", r"^bpm$")
    if hr_col is not None:
        hr = pd.to_numeric(df[hr_col], errors="coerce")
        valid = df.assign(_hr=hr).dropna(subset=["_hr"])
        valid = valid[(valid["_hr"] > 30) & (valid["_hr"] < 220)]
        if not valid.empty:
            if time_col:
                valid = valid.assign(_t=to_time(valid[time_col])).sort_values("_t")
                tl = valid.dropna(subset=["_t"]).tail(48)
                if not tl.empty:
                    out["timeline"] = pd.DataFrame({"시간": tl["_t"].dt.strftime("%m/%d %H:%M"),
                                                    "심박수 (bpm)": tl["_hr"].round(1)})
            out["heart_rate"] = round(float(valid["_hr"].iloc[-1]), 1)

    step_col = find_col(df, r"걸음", r"step_count", r"^steps?$", r"count$")
    if step_col is not None and (hr_col is None or step_col != hr_col):
        steps = pd.to_numeric(df[step_col], errors="coerce").dropna()
        if not steps.empty:
            if time_col and find_col(df, r"day_time|^날짜$|date"):
                # 날짜별 요약 파일이면 가장 최근 하루 값
                out["steps"] = int(steps.iloc[-1])
            else:
                out["steps"] = int(steps.sum())

    sleep_col = find_col(df, r"수면", r"sleep.*(duration|hour|time|total|min)", r"^sleep$")
    s = pd.to_numeric(df[sleep_col], errors="coerce").dropna() if sleep_col is not None else pd.Series(dtype=float)
    if not s.empty:
        val = float(s.iloc[-1])
        if val > 24:  # 분 단위로 적힌 경우
            val /= 60
        out["sleep_hours"] = round(val, 1)
    else:
        start = find_col(df, r"sleep.*start|^start_time$|com\.samsung\.health\.sleep\.start")
        end = find_col(df, r"sleep.*end|^end_time$|com\.samsung\.health\.sleep\.end")
        if start and end and re.search(r"sleep", " ".join(df.columns), re.IGNORECASE):
            dur = (to_time(df[end]) - to_time(df[start])).dt.total_seconds() / 3600
            dur = dur[(dur > 0) & (dur < 16)]
            if not dur.empty:
                out["sleep_hours"] = round(float(dur.iloc[-1]), 1)
    return out


SHEET_GUIDE = """
**처음 한 번만 설정하면 그다음부터는 자동이에요.**
1. 삼성 헬스 → 설정 → **Health Connect** 연결 켜기 (워치 데이터가 Health Connect로 모여요)
2. 플레이스토어에서 **Health Data Export** 앱 설치 → 심박수·걸음·수면 권한 허용
3. 그 앱에서 **Google Sheets 내보내기**를 켜고 자동 동기화 설정
4. 만들어진 구글 시트 → 공유 → **링크가 있는 모든 사용자: 뷰어**
5. 그 시트 링크를 아래에 붙여넣기 (이 페이지를 즐겨찾기 해두면 다음엔 링크 없이 바로 열려요)
"""


def sheet_id(text: str):
    m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]{20,})", text or "")
    if m:
        return m.group(1)
    return text.strip() if re.fullmatch(r"[A-Za-z0-9_-]{20,}", (text or "").strip()) else None


@st.cache_data(ttl=300, show_spinner=False)
def load_sheet(sid: str):
    """공개된 구글 시트의 모든 탭을 읽습니다. 5분마다 새로 읽어요."""
    url = f"https://docs.google.com/spreadsheets/d/{sid}/export?format=xlsx"
    r = requests.get(url, timeout=20)
    if r.status_code != 200 or not r.content.startswith(b"PK"):
        raise PermissionError("시트를 열 수 없어요. 공유가 '링크가 있는 모든 사용자: 뷰어'인지 확인해 주세요.")
    return pd.read_excel(io.BytesIO(r.content), sheet_name=None)


health = {"heart_rate": None, "steps": None, "sleep_hours": None, "timeline": pd.DataFrame()}
tab_auto, tab_file = st.tabs(["⌚ 워치 자동 연동", "📁 파일로 올리기 (예비)"])

with tab_auto:
    saved = st.query_params.get("sheet", "")
    link = st.text_input("내 건강 데이터 구글 시트 링크", value=saved,
                         placeholder="https://docs.google.com/spreadsheets/d/...")
    with st.expander("처음이라면: 워치 자동 연동 설정 방법", expanded=not saved):
        st.markdown(SHEET_GUIDE)
    sid = sheet_id(link)
    if link and not sid:
        st.error("구글 시트 링크가 아닌 것 같아요.")
    if sid:
        if saved != sid:
            st.query_params["sheet"] = sid  # 즐겨찾기용으로 주소에 기억
        try:
            with st.spinner("워치 데이터를 불러오는 중..."):
                sheets = load_sheet(sid)
            for name, df in sheets.items():
                df.columns = [str(c).strip() for c in df.columns]
                got = extract(df)
                for k in ("heart_rate", "steps", "sleep_hours"):
                    if got[k] is not None:
                        health[k] = got[k]
                if not got["timeline"].empty:
                    health["timeline"] = got["timeline"]
            st.caption(f"📡 시트 탭 {len(sheets)}개에서 불러옴 · 5분마다 새로 읽어요")
            if st.button("🔄 지금 다시 불러오기"):
                load_sheet.clear()
                st.rerun()
        except PermissionError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"시트를 읽는 중 문제가 생겼어요: {exc}")

with tab_file:
    st.caption("자동 연동 설정 전에 써볼 수 있어요. 삼성 헬스 → 설정 → **개인 데이터 다운로드**로 받은 "
               "심박수(heart_rate)·걸음(step)·수면(sleep) CSV를 올려주세요. 여러 개를 한 번에 올려도 돼요.")
    files = st.file_uploader("CSV 파일", type=["csv"], accept_multiple_files=True)
    for f in files or []:
        got = extract(read_any_csv(f.getvalue()))
        for k in ("heart_rate", "steps", "sleep_hours"):
            if got[k] is not None:
                health[k] = got[k]
        if not got["timeline"].empty:
            health["timeline"] = got["timeline"]

if all(health[k] is None for k in ("heart_rate", "steps", "sleep_hours")):
    st.info("워치 데이터가 연결되면 여기에 추천이 나타나요.")
    st.stop()


# ---------------------------------------------------------------
# 4. 추천 로직 (원래 로직 유지)
# ---------------------------------------------------------------
def analyze(h: dict) -> dict:
    now_hour = datetime.datetime.now(KST).hour
    hr, sleep, steps = h["heart_rate"], h["sleep_hours"], h["steps"] or 0
    if now_hour >= 18 or (sleep is not None and sleep < 6.0 and now_hour >= 15):
        return {"status": "warning", "kind": "decaf_tea",
                "menu": "디카페인 커피 / 허브티",
                "reason": "수면이 부족하거나 늦은 시간이에요. 지금 카페인을 마시면 오늘 밤 잠을 방해할 수 있어요.",
                "limit": "0 mg (카페인 쉬어가기)"}
    if hr is not None and hr >= 85:
        return {"status": "error", "kind": "decaf",
                "menu": "디카페인 커피",
                "reason": f"지금 심박수가 {hr} bpm으로 조금 높아요. 카페인을 더하면 가슴 두근거림이 심해질 수 있어요.",
                "limit": "최대 50 mg 이하"}
    if steps >= 7000:
        return {"status": "success", "kind": "latte",
                "menu": "카페라떼 / 바닐라라떼",
                "reason": f"오늘 {steps:,}보나 걸으셨네요! 우유와 약간의 당분이 있는 라떼가 잘 어울려요.",
                "limit": "150 ~ 200 mg"}
    return {"status": "info", "kind": "americano",
            "menu": "아메리카노",
            "reason": "컨디션이 안정적이에요. 깔끔한 아메리카노로 집중력을 챙겨보세요.",
            "limit": "100 ~ 150 mg"}


KIND_KEYWORDS = {
    "decaf_tea": r"디카페인|캐모마일|루이보스|페퍼민트|민트티|유자|레몬티|자몽티|매실",
    "decaf": r"디카페인",
    "latte": r"^카페라떼$|^바닐라라떼$|^바닐라 라떼$",
    "americano": r"^아메리카노$",
}

rec = analyze(health)

st.divider()
m1, m2, m3, m4 = st.columns(4)
m1.metric("심박수", f"{health['heart_rate']} bpm" if health["heart_rate"] is not None else "기록 없음")
m2.metric("수면 시간", f"{health['sleep_hours']} 시간" if health["sleep_hours"] is not None else "기록 없음")
m3.metric("걸음 수", f"{int(health['steps']):,} 보" if health["steps"] is not None else "기록 없음")
m4.metric("권장 카페인", rec["limit"])

st.subheader("🎯 지금 추천 메뉴")
box = {"warning": st.warning, "error": st.error, "success": st.success}.get(rec["status"], st.info)
box(f"**{rec['menu']}**\n\n{rec['reason']}")

# 실제 판매 메뉴에서 골라 보여주기
if load_data is not None:
    rows, _ = load_data(ROOT / "data" / "menus.csv")
    pat = re.compile(KIND_KEYWORDS[rec["kind"]])
    picks = [r for r in rows if pat.search(str(r["menu_name"]))]
    if picks:
        st.markdown("**이 브랜드들에서 고르면?**")
        seen, shown = set(), []
        for r in picks:
            key = (r["brand"], r["menu_name"])
            if key in seen:
                continue
            seen.add(key)
            shown.append(r)
        cols = st.columns(3)
        for i, r in enumerate(shown[:9]):
            price = f"{int(r['price_krw']):,}원" if r.get("price_krw") else "가격 확인 자료 없음"
            cols[i % 3].markdown(f"☕ **{r['brand']}** · {r['menu_name']}  \n<small>{price}</small>",
                                 unsafe_allow_html=True)

if not health["timeline"].empty:
    st.subheader("📊 심박수 추이")
    st.line_chart(health["timeline"].set_index("시간"))

st.caption("※ 참고용 추천이에요. 의학적 판단이 아니며, 몸에 이상이 느껴지면 전문가와 상담하세요.")
