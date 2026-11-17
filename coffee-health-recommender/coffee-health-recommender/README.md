# 건강 기반 커피 추천 — 갤럭시 워치 연동 PoC

갤럭시 워치 데이터(Samsung Health → Health Connect)를 읽어, 사용자의 수면·심박·활동
상태에 맞는 커피 메뉴를 추천하는 기술 PoC 코드입니다.

## 데이터 흐름

```
갤럭시 워치 → Samsung Health → Health Connect(온디바이스)
   → Android 앱(Health Connect SDK로 READ)
   → '가공 feature'만 서버 전송(HTTPS)
   → FastAPI 추천 엔진 → 추천 결과
```

> 핵심 설계: 원시 건강데이터(심박 배열·수면 세션)는 폰 밖으로 내보내지 않고,
> `수면시간/평균심박/안정심박/걸음/운동분/현재시각` 같은 가공 feature만 전송.

## 파일 구성

| 경로 | 설명 |
|---|---|
| `android/AndroidManifest.xml` | Health Connect 권한(수면·심박·걸음·운동) + 개인정보처리방침 intent |
| `android/HealthRepository.kt` | Health Connect 읽기 로직 (수면/심박/걸음/운동 집계) |
| `android/RecommendApi.kt` | feature 변환 + Retrofit 통신 |
| `android/MainActivity.kt` | 권한 요청 → 데이터 수집 → 추천 표시 (Compose) |
| `android/build.gradle.kts` | 의존성 |
| `backend/main.py` | FastAPI 추천 엔진 (카페인 상한 계산 + 메뉴 매칭) |

## 실행

### 백엔드
```bash
cd backend
pip install fastapi uvicorn pydantic
uvicorn main:app --reload
# 테스트: curl -X POST localhost:8000/recommend \
#   -H "Content-Type: application/json" \
#   -d '{"sleepHours":4.5,"restingHeartRate":62,"steps":800,"exerciseMinutes":0,"localHour":8}'
```

### 앱
1. Android Studio 로 `android/` 코드를 앱 모듈에 배치
2. 테스트 기기에 **Samsung Health 설정 → Health Connect 동기화 ON**
3. 앱 실행 → "건강 데이터 연동하고 추천받기" → 권한 동의

## 출시 전 체크리스트 (중요)

- [ ] **Google Play 건강앱 심사**: 사용하는 각 Health Connect 데이터 타입의 용도를
      Play Console `App content → Health apps declaration` 에 기재. 쓰지 않는
      타입은 요청 금지(거절 사유 1순위).
- [ ] **개인정보처리방침** 화면: Health Connect 권한 화면에서 열리는 방침 =
      Play 에 제출한 방침과 동일해야 함.
- [ ] **민감정보 별도 동의**(국내 개인정보보호법): 건강정보는 일반 약관 동의로
      불가. 명시적·별도 동의 플로우 필요.
- [ ] 데이터는 추천 연산 목적에만 사용. 광고 타겟팅·제3자 판매 금지.
- [ ] 신규 개인 개발자 계정은 production 전 **12명·14일 비공개 테스트** 요건 확인.

## 추천 로직 요약 (backend/main.py)

- 기본 1일 카페인 상한 400mg(식약처/FDA)에서 상태에 따라 차감:
  수면<6h(-100), 안정심박>80(-80), 14시 이후(-100), 18시 이후(-100)
- 상황별 메뉴 매칭: 늦은시간/여력없음→디카페인, 심박높음→디카페인,
  운동직후→회복(단백질), 수면부족→적당한 각성, 그 외→무난한 선택
