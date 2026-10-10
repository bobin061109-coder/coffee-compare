"""CSV 검증 및 검색 로직. 네트워크 수집 또는 임의 값 보정은 하지 않습니다."""
import csv
import math
import re
from datetime import date
from pathlib import Path

BRANDS = ('컴포즈커피', '메가MGC커피', '우지커피', '빽다방')
METRICS = ('price_krw', 'volume_ml', 'rating', 'taste', 'review')
COLUMNS = ['brand', 'menu_name', 'variant', 'data_verified', 'verified_at',
           'menu_source_url', 'price_krw', 'price_source_url', 'volume_ml',
           'volume_source_url', 'rating', 'rating_scale', 'rating_source_url',
           'taste', 'taste_source_url', 'review', 'review_source_url']
SOURCES = dict(zip(METRICS, ('price_source_url', 'volume_source_url',
                           'rating_source_url', 'taste_source_url', 'review_source_url')))

def normalize(text):
    return re.sub(r'\s+', '', str(text)).casefold()

def valid_url(text):
    return bool(re.match(r'^https?://[^\s/]+(?:/[^\s]*)?$', text or ''))

def load_data(path):
    """Return (usable rows, warnings). Invalid metrics become None, never zero."""
    rows, warnings = [], []
    try:
        with Path(path).open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            missing = set(COLUMNS) - set(reader.fieldnames or [])
            if missing:
                return [], ['CSV 필수 열 누락: ' + ', '.join(sorted(missing))]
            for line, raw in enumerate(reader, start=2):
                row = {k: (raw.get(k) or '').strip() for k in COLUMNS}
                if row['brand'] not in BRANDS or not row['menu_name']:
                    warnings.append(f'{line}행: 브랜드 또는 메뉴명 오류로 제외했습니다.')
                    continue
                try:
                    checked = date.fromisoformat(row['verified_at'])
                    valid_date = checked <= date.today()
                except ValueError:
                    valid_date = False
                if (row['data_verified'].casefold() != 'true' or not valid_date
                        or not valid_url(row['menu_source_url'])):
                    warnings.append(f'{line}행: 확인 표시·확인일·메뉴 출처가 없어 제외했습니다.')
                    continue
                out = dict(row)
                for metric in METRICS:
                    value = row[metric]
                    out[metric] = None
                    if not value:
                        continue
                    if not valid_url(row[SOURCES[metric]]):
                        warnings.append(f'{line}행: {metric} 출처가 없어 표시하지 않습니다.')
                        continue
                    if metric in ('taste', 'review'):
                        out[metric] = value
                        continue
                    try:
                        number = float(value)
                        if not math.isfinite(number) or number < 0:
                            raise ValueError
                        if metric == 'volume_ml' and number <= 0:
                            raise ValueError
                        if metric == 'price_krw' and not number.is_integer():
                            raise ValueError
                        if metric == 'rating':
                            scale = float(row['rating_scale'])
                            if not math.isfinite(scale) or scale <= 0 or number > scale:
                                raise ValueError
                            out['rating_scale'] = scale
                            out['rating_normalized'] = number / scale * 5
                        out[metric] = number
                    except (ValueError, OverflowError):
                        warnings.append(f'{line}행: {metric} 값 오류로 표시하지 않습니다.')
                rows.append(out)
    except FileNotFoundError:
        warnings.append('CSV 파일이 없습니다. data/menus.csv를 준비해 주세요.')
    except (OSError, UnicodeError, csv.Error) as exc:
        warnings.append(f'CSV를 읽을 수 없습니다: {exc}')
    return rows, warnings

def search(rows, query, brands=BRANDS, sort='price'):
    key = normalize(query)
    if not key:
        return []
    found = [r for r in rows if r['brand'] in brands and
             key in normalize(r['menu_name'] + ' ' + r['variant'])]
    metric = 'rating_normalized' if sort == 'rating' else 'price_krw'
    def order(r):
        value = r.get(metric)
        return (value is None, -value if sort == 'rating' and value is not None
                else value if value is not None else 0, r['brand'], r['menu_name'])
    return sorted(found, key=order)
