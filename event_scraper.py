"""공개된 공식 브랜드 이벤트 목록에서 상세 링크만 수집합니다."""
import csv
import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "events.csv"
NEW_MENU = r"신메뉴|출시|신제품|NEW|시즌\s*메뉴|한정\s*메뉴"
# (브랜드, 주소, 종류, 제목 필터) — 한 브랜드에서 여러 페이지를 읽을 수 있습니다.
# 제목 필터가 있으면 그 단어가 들어간 게시물만 가져옵니다.
SOURCES = [
    ("컴포즈커피", "https://composecoffee.com/event", "compose", None),
    ("메가MGC커피", "https://www.mega-mgccoffee.com/bbs/?bbs_category=3", "mega", None),
    ("빽다방", "https://paikdabang.com/news/?cate=event", "paik", None),
    ("빽다방", "https://paikdabang.com/news/", "paik", NEW_MENU),  # 전체 소식 중 신메뉴 글만
]
FIELDS = ["id", "brand", "title", "snippet", "url", "checked_at"]
# 일부 공식 사이트는 일반 브라우저가 아닌 요청(User-Agent)을 차단합니다.
# 실제 브라우저와 유사한 헤더를 보내 차단 가능성을 줄입니다.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}
# 게시판마다 상세글 식별에 쓰는 쿼리 파라미터 이름이 달라서 폭넓게 받아둡니다.
DETAIL_KEYS = {
    "bbs_detail", "bbs_detail_id", "bbs_idx", "bbs_no", "wr_id", "idx",
    "post_id", "no", "seq", "num", "id", "bo_id", "article_id", "board_id",
}


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def is_detail_link(kind, parsed):
    path = parsed.path.rstrip("/")
    if kind == "compose":
        # /event/123 뿐 아니라 끝에 슬래시나 하위 경로가 더 붙는 경우도 허용합니다.
        return bool(re.search(r"/event/\d+", path))
    if kind == "paik":
        return "/post_news/" in path and path.rsplit("/", 1)[-1] not in ("", "event")
    if kind == "mega":
        params = parse_qs(parsed.query)
        if path.startswith("/bbs/detail") or "/bbs/board" in path:

            return True
        return any(key in params and params[key] for key in DETAIL_KEYS)
    return False


def parse_page(brand, kind, base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlparse(base_url).netloc.lower()
    anchors = soup.find_all("a", href=True)
    same_host = 0
    found, seen = [], set()
    for anchor in anchors:
        absolute = urljoin(base_url, anchor["href"].strip())
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https") or parsed.netloc.lower() != base_host:
            continue
        same_host += 1
        if not is_detail_link(kind, parsed):
            continue
        title = clean(anchor.get_text(" ", strip=True) or anchor.get("title", ""))
        if not title or title in {"이벤트", "더보기", "상세보기", "자세히 보기", "처음", "마지막", "이전", "다음"} or len(title) < 3:
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        event_id = hashlib.sha256((brand + "|" + absolute).encode()).hexdigest()[:16]
        found.append({"id": event_id, "brand": brand, "title": title[:200],
                      "snippet": "공식 사이트 게시물입니다. 진행 여부·기간·참여 조건은 원문에서 확인하세요.",
                      "url": absolute})
    # 사이트 구조가 또 바뀌면 다음 실행 로그에서 바로 원인을 알 수 있도록 진단 정보를 남깁니다.
    print(f"  [진단] {brand}: 전체 링크 {len(anchors)}개 중 같은 도메인 링크 {same_host}개, 상세글로 인식 {len(found)}개")
    if not found:
        # 상세글을 못 찾았을 때 실제 링크 모양을 로그에 남겨서 패턴을 맞출 수 있게 합니다.
        for anchor in anchors[:80]:
            text = clean(anchor.get_text(" ", strip=True))[:40]
            print(f"    [링크] {anchor['href'][:150]} | {text}")
        for tag in soup.find_all(attrs={"onclick": True})[:30]:
            text = clean(tag.get_text(" ", strip=True))[:40]
            print(f"    [onclick] {tag.name} {tag['onclick'][:150]} | {text}")
        for tag in soup.find_all(attrs={"data-href": True})[:30]:
            print(f"    [data-href] {tag['data-href'][:150]}")
        print(f"    [HTML 앞부분] {clean(html[:1500])}")
    return found


def read_old():
    if not OUT.exists():
        return {}
    try:
        with OUT.open(encoding="utf-8-sig", newline="") as f:
            return {r.get("id", ""): r for r in csv.DictReader(f) if r.get("id")}
    except (OSError, csv.Error, UnicodeError):
        return {}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    latest = read_old()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    warnings = []
    session = requests.Session()
    session.headers.update(HEADERS)
    collected = {}  # 브랜드별로 이번에 새로 찾은 게시물
    for index, (brand, url, kind, title_filter) in enumerate(SOURCES):
        if index:
            time.sleep(2)
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            items = parse_page(brand, kind, url, response.text)
            if title_filter:
                items = [i for i in items if re.search(title_filter, i["title"], re.IGNORECASE)]
                print(f"  {brand} 소식 중 신메뉴 글 {len(items)}개")
                if not items:
                    continue  # 신메뉴 글이 없을 수도 있으니 경고하지 않음
            if not items:
                warnings.append(f"{brand} ({url}): 상세 링크를 찾지 못함(사이트 구조 변경 또는 차단 가능)")
                continue
            bucket = collected.setdefault(brand, {})
            for item in items:
                bucket.setdefault(item["id"], item)
        except requests.RequestException as exc:
            warnings.append(f"{brand} ({url}): 요청 실패: {exc}")
    # 새로 찾은 브랜드만 목록을 교체하고, 실패한 브랜드는 예전 목록을 그대로 둡니다.
    for brand, bucket in collected.items():
        latest = {key: row for key, row in latest.items() if row.get("brand") != brand}
        for item in bucket.values():
            item["checked_at"] = now
            latest[item["id"]] = item
        print(f"{brand}: {len(bucket)}개 게시물 확인")
    rows = sorted(latest.values(), key=lambda r: r.get("checked_at", ""), reverse=True)[:300]
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"저장된 게시물: {len(rows)}개")
    for warning in warnings:
        print("경고:", warning)
    try:
        update_menus(session)
    except Exception as exc:  # 메뉴 추가가 실패해도 이벤트 수집은 유지
        print("메뉴 추가 건너뜀:", exc)
    if not any(row.get("checked_at") == now for row in rows):
        raise SystemExit("새 공식 게시물을 하나도 확인하지 못했습니다. GitHub Actions 로그를 확인하세요.")


# ===== 새 음료 메뉴 자동 추가 =====
# 공식 사이트 음료 메뉴만 읽어서 data/menus.csv에 없는 음료를 추가합니다. (디저트·푸드 제외)
# 기존 줄은 절대 수정·삭제하지 않습니다. 가격이 공식 페이지에 없으면 비워 둡니다(앱에서 '확인 자료 없음').
MENU_CSV = ROOT / "data" / "menus.csv"
IMG_DIR = ROOT / "images"
MENU_COLUMNS = ["brand", "menu_name", "variant", "data_verified", "verified_at",
                "menu_source_url", "price_krw", "price_source_url", "volume_ml",
                "volume_source_url", "rating", "rating_scale", "rating_source_url",
                "taste", "taste_source_url", "review", "review_source_url"]
PAIK_DRINK_PAGES = [  # 디저트 페이지(menu_dessert)는 넣지 않음
    "https://paikdabang.com/menu/menu_new/",
    "https://paikdabang.com/menu/menu_coffee/",
    "https://paikdabang.com/menu/menu_drink/",
    "https://paikdabang.com/menu/menu_ccino/",
]
MEGA_DRINK_LIST = ("https://www.mega-mgccoffee.com/menu/menu.php?page={page}&menu_category1=1"
                   "&menu_category2=1&category=&list_checkbox_all=all")  # category1=1 → 음료
MEGA_SOURCE = "https://www.mega-mgccoffee.com/menu/?menu_category1=1&menu_category2=1"


def norm(text):
    return re.sub(r"\s+", "", str(text or "")).casefold()


def split_variant(name):
    pre = re.match(r"\s*\((HOT|ICED?|ICE)\)\s*", name, re.IGNORECASE)
    if pre:  # 메가 '(HOT)헛개리카노' 처럼 앞에 붙은 경우
        return clean(name[pre.end():]), "HOT" if pre.group(1).upper() == "HOT" else "ICE"
    m = re.search(r"\(?\b(HOT|ICED?|ICE)\b\)?\s*$", name, re.IGNORECASE)
    if not m:
        return clean(name), "전체"
    variant = "HOT" if m.group(1).upper() == "HOT" else "ICE"
    return clean(name[:m.start()]), variant


def parse_paik(html, url):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for h3 in soup.find_all("h3"):
        box = h3
        for _ in range(6):
            if box.parent is None:
                break
            box = box.parent
            img = box.find("img", src=re.compile(r"/uploads/"))
            if img:
                break
        else:
            continue
        img = box.find("img", src=re.compile(r"/uploads/"))
        if not img:
            continue
        text = box.get_text(" ", strip=True)
        cup = re.search(r"컵용량\s*:?\s*([\d,.]+)\s*ml", text, re.IGNORECASE)
        if not cup:  # 컵용량이 없으면 음료가 아님(디저트 등)
            print(f"  [음료 아님으로 제외] {clean(h3.get_text(' ', strip=True))} ({url.rsplit('/', 2)[-2]})")
            continue
        name, variant = split_variant(h3.get_text(" ", strip=True))
        items.append({"name": name, "variant": variant, "volume": cup.group(1).replace(",", ""),
                      "img": urljoin(url, img["src"]), "source": url, "price": ""})
    return items


def parse_mega(html):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.find_all("li"):
        img = li.find("img")
        if not img:
            continue
        title = li.find(class_=re.compile(r"cont_text_title")) or li.find("b")
        if not title:
            continue
        raw = clean(title.get_text(" ", strip=True))
        text = li.get_text(" ", strip=True)
        name, variant = split_variant(raw)
        if variant == "전체":
            tags = re.findall(r"\b(HOT|ICE)\b", text)
            if len(set(tags)) == 1:
                variant = tags[0]
        vol = re.search(r"(\d+)\s*oz", text, re.IGNORECASE)
        items.append({"name": name, "variant": variant,
                      "volume": str(round(int(vol.group(1)) * 29.5735)) if vol else "",
                      "img": urljoin("https://www.mega-mgccoffee.com/", img.get("src") or ""),
                      "source": MEGA_SOURCE, "price": ""})
    return items


RECENT_DAYS = 60  # 공식 사진이 최근 60일 안에 올라온 음료만 '새 메뉴'로 봄


def image_date(url):
    """공식 사진 주소에 들어 있는 업로드 날짜를 읽습니다.
    빽다방: /uploads/2026/11/...  메가: .../menu/20261021185329_...png"""
    m = re.search(r"/uploads/(20\d{2})/(\d{2})/", url)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), 1, tzinfo=timezone.utc)
    m = re.search(r"/(20\d{2})(\d{2})(\d{2})\d{6}_", url)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def has_photo(brand, name, variant):
    stem = f"{brand}_{name}_{variant}"
    return any((IMG_DIR / f"{stem}.{ext}").exists() for ext in ("jpg", "jpeg", "png", "webp"))


def save_image(session, brand, name, variant, url):
    """공식 사진을 받아 가로 400px JPEG로 줄여 저장합니다(저장소 용량 절약)."""
    if not url or "/" in name or has_photo(brand, name, variant):
        return False
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        if not 0 < len(r.content) < 8_000_000:
            return False
        IMG_DIR.mkdir(exist_ok=True)
        path = IMG_DIR / f"{brand}_{name}_{variant}.jpg"
        try:
            from io import BytesIO
            from PIL import Image
            img = Image.open(BytesIO(r.content))
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
            if img.width > 400:
                img = img.resize((400, round(img.height * 400 / img.width)))
            img.save(path, "JPEG", quality=85, optimize=True)
        except Exception:  # 변환이 안 되면 원본 그대로 저장
            ext = urlparse(url).path.rsplit(".", 1)[-1].lower()
            if ext not in ("jpg", "jpeg", "png", "webp"):
                return False
            path.with_suffix("." + ext).write_bytes(r.content)
        return True
    except requests.RequestException as exc:
        print(f"  사진 저장 실패 {url}: {exc}")
        return False


def loose(text):
    """띄어쓰기·괄호·기호를 빼고 비교 (예: '녹차 빽스치노(베이직)' == '녹차빽스치노 베이직')."""
    text = str(text or "").casefold().replace("베이직", "basic").replace("소프트", "soft")
    return re.sub(r"[^0-9a-z가-힣]", "", text)


# 메뉴 이름 자체를 바로잡을 것 (CSV에 반영됨)
MENU_RENAMES = {
    ("빽다방", "녹차 빽스치노(베이직)"): "말차 빽스치노(베이직)",
    ("빽다방", "녹차 빽스치노(소프트)"): "말차 빽스치노(소프트)",
}

# 우리 데이터 이름 → 공식 사이트 이름 (공식 메뉴 목록을 보고 확실한 것만 짝지음)
PHOTO_ALIASES = {
    ("빽다방", "아샷추(아이스티+샷추가)"): "아이스티샷추가(아샷추)",
    ("빽다방", "아이스티"): "복숭아 아이스티",
    ("빽다방", "디카페인 연유라떼"): "디카페인 달달연유라떼",
    ("빽다방", "미숫가루 두유"): "미숫가루",
    ("빽다방", "미숫가루 물"): "미숫가루",
    ("빽다방", "미숫가루 우유"): "미숫가루",
    ("빽다방", "피스타치오정글 빽스치노(베이직)"): "피스타치오 빽스치노(BASIC)",
    ("빽다방", "피스타치오정글 빽스치노(소프트)"): "피스타치오 빽스치노(SOFT)",
    ("메가MGC커피", "콜드브루"): "콜드브루오리지널",
    ("메가MGC커피", "디카페인 콜드브루"): "콜드브루디카페인",
    ("메가MGC커피", "디카페인 콜드브루라떼"): "콜드브루디카페인라떼",
}


def loose_match(brand, name, variant, found):
    alias = PHOTO_ALIASES.get((brand, name))
    if alias:
        items = [i for i in found.get(brand, []) if i["img"] and loose(i["name"]) == loose(alias)]
        pick = [i for i in items if i["variant"] == variant] or items
        if pick:
            return pick[0]["img"]
    return _loose_match_all(brand, name, variant, found)


def _loose_match_all(brand, name, variant, found):
    """이름 표기가 조금 다른 경우를 맞춥니다. 확실할 때만 사진을 돌려줍니다."""
    url = _loose_match(brand, name, variant, found)
    if url is None and "(" in name:  # '녹차 빽스치노(베이직)' → '녹차 빽스치노'
        url = _loose_match(brand, re.sub(r"\(.*?\)", "", name), variant, found)
    return url


def _loose_match(brand, name, variant, found):
    target = loose(name)
    if len(target) < 3:
        return None
    items = [i for i in found.get(brand, []) if i["img"]]
    same = [i for i in items if loose(i["name"]) == target or loose(i["name"] + i["variant"]) == target + loose(variant)]
    if not same:
        # '블랙벨벳 라떼' → '챔피언스 블랙 벨벳 라떼'처럼 공식 이름 안에 그대로 들어 있는 경우 (디카페인·스몰 제외)
        same = [i for i in items if target in loose(i["name"])
                and not re.search(r"디카페인|스몰", i["name"]) and not re.search(r"디카페인|스몰", name)]
        names = {loose(i["name"]) for i in same}
        if len(names) != 1:  # 후보가 여러 개면 틀릴 수 있으니 포기
            return None
    pick = [i for i in same if i["variant"] == variant] or same
    return pick[0]["img"]


def backfill_photos(session, existing, found):
    """이미 있는 메뉴 중 사진이 없는 것에 공식 사진을 채웁니다."""
    exact, by_name = {}, {}
    for brand, items in found.items():
        for i in items:
            if i["img"]:
                exact.setdefault((brand, norm(i["name"]), i["variant"]), i["img"])
                by_name.setdefault((brand, norm(i["name"])), i["img"])
    added = 0
    for row in existing:
        brand, name, variant = row["brand"], row["menu_name"], row["variant"]
        if brand not in found or has_photo(brand, name, variant):
            continue
        url = (exact.get((brand, norm(name), variant)) or by_name.get((brand, norm(name)))
               or loose_match(brand, name, variant, found))
        if url and save_image(session, brand, name, variant, url):
            added += 1
            time.sleep(0.3)
    print(f"[사진] 기존 메뉴 사진 {added}개 채움")


def update_menus(session):
    try:
        with MENU_CSV.open(encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
    except (OSError, csv.Error, UnicodeError) as exc:
        print("메뉴 CSV를 읽지 못해 메뉴 추가를 건너뜀:", exc)
        return
    renamed = 0
    for r in existing:  # 공식 이름으로 바로잡기 (예: 빽다방엔 '녹차' 빽스치노가 없고 '말차'만 있음)
        for (brand, old_name), new_name in MENU_RENAMES.items():
            if r["brand"] == brand and r["menu_name"] == old_name:
                r["menu_name"] = new_name
                renamed += 1
    known = {(r["brand"], norm(r["menu_name"]), r["variant"]) for r in existing}
    known_names = {(r["brand"], norm(r["menu_name"])) for r in existing}
    found = {"빽다방": [], "메가MGC커피": []}

    for url in PAIK_DRINK_PAGES:
        time.sleep(2)
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            r.encoding = "utf-8"
            items = parse_paik(r.text, url)
            print(f"[메뉴] 빽다방 {url}: 음료 {len(items)}개")
            found["빽다방"] += items
        except requests.RequestException as exc:
            print(f"[메뉴] 빽다방 {url} 실패: {exc}")

    for page in range(1, 16):
        time.sleep(2)
        try:
            r = session.get(MEGA_DRINK_LIST.format(page=page), timeout=30,
                            headers={"Referer": MEGA_SOURCE, "X-Requested-With": "XMLHttpRequest"})
            r.raise_for_status()
            r.encoding = "utf-8"
            if page == 1:
                lis = [li for li in BeautifulSoup(r.text, "html.parser").find_all("li") if li.find("img")]
                print(f"[메뉴진단] 메가 1쪽 {len(r.text)}자, 사진 있는 li {len(lis)}개")
                for li in lis[:2]:
                    print("  [메가 메뉴 HTML]", clean(str(li))[:1500])
            items = parse_mega(r.text)
            if not items:
                break
            print(f"[메뉴] 메가 {page}쪽: 음료 {len(items)}개")
            found["메가MGC커피"] += items
        except requests.RequestException as exc:
            print(f"[메뉴] 메가 {page}쪽 실패: {exc}")
            break

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_rows = []
    for brand, items in found.items():
        names = {norm(i["name"]) for i in items}
        overlap = len({n for b, n in known_names if b == brand} & names)
        # 안전장치: 기존 메뉴와 3개 이상 겹치지 않으면 읽기가 잘못된 것으로 보고 추가하지 않음
        if overlap < 3:
            print(f"[메뉴] {brand}: 기존 메뉴와 겹치는 이름이 {overlap}개뿐이라 이번엔 추가하지 않음 (예시: {[i['name'] for i in items[:8]]})")
            continue
        fresh = []
        for item in items:
            name = item["name"]
            if not (2 <= len(name) <= 40) or not re.search(r"[가-힣]", name):
                continue
            key = (brand, norm(name), item["variant"])
            if key in known:
                continue
            uploaded = image_date(item["img"])
            if not uploaded or (datetime.now(timezone.utc) - uploaded).days > RECENT_DAYS:
                continue  # 예전부터 있던 메뉴(사진이 오래됨)는 새 메뉴로 보지 않음
            known.add(key)
            fresh.append(item)
        # 안전장치: 한 번에 너무 많으면 이름 표기가 달라 기존 메뉴를 새 메뉴로 착각한 것일 수 있음
        if len(fresh) > 30:
            print(f"[메뉴] {brand}: 새 음료가 {len(fresh)}개나 돼서 이번엔 추가하지 않음 (예시: {[i['name'] + ' ' + i['variant'] for i in fresh[:40]]})")
            continue
        for item in fresh:
            name = item["name"]
            row = {c: "" for c in MENU_COLUMNS}
            row.update({"brand": brand, "menu_name": name, "variant": item["variant"],
                        "data_verified": "True", "verified_at": today,
                        "menu_source_url": item["source"]})
            if item["volume"]:
                row.update({"volume_ml": item["volume"], "volume_source_url": item["source"]})
            new_rows.append(row)
            save_image(session, brand, name, item["variant"], item["img"])
            print(f"[메뉴] 새 음료 추가: {brand} · {name} ({item['variant']})")
    try:
        backfill_photos(session, existing, found)
    except Exception as exc:
        print("사진 채우기 건너뜀:", exc)
    # 공식 사이트에서 사라진 음료(단종·계절 종료)는 목록에서 뺍니다. 컴포즈는 확인할 수 없어 그대로 둡니다.
    removed = []
    keep = []
    for r in existing:
        brand = r["brand"]
        items = found.get(brand)
        if not items:
            keep.append(r)
            continue
        names = {norm(i["name"]) for i in items}
        if norm(r["menu_name"]) in names or loose_match(brand, r["menu_name"], r["variant"], found):
            keep.append(r)
        else:
            removed.append(r)
    for brand in found:
        total = sum(1 for r in existing if r["brand"] == brand)
        gone = [r for r in removed if r["brand"] == brand]
        # 안전장치: 한 브랜드의 40% 넘게 사라지면 공식 사이트를 잘못 읽은 것으로 보고 빼지 않음
        if total and len(gone) > total * 0.4:
            print(f"[메뉴] {brand}: {len(gone)}/{total}개가 없다고 나와서 이번엔 빼지 않음")
            keep += gone
            removed = [r for r in removed if r["brand"] != brand]
    for r in removed:
        print(f"[메뉴] 공식 사이트에 없어 뺌: {r['brand']} · {r['menu_name']} ({r['variant']})")
    if not (new_rows or removed or renamed):
        print("[메뉴] 바뀐 메뉴 없음")
        return
    order = {id(r): i for i, r in enumerate(existing)}
    keep.sort(key=lambda r: order[id(r)])
    with MENU_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MENU_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(keep + new_rows)
    print(f"[메뉴] 추가 {len(new_rows)}개 · 뺌 {len(removed)}개 · 이름 고침 {renamed}개")

if __name__ == "__main__":
    main()
