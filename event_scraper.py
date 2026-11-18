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
        diagnose_menus(session)
    except Exception as exc:
        print("메뉴 진단 건너뜀:", exc)
    if not any(row.get("checked_at") == now for row in rows):
        raise SystemExit("새 공식 게시물을 하나도 확인하지 못했습니다. GitHub Actions 로그를 확인하세요.")


# ===== 메뉴 자동 추가 준비: 메뉴 페이지 구조 확인용 2차 (데이터는 바꾸지 않음) =====
def _show(label, text, limit=3000):
    print(f"  [{label}] {clean(text)[:limit]}")


def diagnose_menus(session):
    jobs = [
        ("mega", "https://www.mega-mgccoffee.com/menu/?menu_category1=1&menu_category2=1"),
        ("paik", "https://paikdabang.com/menu/menu_new/"),
        ("olma", "https://www.olmanama.com/brand_110"),
        ("olma", "https://www.olmanama.com/brand_104"),
    ]
    for kind, url in jobs:
        time.sleep(2)
        try:
            r = session.get(url, timeout=30)
            r.encoding = "utf-8"
            html = r.text
            print(f"[메뉴진단2] {url} → {r.status_code}, {len(html)}자")
            soup = BeautifulSoup(html, "html.parser")
            if kind == "mega":
                for m in list(re.finditer(r"menu\.php", html))[:4]:
                    _show("menu.php 주변", html[max(0, m.start() - 700): m.end() + 900], 1700)
                for form in soup.find_all("form")[:3]:
                    _show("form", str(form), 1500)
            elif kind == "paik":
                img = next((i for i in soup.find_all("img") if "/uploads/" in (i.get("src") or "")), None)
                if img:
                    node = img
                    for _ in range(4):
                        node = node.parent or node
                    _show("메뉴 1개 HTML", str(node), 3000)
            else:
                text = clean(soup.get_text(" ", strip=True))
                prices = re.findall(r"[^\s]{1,12}(?:\s[^\s]{1,12}){0,3}\s*[\d,]{3,6}\s*원", text)
                print(f"  가격 패턴 {len(prices)}개 예시: {prices[:25]}")
                idx = html.find("원<")
                if idx < 0:
                    idx = html.find("원")
                _show("가격 주변 HTML", html[max(0, idx - 1500): idx + 1500], 3000)
                tables = soup.find_all("table")
                print(f"  table {len(tables)}개")
                if tables:
                    _show("첫 table", str(tables[0]), 2000)
        except Exception as exc:  # 진단 실패는 수집에 영향 없음
            print(f"[메뉴진단2] {url} 실패: {exc}")

if __name__ == "__main__":
    main()
