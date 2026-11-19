"""컴포즈커피 메뉴 보기 데모.  실행: streamlit run app_demo.py"""
import streamlit as st
from compose_menu import get_menu, image_path, categories

st.set_page_config(page_title="컴포즈커피 메뉴", layout="wide")
st.title("☕ 컴포즈커피 메뉴")

with st.sidebar:
    category = st.selectbox("카테고리", ["전체"] + categories())
    temp = st.radio("온도", ["전체", "H", "I"], horizontal=True,
                    format_func=lambda x: {"H": "핫", "I": "아이스"}.get(x, x))
    include_decaf = st.checkbox("디카페인 포함", value=True)
    keyword = st.text_input("메뉴 검색")

items = get_menu(category, temp, include_decaf, keyword or None)
st.caption(f"{len(items)}개 메뉴")

COLS = 4
for i in range(0, len(items), COLS):
    cols = st.columns(COLS)
    for col, item in zip(cols, items[i:i + COLS]):
        with col:
            st.image(image_path(item), use_container_width=True)
            st.markdown(f"**{item['name']}**")
            if item["price"]:
                st.caption(f"{item['price']:,}원")
