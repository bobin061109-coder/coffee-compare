"""Lightweight drink recommendation data and scoring logic."""

MENU = [
    {"name": "아메리카노", "category": "coffee", "flavors": ("nutty",), "sweetness": 0, "temps": ("ice", "hot"), "caffeine": "high", "price": 3000, "sizes": ("medium", "large"), "activities": ("study", "work"), "feelings": ("tired", "energetic"), "popularity": 10},
    {"name": "카페라떼", "category": "coffee", "flavors": ("nutty", "sweet"), "sweetness": 1, "temps": ("ice", "hot"), "caffeine": "high", "price": 4000, "sizes": ("medium", "large"), "activities": ("study", "relax", "dessert"), "feelings": ("calm", "tired"), "popularity": 9},
    {"name": "바닐라라떼", "category": "coffee", "flavors": ("sweet",), "sweetness": 2, "temps": ("ice", "hot"), "caffeine": "high", "price": 4800, "sizes": ("medium", "large"), "activities": ("relax", "dessert"), "feelings": ("calm", "refresh"), "popularity": 8},
    {"name": "카라멜마끼아또", "category": "coffee", "flavors": ("sweet",), "sweetness": 3, "temps": ("ice", "hot"), "caffeine": "high", "price": 5200, "sizes": ("medium", "large"), "activities": ("dessert", "relax"), "feelings": ("refresh", "tired"), "popularity": 8},
    {"name": "콜드브루", "category": "coffee", "flavors": ("nutty",), "sweetness": 0, "temps": ("ice",), "caffeine": "high", "price": 4500, "sizes": ("medium", "large"), "activities": ("work", "study"), "feelings": ("tired", "energetic"), "popularity": 7},
    {"name": "초코라떼", "category": "non_coffee", "flavors": ("sweet",), "sweetness": 3, "temps": ("ice", "hot"), "caffeine": "low", "price": 4500, "sizes": ("medium", "large"), "activities": ("dessert", "relax"), "feelings": ("calm", "refresh"), "popularity": 8},
    {"name": "곡물라떼", "category": "non_coffee", "flavors": ("nutty", "sweet"), "sweetness": 1, "temps": ("ice", "hot"), "caffeine": "none", "price": 4800, "sizes": ("medium", "large"), "activities": ("relax", "new"), "feelings": ("calm",), "popularity": 6},
    {"name": "딸기라떼", "category": "non_coffee", "flavors": ("sweet", "sour"), "sweetness": 3, "temps": ("ice",), "caffeine": "none", "price": 5500, "sizes": ("medium", "large"), "activities": ("dessert", "new", "relax"), "feelings": ("refresh", "energetic"), "popularity": 9},
    {"name": "고구마라떼", "category": "non_coffee", "flavors": ("nutty", "sweet"), "sweetness": 2, "temps": ("hot", "ice"), "caffeine": "none", "price": 5000, "sizes": ("medium", "large"), "activities": ("relax", "dessert"), "feelings": ("calm",), "popularity": 5},
    {"name": "얼그레이", "category": "tea", "flavors": ("sweet",), "sweetness": 0, "temps": ("hot", "ice"), "caffeine": "low", "price": 3500, "sizes": ("small", "medium"), "activities": ("relax", "study"), "feelings": ("calm",), "popularity": 6},
    {"name": "캐모마일", "category": "tea", "flavors": ("sweet",), "sweetness": 0, "temps": ("hot",), "caffeine": "none", "price": 3500, "sizes": ("small", "medium"), "activities": ("relax",), "feelings": ("calm", "tired"), "popularity": 5},
    {"name": "유자차", "category": "tea", "flavors": ("sweet", "sour"), "sweetness": 2, "temps": ("hot", "ice"), "caffeine": "none", "price": 4000, "sizes": ("medium", "large"), "activities": ("relax", "dessert"), "feelings": ("calm", "refresh"), "popularity": 7},
    {"name": "페퍼민트", "category": "tea", "flavors": ("sour",), "sweetness": 0, "temps": ("hot", "ice"), "caffeine": "none", "price": 3500, "sizes": ("small", "medium"), "activities": ("study", "relax"), "feelings": ("refresh", "energetic"), "popularity": 4},
    {"name": "레몬에이드", "category": "ade_soda", "flavors": ("sour", "sweet"), "sweetness": 2, "temps": ("ice",), "caffeine": "none", "price": 4500, "sizes": ("medium", "large"), "activities": ("relax", "new", "dessert"), "feelings": ("refresh", "energetic"), "popularity": 9},
    {"name": "자몽에이드", "category": "ade_soda", "flavors": ("sour",), "sweetness": 2, "temps": ("ice",), "caffeine": "none", "price": 5000, "sizes": ("medium", "large"), "activities": ("relax", "new"), "feelings": ("refresh", "energetic"), "popularity": 8},
    {"name": "청포도에이드", "category": "ade_soda", "flavors": ("sweet", "sour"), "sweetness": 3, "temps": ("ice",), "caffeine": "none", "price": 5000, "sizes": ("medium", "large"), "activities": ("dessert", "new"), "feelings": ("refresh", "energetic"), "popularity": 6},
    {"name": "콜라/사이다", "category": "ade_soda", "flavors": ("sweet",), "sweetness": 3, "temps": ("ice",), "caffeine": "none", "price": 2500, "sizes": ("small", "medium"), "activities": ("dessert",), "feelings": ("energetic", "refresh"), "popularity": 4},
    {"name": "에스프레소 토닉", "category": "ade_soda", "flavors": ("sour", "nutty"), "sweetness": 1, "temps": ("ice",), "caffeine": "high", "price": 5500, "sizes": ("medium", "large"), "activities": ("new", "work"), "feelings": ("refresh", "tired", "energetic"), "popularity": 6},
    {"name": "아인슈페너", "category": "coffee", "flavors": ("nutty", "sweet"), "sweetness": 2, "temps": ("ice", "hot"), "caffeine": "high", "price": 6200, "sizes": ("medium", "large"), "activities": ("new", "dessert", "relax"), "feelings": ("refresh", "calm"), "popularity": 5},
    {"name": "대용량 아이스티", "category": "tea", "flavors": ("sweet", "sour"), "sweetness": 2, "temps": ("ice",), "caffeine": "low", "price": 2800, "sizes": ("large",), "activities": ("study", "relax"), "feelings": ("refresh", "energetic"), "popularity": 6},
]

CATEGORIES = {
    "coffee": "커피",
    "non_coffee": "논커피",
    "tea": "차",
    "ade_soda": "에이드·탄산음료",
}
FLAVORS = {"sweet": "달콤한 맛", "sour": "상큼한 맛", "nutty": "고소한 맛"}
BUDGETS = {
    "3,000원 이하": "under_3000",
    "3,000~4,500원": "3000_4500",
    "4,500~6,000원": "4500_6000",
    "6,000원 이상": "over_6000",
}

SURVEY = {
    "taste": {
        "title": "취향 바탕 추천",
        "questions": [
            {"id": "category", "text": "지금 어떤 종류의 음료를 마시고 싶나요?", "multi": True,
             "options": [("coffee", "커피"), ("non_coffee", "논커피"), ("tea", "차"), ("ade_soda", "에이드·탄산음료")]},
            {"id": "flavor", "text": "어떤 맛을 선호하나요?", "multi": True,
             "options": [("sweet", "달콤한 맛"), ("sour", "상큼한 맛"), ("nutty", "고소한 맛")]},
            {"id": "sweetness", "text": "단맛은 어느 정도가 좋나요?", "multi": False,
             "options": [(0, "단맛 없이"), (1, "은은하게 달콤하게"), (2, "적당히 달콤하게"), (3, "많이 달콤하게")]},
            {"id": "temperature", "text": "어떤 온도의 음료를 원하나요?", "multi": False,
             "options": [("ice", "차가운 음료"), ("hot", "따뜻한 음료"), ("any", "둘 다 괜찮음")]},
        ],
    },
    "mood": {
        "title": "기분 바탕 추천",
        "questions": [
            {"id": "activity", "text": "어떤 일을 하고 있나요?", "multi": False,
             "options": [("study", "공부하거나 과제하기"), ("relax", "휴식하고 기분 전환하기"),
                         ("work", "일하거나 집중하기"), ("dessert", "디저트와 함께 즐기기"),
                         ("new", "새로운 메뉴 경험하기")]},
            {"id": "feeling", "text": "지금 기분은 어떤가요?", "multi": False,
             "options": [("tired", "피곤하고 졸림"), ("refresh", "기분전환이 필요함"),
                         ("energetic", "상쾌하고 활기참"), ("calm", "편안하고 차분함")]},
            {"id": "caffeine", "text": "카페인이 필요한가요?", "multi": False,
             "options": [("high", "잠을 깨거나 집중하고 싶음"), ("low", "카페인이 조금 있으면 좋음"),
                         ("none", "카페인이 없는 음료를 원함"), ("any", "상관 없음")]},
        ],
    },
    "budget": {
        "title": "구매 조건 바탕 추천",
        "questions": [
            {"id": "price", "text": "얼마의 음료를 원하나요?", "multi": False,
             "options": [("under_3000", "3,000원 이하"), ("3000_4500", "3,000~4,500원"),
                         ("4500_6000", "4,500~6,000원"), ("over_6000", "6,000원 이상")]},
            {"id": "size", "text": "음료의 양은 어느 정도가 좋나요?", "multi": False,
             "options": [("small", "작은 사이즈"), ("medium", "보통 사이즈"),
                         ("large", "큰 사이즈"), ("any", "상관없음")]},
        ],
    },
}

CATEGORY_LABEL = {"coffee": "커피", "non_coffee": "논커피", "tea": "차", "ade_soda": "에이드·탄산음료"}
SIZE_LABEL = {"small": "작은", "medium": "보통", "large": "큰"}
CAFFEINE_LABEL = {"none": "없음", "low": "약간", "high": "많음"}
PRICE_RANGES = {
    "under_3000": (0, 3000), "3000_4500": (3000, 4500),
    "4500_6000": (4500, 6000), "over_6000": (6000, 10**9),
}
WEIGHTS = {
    "category": 3.0, "flavor": 2.0, "sweetness": 2.0, "temperature": 2.0,
    "activity": 1.5, "feeling": 1.5, "caffeine": 3.0, "price": 3.0, "size": 1.5,
}
STRICT = {"category", "temperature", "caffeine", "price", "size"}
FEELING_CAFFEINE_HINT = {"tired": "high", "calm": "low"}
REASON_TEXT = {
    "category": "원하는 음료 종류", "flavor": "선호하는 맛", "sweetness": "원하는 단맛 정도",
    "temperature": "원하는 온도", "activity": "지금 하는 일에 어울림", "feeling": "현재 기분에 어울림",
    "caffeine": "카페인 조건", "price": "예산 범위", "size": "원하는 사이즈",
}


def _as_list(value):
    if value is None or value == "" or value == []:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def _is_answered(key, value):
    values = _as_list(value)
    return bool(values) and not (
        key in ("temperature", "caffeine", "size") and values == ["any"]
    )


def _score_one(key, value, item):
    values = _as_list(value)
    if key == "category":
        return 1.0 if item["category"] in values else 0.0
    if key == "flavor":
        return len(set(values) & set(item["flavors"])) / len(set(values))
    if key == "sweetness":
        return max(0.0, 1.0 - abs(int(values[0]) - item["sweetness"]) / 3)
    if key == "temperature":
        return 1.0 if values[0] in item["temps"] else 0.0
    if key == "activity":
        return 1.0 if values[0] in item["activities"] else 0.0
    if key == "feeling":
        score = 1.0 if values[0] in item["feelings"] else 0.0
        caffeine_hint = FEELING_CAFFEINE_HINT.get(values[0])
        if caffeine_hint and item["caffeine"] == caffeine_hint:
            score = min(1.0, score + 0.3)
        return score
    if key == "caffeine":
        wanted = values[0]
        if wanted == "none":
            return 1.0 if item["caffeine"] == "none" else 0.0
        if wanted == "high":
            return {"high": 1.0, "low": 0.4, "none": 0.0}[item["caffeine"]]
        if wanted == "low":
            return {"low": 1.0, "high": 0.5, "none": 0.3}[item["caffeine"]]
    if key == "price":
        low, high = PRICE_RANGES[values[0]]
        price = item["price"]
        if low <= price <= high:
            return 1.0
        gap = low - price if price < low else price - high
        return max(0.0, 1.0 - gap / 3000)
    if key == "size":
        return 1.0 if values[0] in item["sizes"] else 0.0
    return 0.0


def _flatten_answers(answers):
    preferences = {}
    for section in ("taste", "mood", "budget"):
        for key, value in (answers.get(section) or {}).items():
            if key in WEIGHTS and _is_answered(key, value):
                preferences[key] = value
    return preferences


def recommend(menu, answers, top_n=5):
    preferences = _flatten_answers(answers or {})
    if not preferences:
        ranked = sorted(menu, key=lambda item: -item.get("popularity", 0))[:top_n]
        return {
            "answered": [],
            "mode": "popular",
            "results": [
                {"item": item, "score": None, "reasons": ["인기 메뉴"], "relaxed": False, "unmet": []}
                for item in ranked
            ],
        }

    max_total = sum(WEIGHTS[key] for key in preferences)
    ranked = []
    for item in menu:
        total = 0.0
        reasons = []
        unmet = []
        for key, value in preferences.items():
            score = _score_one(key, value, item)
            total += WEIGHTS[key] * score
            if score >= 0.99:
                reasons.append(REASON_TEXT[key])
            elif key in STRICT and score < 0.5:
                unmet.append(REASON_TEXT[key])
        ranked.append({
            "item": item,
            "score": round(total / max_total * 100, 1),
            "reasons": reasons,
            "unmet": unmet,
            "relaxed": bool(unmet),
        })

    order = lambda result: (-result["score"], -result["item"].get("popularity", 0))
    matching = sorted((result for result in ranked if not result["unmet"]), key=order)
    relaxed = sorted((result for result in ranked if result["unmet"]), key=order)
    return {
        "answered": sorted(preferences),
        "mode": "personalized",
        "results": (matching + relaxed)[:top_n],
    }
