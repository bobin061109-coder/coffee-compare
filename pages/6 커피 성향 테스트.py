"""질문 5개로 나와 맞는 커피 브랜드와 대표 메뉴를 알려주는 재미용 테스트."""
import random
import re
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from menudata import BRAND_COLORS, load_menus, menu_card  # noqa: E402

st.set_page_config(page_title="커피 성향 테스트", page_icon="🧪", layout="wide")
st.title("🧪 나는 어떤 커피 인간일까?")
st.markdown("질문 5개에 답하면 나랑 찰떡인 브랜드와 대표 메뉴를 알려줘요. (재미로 보는 테스트예요!)")

# 각 답이 브랜드에 주는 점수: (컴포즈, 메가, 빽다방)
QUESTIONS = [
    ("☀️ 아침에 카페에 들르면 나는?", [
        ("늘 마시던 걸로 빠르게, 가격도 착하게", (2, 0, 1)),
        ("하루 버티려면 무조건 큰 사이즈", (0, 3, 1)),
        ("오늘 기분 따라 새로운 걸 골라본다", (1, 1, 2)),
    ]),
    ("🍫 단맛에 대한 내 생각은?", [
        ("깔끔한 게 최고, 단 건 별로", (2, 1, 0)),
        ("적당히 달달한 라떼 정도", (1, 2, 1)),
        ("달수록 행복하다, 크림·토핑 환영", (0, 1, 3)),
    ]),
    ("🆕 신메뉴가 나오면?", [
        ("남들이 먹어보고 괜찮다 하면 그때", (2, 1, 0)),
        ("콜라보·굿즈 나오면 바로 달려감", (0, 3, 1)),
        ("특이한 조합일수록 궁금해서 먼저 먹어봄", (0, 1, 3)),
    ]),
    ("💸 커피값에 대한 나의 철학", [
        ("커피는 매일 마시니까 가성비가 생명", (3, 1, 1)),
        ("양 대비 가격이면 충분히 납득", (1, 3, 0)),
        ("맛있으면 조금 비싸도 OK", (0, 1, 2)),
    ]),
    ("🧊 내가 제일 자주 마시는 건?", [
        ("아메리카노", (2, 2, 1)),
        ("라떼·바닐라라떼", (2, 1, 1)),
        ("빽스치노·프라페 같은 블렌딩 음료", (0, 1, 3)),
    ]),
]

RESULTS = {
    "컴포즈커피": ("🎯 실속파 데일리 러버",
              "매일 마셔도 부담 없는 가격과 기본기를 중요하게 생각하는 타입이에요. 유행보다 '늘 맛있는 그 맛'을 믿어요.",
              r"^아메리카노$|^카페라떼$|^바닐라라떼$|^바닐라 라떼$"),
    "메가MGC커피": ("🔥 대용량 트렌드 헌터",
               "넉넉한 양과 신상·콜라보에 진심인 타입이에요. 굿즈 출시 소식엔 누구보다 빠르게 반응해요.",
               r"메가리카노|할메가|왕메가|퐁크러쉬|프라페"),
    "빽다방": ("🍦 달콤 실험가",
            "달콤하고 개성 있는 블렌딩 음료를 사랑하는 타입이에요. 처음 보는 조합에 먼저 손이 가요.",
            r"빽스치노|원조커피|쉐이크|아샷추|아이스티샷"),
}

answers = []
for qi, (q, opts) in enumerate(QUESTIONS):
    choice = st.radio(q, [o for o, _ in opts], index=None, key=f"q{qi}")
    answers.append(next((s for o, s in opts if o == choice), None))

if None in answers:
    st.info(f"👆 {sum(a is None for a in answers)}개 질문이 남았어요.")
    st.stop()

scores = [sum(a[i] for a in answers) for i in range(3)]
brands = ["컴포즈커피", "메가MGC커피", "빽다방"]
best = brands[max(range(3), key=lambda i: (scores[i], -i))]
title, desc, pat = RESULTS[best]
color = BRAND_COLORS[best]
total = sum(scores)

st.divider()
st.markdown(
    f"<div style='background:#FFF8EF;border-left:8px solid {color};border-radius:16px;padding:20px 24px'>"
    f"<div style='color:{color};font-weight:800;font-size:1.1rem'>당신은…</div>"
    f"<div style='color:#3E2723;font-weight:900;font-size:2rem;margin:6px 0'>{best}형 인간</div>"
    f"<div style='color:#3E2723;font-weight:800;font-size:1.2rem'>{title}</div>"
    f"<div style='color:#4E3626;margin-top:8px'>{desc}</div></div>",
    unsafe_allow_html=True,
)
st.markdown("**나의 브랜드 궁합**")
for b, s in sorted(zip(brands, scores), key=lambda x: -x[1]):
    st.progress(s / total, text=f"{b} {s / total:.0%}")

picks = [r for r in load_menus() if r["brand"] == best and re.search(pat, r["menu_name"])
         and "디카페인" not in r["menu_name"]]
seen, uniq = set(), []
for r in picks:
    if r["menu_name"] not in seen:
        seen.add(r["menu_name"])
        uniq.append(r)
if uniq:
    st.subheader(f"☕ {best}형 인간의 추천 메뉴")
    rng = random.Random("".join(str(a) for a in answers))
    cols = st.columns(3)
    for i, r in enumerate(rng.sample(uniq, min(3, len(uniq)))):
        with cols[i]:
            menu_card(st, r)
st.caption("📸 결과 화면을 캡처해서 친구한테 공유해 보세요! 다시 하려면 페이지를 새로고침하면 돼요.")
