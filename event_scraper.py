"""공개된 공식 브랜드 이벤트 목록에서 상세 링크만 수집합니다.
수집 실패/페이지 구조 변경 시 기존 CSV를 지우지 않고 Action 로그에 경고합니다.
"""
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
SOURCES = {
    "컴포즈커피": ("https://composecoffee.com/event", "compose"),
    "메가MGC커피": ("https://www.mega-mgccoffee.com/bbs/?bbs_category=3", "mega"),
    "빽다방": ("https://paikdabang.com/news/?cate=event", "paik"),
}
FIELDS = ["id", "brand", "title", "snippet", "url", "checked_at"]
HEADERS = {"User-Agent": "CoffeeCompareEvents/1.0 (public official page checker)"}
DETAIL_KEYS = {"bbs_detail", "bbs_detail_id", "bbs_idx", "bbs_no", "wr_id", "idx", "post_id"}


def clean(value):
    return re.sub(r"\\s+", " ", value or "").strip()


def is_detail_link(kind, parsed):
    path = parsed.path.rstrip("/")
    if kind == "compose":
        return bool(re.fullmatch(r"/event/\\d+", path))
    if kind == "paik":
        return "/post_news/" in path and path.rsplit("/", 1)[-1] not in ("", "event")
    if kind == "mega":
        params = parse_qs(parsed.query)
        has_detail_param = any(key in params and params[key] for key in DETAIL_KEYS)
        return "/bbs/detail/" in path or has_detail_param
    return False


def parse_page(brand, kind, base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlparse(base_url).netloc.lower()
    found, seen = [], set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("https", "http") or parsed.netloc.lower() != base_host:
            continue
        if not is_detail_link(kind, parsed):
            continue
        title = clean(anchor.get_text(" ", strip=True) or anchor.get("title", ""))
        if not title or title in {"이벤트", "더보기", "상세보기", "자세히 보기"}:
            continue
        if title in {"처음", "마지막", "이전", "다음"} or len(title) < 3:
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        event_id = hashlib.sha256((brand + "|" + absolute).encode()).hexdigest()[:16]
        found.append({
            "id": event_id,
            "brand": brand,
            "title": title[:200],
            "snippet": "공식 사이트 게시물입니다. 진행 여부·기간·참여 조건은 원문에서 확인하세요.",
            "url": absolute,
        })
    return found


def read_old():
    if not OUT.exists():
        return {}
    try:
        with OUT.open(encoding="utf-8-sig", newline="") as file:
            return {row.get("id", ""): row for row in csv.DictReader(file) if row.get("id")}
    except (OSError, csv.Error, UnicodeError):
        return {}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    latest = read_old()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    errors = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for index, (brand, (url, kind)) in enumerate(SOURCES.items()):
        if index:
            time.sleep(2)
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            items = parse_page(brand, kind, url, response.text)
            if not items:
                errors.append(f"{brand}: 상세 이벤트 링크를 찾지 못함(페이지 구조 변경 또는 차단 가능)")
                continue
            latest = {key: row for key, row in latest.items() if row.get("brand") != brand}
            for item in items:
                item["checked_at"] = now
                latest[item["id"]] = item
            print(f"{brand}: {len(items)}개 링크 확인")
        except requests.RequestException as exc:
            errors.append(f"{brand}: 요청 실패: {exc}")

    rows = sorted(latest.values(), key=lambda row: row.get("checked_at", ""), reverse=True)[:300]
    with OUT.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"저장된 이벤트: {len(rows)}개")
    for message in errors:
        print("경고:", message)
    if not any(row.get("checked_at") == now for row in rows):
        raise SystemExit("새 공식 이벤트 목록을 하나도 확인하지 못했습니다. Actions 로그를 확인하세요.")


if __name__ == "__main__":
    main()
