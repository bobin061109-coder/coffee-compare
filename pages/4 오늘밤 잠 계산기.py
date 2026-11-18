"""오늘 마신 음료로 몸속 카페인이 언제 빠지는지 계산해서 잠들기 좋은 시각을 알려줍니다."""
import datetime
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from menudata import label, load_menus, menu_card  # noqa: E402

st.set_page_config(page_title="오늘 밤 잠 계산기", page_icon="🌙", layout="wide")
KST = datetime.timezone(datetime.timedelta(hours=9))
HALF_LIFE_H = 5.0      # 카페인 반감기(성인 평균, 사람마다 3~7시간)
SLEEP_OK_MG = 50.0     # 이 아래로 내려가면 잠들기 편하다고 봄(참고 기준)
DAILY_LIMIT = 400      # 식약처 성인 하루 최대 권고량

st.title("🌙 오늘 밤 잠 계산기")
st.markdown("오늘 마신 음료를 고르면, 카페인이 몸에서 빠지는 걸 계산해서 **몇 시쯤 잠들기 편한지** 알려줘요.")

menus = [r for r in load_menus() if r["caffeine"] is not None]
if not menus:
    st.info("아직 카페인 정보가 모이지 않았어요. 매일 아침 자동 수집 때 공식 사이트에서 채워져요.")
    st.stop()
st.caption(f"공식 사이트에 카페인이 표시된 음료 {len(menus)}개 · 컴포즈커피는 공식 정보가 없어 빠져 있어요.")

options = {f"{r['brand']} · {label(r)} · {r['caffeine']:g}mg": r for r in menus}
picked = st.multiselect("☕ 오늘 마신 음료", list(options), placeholder="음료 이름으로 검색")
now = datetime.datetime.now(KST).replace(second=0, microsecond=0)

drinks = []
if picked:
    st.markdown("**언제 마셨어요?**")
    cols = st.columns(min(len(picked), 3))
    for i, name in enumerate(picked):
        with cols[i % 3]:
            t = st.time_input(name.split(" · ")[1], value=(now - datetime.timedelta(hours=1)).time(),
                              key=f"t{i}", step=900)
            drinks.append((options[name], t))
bed = st.time_input("🛏️ 오늘 잘 시간", value=datetime.time(23, 30), step=900)

if not drinks:
    st.info("음료를 하나 이상 고르면 계산해요.")
    st.stop()


def at_today(t):
    dt = datetime.datetime.combine(now.date(), t, tzinfo=KST)
    return dt - datetime.timedelta(days=1) if dt > now + datetime.timedelta(hours=1) else dt


intakes = [(at_today(t), r["caffeine"]) for r, t in drinks]
start = min(d for d, _ in intakes)
bed_dt = datetime.datetime.combine(now.date(), bed, tzinfo=KST)
if bed_dt < now - datetime.timedelta(hours=6):
    bed_dt += datetime.timedelta(days=1)
end = max(bed_dt, now) + datetime.timedelta(hours=6)


def level(at):
    total = 0.0
    for d, mg in intakes:
        if at >= d:
            total += mg * 0.5 ** ((at - d).total_seconds() / 3600 / HALF_LIFE_H)
    return total


times = pd.date_range(start, end, freq="15min")
curve = pd.DataFrame({"시각": times, "몸속 카페인 (mg)": [round(level(t.to_pydatetime()), 1) for t in times]})
ok_time = next((t for t, v in zip(times, curve["몸속 카페인 (mg)"]) if t > now and v < SLEEP_OK_MG), None)
total = sum(mg for _, mg in intakes)
at_bed = level(bed_dt)

c1, c2, c3 = st.columns(3)
c1.metric("오늘 마신 카페인", f"{total:g} mg", f"하루 권고량 {DAILY_LIMIT}mg 중 {total / DAILY_LIMIT:.0%}",
          delta_color="off")
c2.metric("지금 몸속에 남은 양", f"{level(now):.0f} mg")
c3.metric("잘 시간에 남는 양", f"{at_bed:.0f} mg")

if at_bed < SLEEP_OK_MG:
    st.success(f"😴 **{bed.strftime('%H:%M')}에 자도 괜찮아요!** 그때쯤이면 카페인이 {at_bed:.0f}mg까지 줄어들어요.")
else:
    when = ok_time.strftime("%m/%d %H:%M") if ok_time is not None else "내일"
    st.warning(f"☕ **{bed.strftime('%H:%M')}에는 아직 {at_bed:.0f}mg이 남아 있어요.** "
               f"**{when}** 이후에 잠들기 편해질 거예요.")
if total > DAILY_LIMIT:
    st.error(f"오늘 카페인이 하루 권고량({DAILY_LIMIT}mg)을 넘었어요. 남은 하루는 디카페인이나 차를 추천해요.")

st.line_chart(curve.set_index("시각"))
st.caption(f"계산 기준: 카페인 반감기 {HALF_LIFE_H:g}시간, 몸속 {SLEEP_OK_MG:g}mg 아래면 잠들기 편하다고 봤어요. "
           "사람마다 반감기가 3~7시간으로 달라서 참고용이에요. 의학적 판단이 아니에요.")

st.subheader("마신 음료")
cols = st.columns(4)
for i, (r, t) in enumerate(drinks):
    with cols[i % 4]:
        menu_card(st, r, extra=t.strftime("%H:%M"))
