from pathlib import Path
import pandas as pd
import streamlit as st
from core import BRANDS, load_data, search

st.set_page_config(page_title='저가커피 메뉴 비교', page_icon='☕', layout='wide')
st.title('☕ 저가커피 메뉴 비교')
st.caption('컴포즈커피 · 메가MGC커피 · 빽다방')
st.info('확인된 CSV 자료만 표시합니다. 미확인 항목은 “확인 자료 없음”이며 0점·0원으로 처리하지 않습니다. 가격은 지점·옵션·시점에 따라 달라질 수 있습니다.')
with st.sidebar:
    st.header('검색 설정')
    selected = st.multiselect('비교 브랜드', BRANDS, default=list(BRANDS))
    sort_label = st.radio('정렬', ['가격 낮은 순', '평점 높은 순'])
    st.caption('평점은 척도가 다르면 5점 만점으로 환산합니다. 출처·표본·시점이 다른 평점은 직접 비교에 주의하세요.')
    st.button('데이터 새로 읽기', help='CSV를 변경한 후 누르세요.')
query = st.text_input('메뉴명 입력', placeholder='예: 아메리카노, 라떼')
rows, warnings = load_data(Path(__file__).resolve().parent / 'data' / 'menus.csv')
if warnings:
    with st.expander(f'데이터 확인 안내 ({len(warnings)}건)'):
        for warning in warnings:
            st.warning(warning)
if not rows:
    st.warning('표시 가능한 확인 데이터가 없습니다. README의 수집·확인 절차에 따라 CSV를 채워 주세요.')
if not selected:
    st.info('비교할 브랜드를 하나 이상 선택해 주세요.')
elif not query.strip():
    st.info('메뉴명을 입력하면 관련 메뉴를 검색합니다.')
else:
    results = search(rows, query, selected, 'rating' if sort_label == '평점 높은 순' else 'price')
    if not results:
        st.warning(f'“{query}” 검색 결과가 없습니다. 다른 메뉴명으로 검색하거나 CSV 자료를 확인해 주세요.')
    missing = [b for b in selected if not any(r['brand'] == b for r in results)]
    if missing:
        st.info('해당 검색어의 확인 메뉴 데이터가 없는 브랜드: ' + ', '.join(missing))
    if results:
        st.subheader(f'검색 결과 {len(results)}건')
        def number(value, unit):
            return '확인 자료 없음' if value is None else f'{value:,.0f}{unit}'
        table = []
        for r in results:
            table.append({'브랜드': r['brand'], '메뉴명': r['menu_name'], '옵션/크기': r['variant'],
                          '가격': number(r['price_krw'], '원'), '용량': number(r['volume_ml'], 'mL'),
                          '평점(원척도)': '확인 자료 없음' if r['rating'] is None else f"{r['rating']:g}/{r['rating_scale']:g}",
                          '평점(5점 환산)': '확인 자료 없음' if r.get('rating_normalized') is None else f"{r['rating_normalized']:.2f}",
                          '맛 평가': r['taste'] or '확인 자료 없음', '리뷰': r['review'] or '확인 자료 없음',
                          '확인일': r['verified_at']})
        st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
        st.subheader('출처 및 상세 정보')
        source_fields = [('메뉴', 'menu_source_url', None), ('가격', 'price_source_url', 'price_krw'),
                         ('용량', 'volume_source_url', 'volume_ml'), ('평점', 'rating_source_url', 'rating'),
                         ('맛 평가', 'taste_source_url', 'taste'), ('리뷰', 'review_source_url', 'review')]
        for index, r in enumerate(results, 1):
            with st.expander(f"{index}. {r['brand']} — {r['menu_name']} {r['variant']}"):
                st.write('확인일:', r['verified_at'])
                st.write('맛 평가:', r['taste'] or '확인 자료 없음')
                st.write('리뷰:', r['review'] or '확인 자료 없음')
                for label, field, metric in source_fields:
                    if r[field] and (metric is None or r.get(metric) is not None):
                        st.link_button(label + ' 출처', r[field])
