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
from menudata import load_menus, menu_card  # noqa: E402

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


def heart_col(df):
    """심박수 열 고르기: 심박변이도(HRV)는 빼고, 평균(avg) 열을 먼저, 없으면 안정시 심박수."""
    cols = [c for c in df.columns
            if re.search(r"심박|heart.?rate|^bpm$", c, re.IGNORECASE)
            and not re.search(r"variab|변이|hrv", c, re.IGNORECASE)]
    if not cols:
        return None

    def rank(c):
        low = c.casefold()
        resting = bool(re.search(r"rest|안정", low))
        avg = bool(re.search(r"avg|average|mean|평균", low))
        minmax = bool(re.search(r"\bmin|\bmax|최소|최대", low))
        return (resting, not avg, minmax)
    return sorted(cols, key=rank)[0]


def to_time(series):
    return pd.to_datetime(series, errors="coerce")


def extract(df: pd.DataFrame) -> dict:
    """올린 파일에서 심박수·걸음 수·수면 시간을 찾아냅니다. 못 찾은 값은 None."""
    out = {"heart_rate": None, "steps": None, "sleep_hours": None, "resting_hr": None, "timeline": pd.DataFrame()}
    if df.empty:
        return out
    time_col = find_col(df, r"^시간$|^날짜$|start_time|create_time|day_time|date|time")

    # 간단한 양식: 시간, 심박수, 걸음수, 수면시간
    hr_col = heart_col(df)
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

    rest_cols = [c for c in df.columns if re.search(r"rest|안정", c, re.IGNORECASE)
                 and re.search(r"heart|심박", c, re.IGNORECASE)]
    rest_cols.sort(key=lambda c: not re.search(r"avg|평균", c, re.IGNORECASE))
    if rest_cols:
        rv = pd.to_numeric(df[rest_cols[0]], errors="coerce").dropna()
        rv = rv[(rv > 30) & (rv < 150)]
        if not rv.empty:
            out["resting_hr"] = round(float(rv.iloc[-1]), 1)

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


health = {"heart_rate": None, "steps": None, "sleep_hours": None, "resting_hr": None, "timeline": pd.DataFrame()}
tab_auto, tab_file, tab_demo = st.tabs(["⌚ 워치 자동 연동", "📁 파일로 올리기 (예비)", "🎬 예시로 체험 (발표용)"])

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
                for k in ("heart_rate", "steps", "sleep_hours", "resting_hr"):
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
        for k in ("heart_rate", "steps", "sleep_hours", "resting_hr"):
            if got[k] is not None:
                health[k] = got[k]
        if not got["timeline"].empty:
            health["timeline"] = got["timeline"]

DEMOS = {  # 이름: (심박수, 수면시간, 걸음수, 시각)
    "😵 밤샘 다음 날 아침": (74, 3.5, 1500, 9),
    "🥱 조금 못 잔 오후": (72, 5.5, 4000, 15),
    "😴 푹 잔 날": (66, 8.0, 5000, 10),
    "💓 심박수가 높은 날": (102, 6.5, 4000, 11),
    "🏃 만 보 넘게 걸은 날": (80, 6.5, 12000, 17),
    "🌙 밤 10시 야식 타임": (70, 6.0, 7000, 22),
}
demo_hour = None
with tab_demo:
    st.caption("실제 워치 데이터 없이, 상황별로 추천이 어떻게 바뀌는지 보여줘요.")
    pick = st.radio("상황 고르기", ["사용 안 함"] + list(DEMOS), key="demo")
    if pick != "사용 안 함":
        hr_d, sleep_d, steps_d, demo_hour = DEMOS[pick]
        health = {"heart_rate": hr_d, "sleep_hours": sleep_d, "steps": steps_d, "resting_hr": 65,
                  "timeline": pd.DataFrame()}

if demo_hour is not None:
    st.warning(f"🎬 **예시 데이터로 보는 중이에요** ({pick}, {demo_hour}시 기준). 실제 워치 데이터가 아니에요.")

if all(health[k] is None for k in ("heart_rate", "steps", "sleep_hours")):
    st.info("워치 데이터가 연결되면 여기에 추천이 나타나요. 먼저 둘러보려면 '🎬 예시로 체험' 탭을 눌러보세요.")
    st.stop()
if demo_hour is None and health["heart_rate"] is None:
    st.caption("💓 심박수는 지금 연동 앱(Health Data Export)이 시트로 내보내지 못해서, 걸음 수·수면·시간대로 추천해요.")


# ---------------------------------------------------------------
# 4. 추천 로직: 수면·시간·심박수·걸음 수로 '이번 한 잔'의 카페인 범위를 정함
# ---------------------------------------------------------------
SINGLE_MAX = 200   # 한 번에 마실 카페인 상한 (EFSA: 성인 1회 200mg까지 안전)
SLEEP_OK = 50      # 잘 때 몸에 남아도 괜찮은 정도 (참고 기준)
HALF_LIFE = 5.0    # 카페인 반감기, 성인 평균 약 5시간 (사람마다 3~7시간)

with st.expander("⚙️ 잘 시간 설정 (기본 밤 12시)"):
    bed_hour = st.slider("보통 몇 시에 자요?", 21, 27, 24, format="%d시",
                         help="25시 = 새벽 1시") 


def plan(h, hour):
    """요인별로 카페인 상한을 줄여가며 최종 범위를 정합니다. (요인 설명 목록, 최소, 최대, 열량 상한, 선호 종류)"""
    factors, cap, floor, kcal_cap, prefer = [], SINGLE_MAX, 0, None, None
    sleep, hr, rest, steps = h["sleep_hours"], h["heart_rate"], h.get("resting_hr"), h["steps"]

    # 1) 수면: 충분히 잤으면 카페인이 필요 없어요
    if sleep is None:
        factors.append(("😶", "수면", "기록 없음", "수면 기록이 없어서 수면은 빼고 계산했어요."))
    elif sleep >= 7:
        cap = min(cap, 15)
        factors.append(("😴", "수면", f"{sleep:g}시간 · 충분", "푹 잤으니 카페인 없이도 괜찮은 날이에요. 맛있는 논카페인 음료를 추천해요."))
    elif sleep >= 6:
        cap = min(cap, 120)
        factors.append(("🙂", "수면", f"{sleep:g}시간 · 조금 부족", "가볍게 한 잔(120mg 이하)이면 충분해요."))
    elif sleep >= 5:
        cap, floor = min(cap, 180), 60
        factors.append(("🥱", "수면", f"{sleep:g}시간 · 부족", "적당한 카페인(60~180mg)이 집중에 도움이 돼요."))
    else:
        cap, floor = min(cap, SINGLE_MAX), 100
        factors.append(("😵", "수면", f"{sleep:g}시간 · 많이 부족", "카페인이 도움은 되지만 한 번에 200mg은 넘기지 마세요. 20분 낮잠이 더 효과적일 수 있어요."))

    # 2) 잘 시간까지 남은 시간: 잘 때 50mg 아래로 빠질 만큼만
    left = bed_hour - hour
    if left <= 4:
        cap = min(cap, 15)
        factors.append(("🌙", "시간", f"잘 시간까지 {max(left, 0)}시간", "곧 잘 시간이라 카페인은 쉬어가요."))
    else:
        by_time = int(SLEEP_OK * 2 ** (left / HALF_LIFE))
        if by_time < cap:
            cap = by_time
            factors.append(("⏰", "시간", f"잘 시간까지 {left}시간", f"지금 {by_time}mg 넘게 마시면 잘 때까지 다 안 빠져요."))
        else:
            factors.append(("⏰", "시간", f"잘 시간까지 {left}시간", "아직 여유 있는 시간이에요."))

    # 3) 심박수: 이미 빠르면 카페인을 줄여요
    if hr is None:
        factors.append(("💓", "심박수", "기록 없음", "심박수 기록이 없어서 심박수는 빼고 계산했어요."))
    elif hr >= 100:
        cap = min(cap, 15)
        factors.append(("💓", "심박수", f"{hr:g} bpm · 빠름", "심장이 이미 빨리 뛰고 있어요. 카페인은 두근거림을 더 키울 수 있어요."))
    elif hr >= 90:
        cap = min(cap, 50)
        factors.append(("💓", "심박수", f"{hr:g} bpm · 조금 빠름", "카페인을 50mg 이하로 줄였어요."))
    elif rest is not None and hr - rest >= 20:
        cap = int(cap * 0.5)
        factors.append(("💓", "심박수", f"{hr:g} bpm (평소 {rest:g})", "평소보다 20 넘게 높아서 카페인을 절반으로 줄였어요."))
    else:
        factors.append(("💓", "심박수", f"{hr:g} bpm · 안정", "안정적이에요."))

    # 4) 걸음 수: 많이 걸었으면 수분, 적게 걸었으면 가벼운 음료
    if steps is None:
        factors.append(("👟", "걸음 수", "기록 없음", "걸음 기록이 없어요."))
    elif steps >= 10000:
        prefer, kcal_cap = "drink", 400
        factors.append(("🏃", "걸음 수", f"{steps:,}보 · 아주 많음", "땀을 많이 흘렸을 수 있어요. 수분 보충되는 에이드·주스·티를 먼저 보여줘요."))
    elif steps >= 6000:
        kcal_cap = 350
        factors.append(("🚶", "걸음 수", f"{steps:,}보 · 활발", "충분히 움직였어요. 달달한 라떼도 괜찮아요."))
    elif steps < 3000 and hour >= 14:
        kcal_cap = 200
        factors.append(("🛋️", "걸음 수", f"{steps:,}보 · 적음", "오늘 활동량이 적어서 200kcal 이하 가벼운 음료를 골랐어요. 산책 10분도 좋아요!"))
    else:
        kcal_cap = 300
        factors.append(("🚶", "걸음 수", f"{steps:,}보 · 보통", "평범한 활동량이에요."))

    if cap <= 15:
        floor = 0
    floor = min(floor, cap)
    return factors, floor, cap, kcal_cap, prefer


hour = datetime.datetime.now(KST).hour if demo_hour is None else demo_hour
if hour < 5:
    hour += 24  # 새벽은 '전날 밤'으로 계산
factors, lo, hi, kcal_cap, prefer = plan(health, hour)

st.divider()
st.subheader("🧠 오늘 내 몸 상태로 계산했어요")
cols = st.columns(len(factors))
for col, (emoji, name, value, why) in zip(cols, factors):
    with col:
        with st.container(border=True):
            st.markdown(f"**{emoji} {name}**  \n{value}")
            st.caption(why)

if hi <= 15:
    st.success("### 오늘은 **카페인 없는 음료** 추천! ☕❌\n디카페인·차·에이드·주스 중에서 골라봤어요.")
elif lo > 0:
    st.warning(f"### 이번 한 잔은 카페인 **{lo}~{hi}mg**\n졸음을 깨울 만큼만, 잘 때 방해되지 않을 만큼만 골랐어요.")
else:
    st.info(f"### 이번 한 잔은 카페인 **{hi}mg 이하**\n이 안에서 마시면 오늘 밤 잠에 큰 영향이 없어요.")

# 실제 판매 음료에서 고르기 (공식 카페인 표기가 있는 메뉴만)
GROUPS = {
    "☕ 커피": r"아메리카노|리카노|에스프레소|콜드브루|커피|샷",
    "🥛 라떼·달달": r"라떼|모카|마끼아또|마키아또|카푸치노|빽스치노|프라페|쉐이크|스무디|초코|밀크티",
    "🍹 에이드·주스·티": r"에이드|주스|아이스티|티$|차$|소다|유자|레몬|자몽|캐모마일|루이보스|민트",
}
rows = [r for r in load_menus() if r["caffeine"] is not None and lo <= r["caffeine"] <= hi
        and not re.search(r"빽사이즈|왕메가|메가리카노|ARIH", r["menu_name"])
        and (kcal_cap is None or r["kcal_n"] is None or r["kcal_n"] <= kcal_cap)]
temp = st.radio("온도", ["상관없음", "HOT", "ICE"], horizontal=True, key="temp")
if temp != "상관없음":
    rows = [r for r in rows if r.get("variant") in (temp, "전체")]
target = (lo + hi) / 2 if lo > 0 else (hi * 0.7 if hi > 15 else 0)  # 범위 안에서 너무 약하지도 세지도 않게
best = {}
for r in sorted(rows, key=lambda r: (abs(r["caffeine"] - target), r["kcal_n"] or 0)):
    best.setdefault((r["brand"], r["menu_name"]), r)
picks = list(best.values())
order = list(GROUPS)
if prefer == "drink":
    order = ["🍹 에이드·주스·티", "🥛 라떼·달달", "☕ 커피"]
if hi <= 15:
    order = ["🍹 에이드·주스·티", "🥛 라떼·달달", "☕ 커피"]
if not picks:
    st.info("조건에 맞는 음료를 찾지 못했어요. 온도를 '상관없음'으로 바꿔보세요.")
else:
    st.markdown("**🎯 조건에 맞는 음료** (카페인·열량은 공식 사이트 표기 기준)")
    tabs = st.tabs(order)
    for tab, g in zip(tabs, order):
        with tab:
            pool = [r for r in picks if re.search(GROUPS[g], r["menu_name"])]
            if not pool:
                st.caption("이 종류에서는 조건에 맞는 음료가 없어요.")
                continue
            c = st.columns(4)
            for k, r in enumerate(pool[:8]):
                with c[k % 4]:
                    menu_card(st, r, extra=f"{r['kcal_n']:g}kcal" if r["kcal_n"] is not None else "")
            if len(pool) > 8:
                with st.expander(f"더 보기 ({len(pool) - 8}개)"):
                    st.write(" · ".join(f"{r['brand']} {r['menu_name']} ({r['caffeine']:g}mg)" for r in pool[8:]))
    st.caption("컴포즈커피는 공식 카페인 정보가 없어 빠져 있어요. 하루 카페인은 성인 400mg 이하가 권고량이에요.")

if not health["timeline"].empty:
    st.subheader("📊 심박수 추이")
    st.line_chart(health["timeline"].set_index("시간"))

st.caption("※ 참고용 추천이에요. 의학적 판단이 아니며, 몸에 이상이 느껴지면 전문가와 상담하세요.")
