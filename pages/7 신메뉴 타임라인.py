"""공식 사이트에 신메뉴 사진이 올라온 날짜로 브랜드별 신메뉴 출시 흐름을 보여줍니다."""
import datetime
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from menudata import load_menus, menu_card  # noqa: E402

st.set_page_config(page_title="신메뉴 타임라인", page_icon="🗓️", layout="wide")
KST = datetime.timezone(datetime.timedelta(hours=9))
st.title("🗓️ 신메뉴 타임라인")
st.markdown("브랜드들이 언제 어떤 신메뉴를 냈는지 한눈에 봐요.")

rows = []
for r in load_menus():
    try:
        r["_date"] = datetime.date.fromisoformat(r.get("released_at", ""))
    except ValueError:
        continue
    rows.append(r)
if not rows:
    st.info("아직 출시일 정보가 모이지 않았어요. 매일 아침 자동 수집 때 공식 사이트에서 채워져요.")
    st.stop()

months = st.select_slider("기간", options=[3, 6, 12], value=6, format_func=lambda m: f"최근 {m}개월")
today = datetime.datetime.now(KST).date()
since = (today.replace(day=1) - pd.DateOffset(months=months - 1)).date()

# 같은 음료의 HOT/ICE는 하나로 묶기
groups = {}
for r in rows:
    if r["_date"] < since:
        continue
    k = (r["brand"], r["menu_name"])
    g = groups.setdefault(k, {"row": r, "date": r["_date"], "variants": set()})
    g["variants"].add(r.get("variant", ""))
    g["date"] = min(g["date"], r["_date"])
items = sorted(groups.values(), key=lambda g: (g["date"], g["row"]["brand"]), reverse=True)
if not items:
    st.info("이 기간에는 신메뉴가 없어요.")
    st.stop()

df = pd.DataFrame([{"월": g["date"].strftime("%Y-%m"), "브랜드": g["row"]["brand"]} for g in items])
count = df.groupby(["월", "브랜드"]).size().unstack(fill_value=0).sort_index()
st.subheader("📊 월별 신메뉴 수")
st.bar_chart(count, color=["#A14314", "#5B7FB5"] if list(count.columns) == ["메가MGC커피", "빽다방"] else None)
this_month = df[df["월"] == today.strftime("%Y-%m")]["브랜드"].value_counts()
if not this_month.empty:
    st.caption("이번 달: " + " · ".join(f"{b} {n}개" for b, n in this_month.items()))

st.subheader("🆕 최근 나온 순서")
current = None
cols = None
for i, g in enumerate(items[:60]):
    month = g["date"].strftime("%Y년 %m월")
    if month != current:
        current = month
        st.markdown(f"#### {month}")
        cols = st.columns(4)
        i0 = i
    with cols[(i - i0) % 4]:
        v = "/".join(sorted(x for x in g["variants"] if x and x != "전체"))
        menu_card(st, g["row"], extra=v)

st.caption("출시일은 공식 사이트에 메뉴 사진이 올라온 날짜 기준이에요. 빽다방은 월 단위까지만 알 수 있어요. "
           "컴포즈커피는 공식 정보를 가져올 수 없어 빠져 있어요.")
