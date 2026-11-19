# 저가커피 메뉴 비교 - 컴포즈커피 데이터

- `assets/compose/` : 메뉴 이미지 57장 (파일명 = 메뉴 id, 300x300 PNG)
- `compose_menu.py` : 메뉴 데이터와 필터/이미지 경로 함수
- `app_demo.py` : 단독 실행 가능한 데모 (`streamlit run app_demo.py`)

## 내 앱에 붙이기
```python
from compose_menu import get_menu, image_path
for item in get_menu(category="라떼", temp="I"):
    st.image(image_path(item), caption=item["name"])
```

## 메뉴 추가하는 법
1. 이미지를 `assets/compose/새id.png` 로 저장
2. `compose_menu.py` 의 `_RAW` 목록에 `("새id", "메뉴명", "카테고리")` 한 줄 추가

이미지 출처: 컴포즈커피 공식 홈페이지 (저작권은 각 브랜드에 있음)
