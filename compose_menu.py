"""컴포즈커피 메뉴 데이터 + 이미지 경로 도우미.

사용 예 (기존 Streamlit 앱 어디서든):
    from compose_menu import get_menu, image_path
    for item in get_menu(category="라떼", temp="I"):
        st.image(image_path(item), caption=item["name"])

가격·칼로리 등은 아직 없으니 MENU 항목에 "price": 2500 처럼 키를 추가해서 쓰면 됩니다.
"""
from pathlib import Path

BASE_DIR = Path(__file__).parent
IMG_DIR = BASE_DIR / "assets" / "compose"
PLACEHOLDER = BASE_DIR / "assets" / "placeholder.png"

# (id, 공식 메뉴명, 카테고리)  ← id 가 곧 이미지 파일명(assets/compose/{id}.png)
_RAW = [
    ("espresso", "에스프레소", "에스프레소"),
    ("h_americano", "H-아메리카노", "아메리카노"),
    ("i_americano", "I-아메리카노", "아메리카노"),
    ("i_bigpot_americano", "I-빅포즈 아메리카노", "아메리카노"),
    ("h_honey_americano", "H-꿀아메리카노", "아메리카노"),
    ("i_honey_americano", "I-꿀아메리카노", "아메리카노"),
    ("i_airy_americano", "에어리 아메리카노", "아메리카노"),
    ("h_decaf_americano", "H-디카페인 아메리카노", "아메리카노"),
    ("i_decaf_americano", "I-디카페인 아메리카노", "아메리카노"),
    ("i_bigpot_decaf_americano", "I-빅포즈 디카페인 아메리카노", "아메리카노"),
    ("i_ashotchu", "I-아샷추", "샷추"),
    ("i_bigpot_ashotchu", "I-빅포즈 아샷추", "샷추"),
    ("i_maeshotchu", "I-매샷추", "샷추"),
    ("h_cafe_latte", "H-카페라떼", "라떼"),
    ("i_cafe_latte", "I-카페라떼", "라떼"),
    ("i_bigpot_cafe_latte", "I-빅포즈 카페라떼", "라떼"),
    ("h_cappuccino", "H-카푸치노", "라떼"),
    ("h_vanilla_latte", "H-바닐라라떼", "라떼"),
    ("i_vanilla_latte", "I-바닐라라떼", "라떼"),
    ("i_bigpot_vanilla_latte", "I-빅포즈 바닐라라떼", "라떼"),
    ("h_hazelnut_latte", "H-헤이즐넛라떼", "라떼"),
    ("i_hazelnut_latte", "I-헤이즐넛라떼", "라떼"),
    ("i_bigpot_hazelnut_latte", "I-빅포즈 헤이즐넛라떼", "라떼"),
    ("h_dolce_latte", "H-돌체라떼", "라떼"),
    ("i_dolce_latte", "I-돌체라떼", "라떼"),
    ("i_bigpot_dolce_latte", "I-빅포즈 돌체라떼", "라떼"),
    ("i_brownsugar_cafe_latte", "I-흑당 카페라떼", "라떼"),
    ("i_brownsugar_bubble_cafe_latte", "I-흑당 버블 카페라떼", "라떼"),
    ("h_caramel_macchiato", "H-캬라멜마끼아또", "라떼"),
    ("i_caramel_macchiato", "I-캬라멜마끼아또", "라떼"),
    ("h_cafe_mocha", "H-카페모카", "라떼"),
    ("i_cafe_mocha", "I-카페모카", "라떼"),
    ("i_dalgona_latte", "I-달고나라떼", "라떼"),
    ("i_vanilla_cream_latte", "I-바닐라크림라떼", "라떼"),
    ("i_nutty_cream_latte", "I-너티크림라떼", "라떼"),
    ("h_allday_oat", "H-올데이 오트", "라떼"),
    ("i_allday_oat", "I-올데이 오트", "라떼"),
    ("h_decaf_cafe_latte", "H-디카페인 카페라떼", "라떼"),
    ("i_decaf_cafe_latte", "I-디카페인 카페라떼", "라떼"),
    ("i_bigpot_decaf_latte", "I-빅포즈 디카페인라떼", "라떼"),
    ("h_decaf_vanilla_latte", "H-디카페인 바닐라라떼", "라떼"),
    ("i_decaf_vanilla_latte", "I-디카페인 바닐라라떼", "라떼"),
    ("h_decaf_hazelnut_latte", "H-디카페인 헤이즐넛라떼", "라떼"),
    ("i_decaf_hazelnut_latte", "I-디카페인 헤이즐넛라떼", "라떼"),
    ("h_decaf_dolce_latte", "H-디카페인 돌체라떼", "라떼"),
    ("i_decaf_dolce_latte", "I-디카페인 돌체라떼", "라떼"),
    ("h_cold_brew", "H-콜드브루", "콜드브루"),
    ("i_cold_brew", "I-콜드브루", "콜드브루"),
    ("h_cold_brew_latte", "H-콜드브루라떼", "콜드브루"),
    ("i_cold_brew_latte", "I-콜드브루라떼", "콜드브루"),
    ("h_decaf_cold_brew", "H-디카페인콜드브루", "콜드브루"),
    ("i_decaf_cold_brew", "I-디카페인콜드브루", "콜드브루"),
    ("h_decaf_cold_brew_latte", "H-디카페인콜드브루라떼", "콜드브루"),
    ("i_decaf_cold_brew_latte", "I-디카페인콜드브루라떼", "콜드브루"),
    ("i_compose_mix_coffee", "I-컴포즈믹스커피", "기타"),
    ("jjondeukcano", "쫀득카노", "콤보"),
    ("coffee_bread_combo", "커피엔 역시 커피빵", "콤보"),
]


def _build():
    menu = []
    for id_, name, category in _RAW:
        menu.append({
            "id": id_,
            "name": name,
            "category": category,
            "temp": "H" if name.startswith("H-") else "I" if name.startswith("I-") else None,
            "decaf": "디카페인" in name,
            "bigpot": "빅포즈" in name,
            "brand": "컴포즈커피",
            "price": None,  # TODO: 가격 입력
        })
    return menu


MENU = _build()


def image_path(item):
    """메뉴 이미지 경로. 파일이 없으면 기본 이미지를 돌려줍니다."""
    p = IMG_DIR / f"{item['id']}.png"
    return str(p if p.exists() else PLACEHOLDER)


def get_menu(category=None, temp=None, include_decaf=True, keyword=None):
    """조건에 맞는 메뉴 리스트를 돌려줍니다. 인자를 비우면 전체."""
    result = MENU
    if category and category != "전체":
        result = [m for m in result if m["category"] == category]
    if temp and temp != "전체":
        result = [m for m in result if m["temp"] == temp]
    if not include_decaf:
        result = [m for m in result if not m["decaf"]]
    if keyword:
        result = [m for m in result if keyword in m["name"]]
    return result


def categories():
    seen = []
    for m in MENU:
        if m["category"] not in seen:
            seen.append(m["category"])
    return seen
