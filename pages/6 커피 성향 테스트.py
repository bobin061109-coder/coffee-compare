"""상황형 질문 10개로 나의 '커피 캐릭터' 8종 중 하나를 알려주는 재미용 테스트."""
import datetime
import random
import re
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from menudata import BRAND_COLORS, load_menus, menu_card  # noqa: E402

st.set_page_config(page_title="커피 성향 테스트", page_icon="🧪", layout="centered")

# ---------------------------------------------------------------
# 캐릭터 8종: (이모지, 이름, 한줄, 설명, 특징, 잘 맞는 타입, 안 맞는 타입, 대표 음료 찾는 규칙)
# ---------------------------------------------------------------
TYPES = {
    "warrior": ("⚡", "각성 전사", "카페인은 연료, 나는 엔진",
                "커피를 '마시는' 게 아니라 '장전'하는 타입. 시험기간·마감 앞에서 가장 빛나고, 잔이 비면 불안해져요.",
                ["샷 추가는 기본 옵션", "대용량 아니면 감질남", "카페인 함량부터 확인함"],
                "trend", "monk", r"메가리카노|왕메가카페라떼|왕메가헛개리카노|빽사이즈 아메리카노|에스프레소|^아메리카노$"),
    "dessert": ("🍰", "디저트 덕후", "커피는 핑계, 진짜는 크림",
                "음료 위에 휘핑·토핑이 올라가야 비로소 완성. 달달함으로 하루를 버티는 행복 추구형이에요.",
                ["'덜 달게'는 내 사전에 없음", "토핑 추가 버튼을 사랑함", "사진 먼저 찍고 마심"],
                "latte", "thrift", r"빽스치노|프라페|퐁크러쉬|쉐이크|크림"),
    "monk": ("🧘", "디카페인 수행자", "평온함이 최고의 각성제",
             "카페 분위기는 좋지만 내 수면은 더 소중한 타입. 몸의 소리에 귀 기울이는 자기관리 장인이에요.",
             ["오후 3시 이후 카페인 금지", "허브티 이름을 줄줄 외움", "디카페인 옵션부터 찾음"],
             "granny", "warrior", r"디카페인|캐모마일|루이보스|페퍼민트|민트티"),
    "thrift": ("🎯", "가성비 장인", "맛은 같고 가격은 반",
               "같은 맛이면 무조건 싼 쪽. 앱 쿠폰·스탬프·이벤트를 놓치지 않는 생활력 만렙 타입이에요.",
               ["스탬프 쿠폰 지갑 보유", "이벤트 날짜를 외움", "기본 메뉴가 제일 맛있다고 믿음"],
               "warrior", "dessert", r"^아메리카노$|^카페라떼$"),
    "trend": ("🌈", "신상 사냥꾼", "출시 첫날이 내 생일",
              "신메뉴·콜라보·굿즈 소식엔 누구보다 빠른 타입. 친구들 사이 '이거 먹어봤어?'의 원조예요.",
              ["SNS로 신메뉴 소식 먼저 앎", "굿즈 때문에 음료 시킨 적 있음", "같은 메뉴 두 번은 잘 안 시킴"],
              "dessert", "granny", None),
    "latte": ("🥛", "라떼 감성러", "부드러움이 곧 행복",
              "쓴 것도 단 것도 아닌 딱 그 중간, 우유 거품의 포근함을 사랑하는 타입이에요. 카페에서 오래 머무는 스타일.",
              ["라떼 아트 보면 기분 좋아짐", "바닐라·헤이즐넛 시럽 감별 가능", "창가 자리 선호"],
              "dessert", "fresh", r"라떼|카푸치노|마끼아또|마키아또"),
    "fresh": ("🍹", "상큼 청량파", "커피 말고 톡 쏘는 거",
              "카페에 와도 커피보단 에이드·아이스티. 사계절 내내 얼음 가득 시원한 음료를 찾는 청량 그 자체예요.",
              ["한겨울에도 ICE", "탄산 없으면 섭섭함", "과일 이름 메뉴부터 봄"],
              "trend", "latte", r"에이드|아이스티|주스|소다|스무디|티샷"),
    "granny": ("🫖", "할매입맛 고수", "미숫가루는 근본이다",
               "고소함과 구수함을 아는 진정한 미식가. 곡물·쌍화·대추 메뉴를 보면 마음이 편안해지는 타입이에요.",
               ["'할메가' 이름만 봐도 끌림", "인절미 토핑 환영", "단맛보다 고소한 맛"],
               "monk", "fresh", r"미숫|쌍화|대추|곡물|고구마|할메가|인절미|토피넛|쌀라떼|율무|수정과|식혜"),
}

# 질문 10개: (질문, [(답, {타입: 점수})])
QUESTIONS = [
    ("📚 시험기간 새벽 2시, 내 책상 위에 있는 음료는?", [
        ("샷 추가한 대용량 아메리카노. 오늘 밤은 안 잔다", {"warrior": 3}),
        ("휘핑 듬뿍 프라페… 공부는 당 충전부터", {"dessert": 3}),
        ("캐모마일 티. 벼락치기보단 숙면이 답", {"monk": 3}),
        ("편의점 1+1 커피. 시험기간엔 아껴야지", {"thrift": 3}),
    ]),
    ("👀 카페 앞에 '신메뉴 출시!' 포스터가 붙어 있다", [
        ("오 바로 시켜봐야지 (이미 주문 중)", {"trend": 3}),
        ("크림이나 토핑 올라갔으면 고민해 봄", {"dessert": 2, "trend": 1}),
        ("가격 보고 비싸면 패스", {"thrift": 2}),
        ("난 늘 마시던 걸로~", {"latte": 2, "granny": 1}),
    ]),
    ("☀️ 영하 10도 한겨울 아침, 내 손에 들린 건?", [
        ("그래도 아이스. 얼죽아는 계절을 타지 않는다", {"fresh": 3}),
        ("따끈한 바닐라라떼로 손 녹이기", {"latte": 3}),
        ("뜨끈한 쌍화차나 대추차", {"granny": 3}),
        ("따뜻한 디카페인 한 잔", {"monk": 2}),
    ]),
    ("🧾 메뉴판 앞에 선 나는?", [
        ("메뉴판 안 봄. 주문은 3초 컷", {"warrior": 1, "latte": 1}),
        ("'NEW' 표시부터 찾는다", {"trend": 3}),
        ("에이드·티 칸으로 눈이 먼저 간다", {"fresh": 3}),
        ("곡물·고구마 같은 고소한 메뉴 찾기", {"granny": 2}),
    ]),
    ("💓 커피 마시고 심장이 두근두근. 나는?", [
        ("이게 살아있다는 느낌이지", {"warrior": 2}),
        ("다음부턴 디카페인으로 바꾼다", {"monk": 3}),
        ("커피 대신 상큼한 걸 마실 걸…", {"fresh": 2}),
        ("단 걸 같이 먹으면 괜찮아지더라", {"dessert": 2}),
    ]),
    ("🎁 친구 생일, 기프티콘으로 보낼 음료는?", [
        ("요즘 제일 핫한 콜라보 음료", {"trend": 3}),
        ("실패 없는 카페라떼", {"latte": 2, "thrift": 1}),
        ("케이크 같은 크림 음료 + 디저트 세트", {"dessert": 3}),
        ("아메리카노 2잔 (가성비 최고)", {"thrift": 3}),
    ]),
    ("🏷️ 내 텀블러에 붙어 있을 스티커는?", [
        ("'카페인 수혈 중'", {"warrior": 2}),
        ("'오늘도 무사히, 숙면 기원'", {"monk": 2}),
        ("과일 그림 스티커", {"fresh": 2}),
        ("'고소한 게 최고야'", {"granny": 2}),
    ]),
    ("🪑 카페에서 내가 앉는 자리는?", [
        ("테이크아웃이라 자리 필요 없음", {"warrior": 1, "thrift": 1, "fresh": 1}),
        ("햇살 드는 창가 소파", {"latte": 3}),
        ("사진 잘 나오는 예쁜 자리", {"dessert": 1, "trend": 2}),
        ("조용한 구석 자리", {"monk": 1, "granny": 1}),
    ]),
    ("🧓 할머니 댁 냉장고를 열었다. 꺼내 마시고 싶은 건?", [
        ("시원한 미숫가루", {"granny": 3}),
        ("유리병 식혜", {"granny": 2, "fresh": 1}),
        ("과일 주스", {"fresh": 2}),
        ("믹스커피 한 봉… 아니 세 봉", {"warrior": 1, "granny": 1}),
    ]),
    ("💸 이번 달 커피값이 10만 원 나왔다", [
        ("헉… 다음 달엔 쿠폰 모아서 반으로 줄인다", {"thrift": 3}),
        ("신메뉴 다 먹어봤으니 후회 없음", {"trend": 2}),
        ("이 정도 행복이면 싸지", {"dessert": 1, "latte": 2}),
        ("그만큼 열심히 살았다는 증거", {"warrior": 1, "latte": 1}),
    ]),
]

# ---------------------------------------------------------------
# 진행 상태
# ---------------------------------------------------------------
ss = st.session_state
ss.setdefault("q_step", 0)
ss.setdefault("q_answers", [None] * len(QUESTIONS))

st.title("🧪 나는 어떤 커피 캐릭터일까?")
st.caption("상황 질문 10개 · 결과는 8가지 캐릭터 중 하나 · 재미로 보는 테스트예요!")

step = ss.q_step
if step < len(QUESTIONS):
    q, opts = QUESTIONS[step]
    st.progress(step / len(QUESTIONS), text=f"{step + 1} / {len(QUESTIONS)}")
    st.subheader(q)
    for i, (text, _) in enumerate(opts):
        if st.button(text, key=f"q{step}_{i}", use_container_width=True):
            ss.q_answers[step] = i
            ss.q_step += 1
            st.rerun()
    if step > 0 and st.button("← 이전 질문"):
        ss.q_step -= 1
        st.rerun()
    st.stop()

# ---------------------------------------------------------------
# 결과
# ---------------------------------------------------------------
scores = {k: 0 for k in TYPES}
for (q, opts), a in zip(QUESTIONS, ss.q_answers):
    if a is not None:
        for k, v in opts[a][1].items():
            scores[k] += v
order = sorted(TYPES, key=lambda k: (-scores[k], list(TYPES).index(k)))
me = order[0]
emoji, name, slogan, desc, traits, best, worst, pattern = TYPES[me]
total = sum(scores.values()) or 1

st.balloons()
st.markdown(
    f"<div style='background:#FFF8EF;border:2px solid #C9A27A;border-radius:20px;padding:24px;text-align:center'>"
    f"<div style='font-size:4rem;line-height:1'>{emoji}</div>"
    f"<div style='color:#8B5E3C;font-weight:700;margin-top:8px'>당신의 커피 캐릭터는</div>"
    f"<div style='color:#3E2723;font-weight:900;font-size:2.2rem'>{name}</div>"
    f"<div style='color:#6F4E37;font-weight:700;font-size:1.1rem;margin-bottom:10px'>“{slogan}”</div>"
    f"<div style='color:#4E3626'>{desc}</div></div>",
    unsafe_allow_html=True,
)

st.markdown("#### ✅ 이런 특징이 있어요")
for t in traits:
    st.markdown(f"- {t}")

c1, c2 = st.columns(2)
b, w = TYPES[best], TYPES[worst]
c1.success(f"**💞 찰떡 궁합**\n\n{b[0]} {b[1]}\n\n“{b[2]}”")
c2.error(f"**💥 상극**\n\n{w[0]} {w[1]}\n\n“{w[2]}”")

st.markdown("#### 🧬 나의 커피 성분표")
for k in order[:4]:
    st.progress(scores[k] / total, text=f"{TYPES[k][0]} {TYPES[k][1]} {scores[k] / total:.0%}")

# 대표 음료: 실제 판매 메뉴에서 고르기
menus = load_menus()
if pattern is None:  # 신상 사냥꾼: 가장 최근에 나온 음료
    dated = [r for r in menus if r.get("released_at")]
    picks = sorted(dated, key=lambda r: r["released_at"], reverse=True)
else:
    picks = [r for r in menus if re.search(pattern, r["menu_name"])
             and (me == "monk" or "디카페인" not in r["menu_name"])]
picks = [r for r in picks if not r["menu_name"].startswith("ARIH")]
uniq, seen = [], set()
for r in picks:
    base = re.sub(r"디카페인|스몰사이즈|빽사이즈|\s", "", r["menu_name"])  # 같은 음료의 사이즈·디카페인 버전은 하나로
    if base not in seen:
        seen.add(base)
        uniq.append(r)
if pattern is not None:
    random.Random(str(ss.q_answers)).shuffle(uniq)
if uniq:
    st.markdown(f"#### ☕ {name}에게 추천하는 음료")
    cols = st.columns(3)
    for i, r in enumerate(uniq[:3]):
        with cols[i]:
            menu_card(st, r)
    fav = uniq[0]["brand"]
    st.markdown(f"<div style='text-align:center;color:{BRAND_COLORS.get(fav, '#6F4E37')};font-weight:800'>"
                f"오늘은 {fav} 가볼까요?</div>", unsafe_allow_html=True)

st.divider()
st.caption("📸 결과 화면을 캡처해서 친구한테 공유해 보세요! 친구랑 궁합도 비교해 봐요.")
if st.button("🔄 다시 하기", use_container_width=True):
    ss.q_step = 0
    ss.q_answers = [None] * len(QUESTIONS)
    st.rerun()
