"""하루 1회 공식 공개 페이지의 이벤트 링크를 확인해 data/events.csv로 저장합니다.
로그인/봇 차단 우회 없이 공개 페이지만 낮은 빈도로 요청합니다.
"""
import csv
import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
OUT = ROOT / "data" / "events.csv"
SOURCES = {
    "컴포즈커피": ("https://composecoffee.com/event", "compose"),
    "메가MGC커피": ("https://www.mega-mgccoffee.com/bbs/?bbs_category=3", "mega"),
    "우지커피": ("https://oozycoffee.com/index", "oozy"),
    "빽다방": ("https://paikdabang.com/news/?cate=event", "paik"),
}
FIELDS = ["id", "brand", "title", "snippet", "url", "checked_at"]
KEYWORDS = ("이벤트", "프로모션", "할인", "쿠폰", "증정", "응모", "당첨", "혜택", "행사", "EVENT")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CoffeeCompareEventChecker/1.0)"}


def clean(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"조회\s*[\d,]+", "", text)
    text = re.sub(r"\b20\d\d[-./]\d{1,2}[-./]\d{1,2}\b", "", text)
    return re.sub(r"\s+", " ", text).strip(" ·|-\t")


def is_event(text):
    return any(k.casefold() in text.casefold() for k in KEYWORDS)


def parse_page(brand, kind, base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()
    base_host = urlparse(base_url).netloc.lower()
    for a in soup.find_all("a", href=True):
        absolute = urljoin(base_url, a["href"].strip())
        parsed = urlparse(absolute)
        if parsed.scheme not in ("https", "http"):
            continue
        text = clean(a.get_text(" ", strip=True))
        if kind == "compose":
            accept = "/event/" in parsed.path and parsed.path.rstrip("/") != "/event"
        elif kind == "mega":
            accept = "/bbs/detail/" in parsed.path
        elif kind == "paik":
            accept = "/post_news/" in parsed.path
        else:  # 우지커피 공식 홈페이지가 연결한 공식 SNS 게시물
            host = parsed.netloc.lower()
            accept = host.endswith("instagram.com") and ("/p/" in parsed.path or "/reel/" in parsed.path)
        if not accept or not text or not is_event(text):
            continue
        if kind != "oozy" and parsed.netloc.lower() != base_host:
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        digest = hashlib.sha256((brand + "|" + absolute).encode()).hexdigest()[:16]
        out.append({
            "id": digest,
            "brand": brand,
            "title": text[:180],
            "snippet": "공식 게시물입니다. 기간·대상·조건은 원문에서 확인해 주세요.",
            "url": absolute,
        })
    return out


def read_previous():
    if not OUT.exists():
        return {}
    with OUT.open(encoding="utf-8-sig", newline="") as f:
        return {r.get("id", ""): r for r in csv.DictReader(f) if r.get("id")}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    merged = read_previous()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    warnings = []
    session = requests.Session()
    session.headers.update(HEADERS)
    for idx, (brand, (url, kind)) in enumerate(SOURCES.items()):
        if idx:
            time.sleep(2)
        try:
            response = session.get(url, timeout=25)
            response.raise_for_status()
            items = parse_page(brand, kind, url, response.text)
            if not items:
                # Markup changes or a temporary partial response must not erase known data.
                warnings.append(f"{brand}: matching event links not found; old records kept")
                continue
            # A successful nonempty listing is the current snapshot for this brand.
            merged = {key: row for key, row in merged.items() if row.get("brand") != brand}
            for item in items:
                item["checked_at"] = now
                merged[item["id"]] = item
        except Exception as exc:
            warnings.append(f"{brand}: {type(exc).__name__}: {exc}")
    rows = sorted(merged.values(), key=lambda r: r.get("checked_at", ""), reverse=True)[:300]
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} records")
    if warnings:
        print("Warnings: " + " | ".join(warnings))


if __name__ == "__main__":
    main()
