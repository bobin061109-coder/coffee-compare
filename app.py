import math
import unicodedata
from pathlib import Path

import streamlit as st
from core import BRANDS, load_data, search


st.set_page_config(
    page_title="커피픽 · 저가커피 메뉴 비교",
    page_icon="☕",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "images"

MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

NA = "확인 자료 없음"


def normalize(value):
    return unicodedata.normalize(
        "NFC", str(value)
    ).strip().casefold()


@st.cache_data(show_spinner=False)
def read_photo(path_string, modified_ns, size):
    # 수정 시각과 크기가 바뀌면 이미지 캐시도 갱신됩니다.
    path = Path(path_string)
    mime = MIME.get(path.suffix.lower().lstrip("."))

    if mime is None:
        return None

    try:
        return path.read_bytes()
    except OSError:
        return None


def find_photo(brand, menu, variant):
    target = normalize(
        str(brand) + "_" + str(menu) + "_" + str(variant)
    )

    try:
        if not IMG_DIR.is_dir():
            return None

        paths = sorted(
            IMG_DIR.iterdir(),
            key=lambda item: item.name,
        )

        for path in paths:
            if not path.is_file():
                continue

            extension = path.suffix.lower().lstrip(".")

            if extension not in MIME:
                continue

            if normalize(path.stem) == target:
                info = path.stat()

                return read_photo(
                    str(path),
                    info.st_mtime_ns,
                    info.st_size,
                )

    except OSError:
        return None

    return None


def number(value):
    if value is None or value == "":
        return None

    try:
        result = float(value)

        if math.isfinite(result):
            return result

        return None

    except (TypeError, ValueError, OverflowError):
        return None


def price_text(value):
    value = number(value)

    if value is None:
        return NA

    return format(value, ",.0f") + "원"


def rating_text(row):
    value = number(row.get("rating"))

    if value 
