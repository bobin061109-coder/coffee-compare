"""여러 페이지에서 같이 쓰는 메뉴 데이터·사진 도우미."""
import csv
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MENU_CSV = ROOT / "data" / "menus.csv"
IMG_DIR = ROOT / "images"
BRANDS = ["컴포즈커피", "메가MGC커피", "빽다방"]
BRAND_COLORS = {"컴포즈커피": "#C8961E", "메가MGC커피": "#A14314", "빽다방": "#5B7FB5"}


def num(value):
    try:
        v = float(str(value).replace(",", ""))
        return v if v >= 0 else None
    except (TypeError, ValueError):
        return None


def load_menus():
    """확인 표시가 있는 메뉴만 읽습니다. 카페인·열량·출시일 칸도 같이 읽어요."""
    try:
        with MENU_CSV.open(encoding="utf-8-sig", newline="") as f:
            rows = []
            for r in csv.DictReader(f):
                r = {k: (v or "").strip() for k, v in r.items() if k}
                if r.get("brand") in BRANDS and r.get("menu_name") and r.get("data_verified", "").lower() == "true":
                    r["price"] = num(r.get("price_krw"))
                    r["caffeine"] = num(r.get("caffeine_mg"))
                    r["kcal_n"] = num(r.get("kcal"))
                    rows.append(r)
            return rows
    except (OSError, csv.Error, UnicodeError):
        return []


def _key(text):
    return unicodedata.normalize("NFC", str(text)).strip().casefold()


_PHOTOS = None


def photo_path(brand, menu, variant):
    """images 폴더에서 '브랜드_메뉴_옵션' 사진을 찾습니다. 옵션이 다르면 같은 메뉴 사진이라도 씀."""
    global _PHOTOS
    if _PHOTOS is None:
        _PHOTOS = {}
        if IMG_DIR.is_dir():
            for p in IMG_DIR.iterdir():
                if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    _PHOTOS[_key(p.stem)] = p
    exact = _PHOTOS.get(_key(f"{brand}_{menu}_{variant}"))
    if exact:
        return exact
    prefix = _key(f"{brand}_{menu}_")
    for k, p in _PHOTOS.items():
        if k.startswith(prefix):
            return p
    return None


def label(r):
    v = r.get("variant", "")
    return f"{r['menu_name']} ({v})" if v and v != "전체" else r["menu_name"]


def menu_card(st, r, extra=""):
    """사진 + 브랜드 + 메뉴명 카드."""
    with st.container(border=True):
        p = photo_path(r["brand"], r["menu_name"], r.get("variant", ""))
        if p:
            st.image(str(p), use_container_width=True)
        color = BRAND_COLORS.get(r["brand"], "#6F4E37")
        st.markdown(f"<span style='color:{color};font-weight:800'>{r['brand']}</span><br>"
                    f"<b>{label(r)}</b>", unsafe_allow_html=True)
        bits = []
        if r.get("price"):
            bits.append(f"{int(r['price']):,}원")
        if r.get("caffeine") is not None:
            bits.append(f"카페인 {r['caffeine']:g}mg")
        if extra:
            bits.append(extra)
        if bits:
            st.caption(" · ".join(bits))
