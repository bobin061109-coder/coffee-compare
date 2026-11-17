"""
건강 기반 커피 추천 백엔드 (FastAPI)

앱은 '가공된 feature' 만 보낸다. 서버는 규칙 기반 엔진으로
① 권장 카페인 상한을 계산하고 ② 메뉴 DB에서 적합 음료를 추천한다.

실행:
    pip install fastapi uvicorn pydantic
    uvicorn main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Coffee Health Recommender")


# ---------- 입출력 스키마 ----------
class RecommendRequest(BaseModel):
    sleepHours: Optional[float] = None
    avgHeartRate: Optional[int] = None
    restingHeartRate: Optional[int] = None
    steps: int = 0
    exerciseMinutes: int = 0
    localHour: int = 12


class RecommendResponse(BaseModel):
    recommendation: str
    reason: str
    caffeineLimitMg: int
    tags: list[str]


# ---------- 커피 메뉴 DB (예시) ----------
# caffeine_mg: 1잔 기준, sugar_g: 당, tags: 분류
MENU = [
    {"name": "디카페인 아메리카노", "caffeine_mg": 10,  "sugar_g": 0,  "tags": ["decaf", "low_sugar"]},
    {"name": "아메리카노",         "caffeine_mg": 120, "sugar_g": 0,  "tags": ["low_sugar"]},
    {"name": "콜드브루",           "caffeine_mg": 200, "sugar_g": 0,  "tags": ["strong", "low_sugar"]},
    {"name": "라떼",               "caffeine_mg": 120, "sugar_g": 12, "tags": []},
    {"name": "단백질 쉐이크 라떼",  "caffeine_mg": 90,  "sugar_g": 6,  "tags": ["recovery", "protein"]},
    {"name": "허브티 (카페인프리)", "caffeine_mg": 0,   "sugar_g": 0,  "tags": ["decaf", "calm"]},
]


# ---------- 추천 엔진 ----------
# 성인 1일 카페인 권고 상한 400mg (식약처/FDA 기준) 을 개인 상태로 조정
BASE_DAILY_LIMIT = 400


def compute_caffeine_limit(req: RecommendRequest) -> int:
    limit = BASE_DAILY_LIMIT
    # 수면 부족 -> 상한 하향 (과카페인 시 악순환 방지)
    if req.sleepHours is not None and req.sleepHours < 6:
        limit -= 100
    # 안정 심박이 높으면(스트레스/각성) 하향
    if req.restingHeartRate is not None and req.restingHeartRate > 80:
        limit -= 80
    # 늦은 오후/저녁은 수면 보호를 위해 하향
    if req.localHour >= 14:
        limit -= 100
    if req.localHour >= 18:
        limit -= 100
    return max(limit, 0)


def recommend_drink(req: RecommendRequest, caffeine_limit: int) -> tuple[dict, str, list[str]]:
    want_tags: list[str] = []
    reason_parts: list[str] = []

    low_sleep = req.sleepHours is not None and req.sleepHours < 6
    high_hr = req.restingHeartRate is not None and req.restingHeartRate > 80
    post_workout = req.exerciseMinutes >= 30
    late = req.localHour >= 18

    # 1) 저녁/카페인 여력 없음 -> 디카페인·카페인프리
    if late or caffeine_limit < 60:
        want_tags.append("decaf")
        reason_parts.append("늦은 시간이라 수면을 지키기 위해 저·무카페인을 권해요")
    # 2) 스트레스/심박 높음 -> 진정
    elif high_hr:
        want_tags.append("decaf")
        reason_parts.append(f"안정 심박이 높아({req.restingHeartRate}bpm) 카페인을 줄이는 게 좋아요")
    # 3) 운동 직후 -> 회복
    elif post_workout:
        want_tags.append("recovery")
        reason_parts.append(f"운동 {req.exerciseMinutes}분 후라 회복에 좋은 메뉴예요")
    # 4) 수면 부족 + 아침/오전 -> 적당한 각성 (강하게는 X)
    elif low_sleep:
        reason_parts.append(f"어젯밤 수면이 {req.sleepHours:.1f}시간으로 짧아 적당한 각성을 도와요")
    else:
        reason_parts.append("오늘 컨디션에 무난한 선택이에요")

    # 메뉴 중: 카페인 상한 이내 + 원하는 태그 우선
    candidates = [m for m in MENU if m["caffeine_mg"] <= caffeine_limit]
    if not candidates:
        candidates = [min(MENU, key=lambda m: m["caffeine_mg"])]

    # 각성이 필요한 상황(디카페인을 원하지 않음): 상한 이내에서 가장 가까운
    #   '적당한 카페인' 음료를 목표로 한다. 수면부족이면 좀 더 높게.
    want_awake = "decaf" not in want_tags and "recovery" not in want_tags
    target_caffeine = 150 if low_sleep else 100

    def score(m: dict) -> float:
        s = float(sum(1 for t in want_tags if t in m["tags"]))
        if late and "low_sugar" in m["tags"]:
            s += 1
        if want_awake:
            # 목표 카페인에 가까울수록 높은 점수 (거리 역수)
            s += 1.0 / (1 + abs(m["caffeine_mg"] - target_caffeine) / 50.0)
        return s

    best = max(candidates, key=score)
    return best, " · ".join(reason_parts), want_tags


@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest) -> RecommendResponse:
    limit = compute_caffeine_limit(req)
    drink, reason, tags = recommend_drink(req, limit)
    return RecommendResponse(
        recommendation=f"{drink['name']} (카페인 {drink['caffeine_mg']}mg)",
        reason=reason,
        caffeineLimitMg=limit,
        tags=tags,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
