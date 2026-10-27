# Linkprice 영업 지원 시스템 ( NAVER )

네이버 가격비교 카테고리별 시장현황과 광고 전략을 탐색하는 **GitHub Pages 배포용 정적 웹앱 + 서버 없는 예약 배치**입니다.

## 현재 버전에서 바로 작동하는 기능

- 정식으로 확인된 **네이버 최상위 12개 대분류 코드**와 **초기 탐색용 209개 편집형 중분류 예시** 제공
- 카테고리명 실시간 검색, 대분류 필터, 페이징, 즐겨찾기
- 업종/카테고리별 **네이버 SA** 및 **네이버 GFA** 운영 기회와 주의사항, 퍼널 설계
- GFA 인지도·트래픽 → SA 검색 수요 포착 → GFA 카탈로그 판매 기반 리타겟팅 → 구매완료 성과 개선
- 콜영업 스크립트는 **비어 있는 입력란**으로 제공하며 카테고리별 직접 작성/브라우저 저장/복사/JSON 백업
- 시장지표가 없는 경우 임의의 숫자를 표시하지 않음
- 네이버 커머스 전체 카테고리 CSV/JSON 업로드, CSV 내보내기

> **중요 — 분류 완전성:** 첨부 시점에는 네이버 커머스 API 인증이 없어 **공식 전체 중분류를 실제로 가져오지 못했습니다.** 209개 편집형 중분류는 검색 화면 동작을 위한 **예시**이며, 네이버의 공식 전체 중분류와 일치함을 보증하지 않습니다. `NAVER_COMMERCE_CLIENT_ID`/`SECRET`을 등록하고 자동 업데이트를 실행하면 공식 전체 카테고리 API에서 목록을 받아와 대·중분류를 정리합니다. 데이터가 불완전할 경우 기존 자료를 덮어쓰지 않습니다.

## 빠른 배포 — GitHub Pages

1. 이 ZIP의 모든 파일 및 숨김 폴더 `.github`를 새 GitHub 저장소 루트에 업로드합니다.
2. GitHub 저장소 → **Settings → Pages** → `Deploy from a branch`, `main`, `/ (root)`로 설정합니다.
3. 발급된 `https://계정.github.io/저장소/`로 접속합니다.
4. 초기 버전은 API 키가 없어도 작동합니다. 브라우저에서 `index.html` 파일을 바로 열어도 예시 카테고리 목록은 표시됩니다.

## 공식 API 연동 (선택적이며 API 자격이 있어야 가능)

GitHub → **Settings → Secrets and variables → Actions** → **New repository secret**에 아래 값을 개별 저장합니다. **HTML/JS/JSON에 API 비밀키를 절대 넣지 마세요.**

| Secret | 용도 | 발급 사이트 |
|---|---|---|
| `NAVER_COMMERCE_CLIENT_ID` | 네이버 공식 전체 카테고리 조회 | https://apicenter.commerce.naver.com |
| `NAVER_COMMERCE_CLIENT_SECRET` | 네이버 커머스 OAuth bcrypt 서명 | 같은 사이트 |
| `NAVER_DATALAB_CLIENT_ID` | 네이버 쇼핑 클릭 추이 | https://developers.naver.com |
| `NAVER_DATALAB_CLIENT_SECRET` | 쇼핑인사이트 API 인증 | 같은 사이트 |
| `OPENAI_API_KEY` | 선택된 업종의 AI 요약 생성 (유료, 선택) | https://platform.openai.com/api-keys |

- **Actions → NAVER market and category refresh → Run workflow**를 누르면 즉시 수동 실행됩니다.
- 이후 GitHub Actions가 **매일 06:40 KST(UTC 21:40)**에 실행하도록 예약되어 있습니다. GitHub Actions 스케줄은 지연될 수 있습니다.
- 네이버 커머스 API 인증에 대한 이용 권한이 없으면 공식 카테고리 조회가 실패합니다. 해당 권한은 네이버 커머스 API 센터에서 확인하세요.
- 마켓 트렌드 기본 조회 대상은 **최상위 분류 + 선택된 중분류를 우선**하고, 나머지를 포함해 **최대 180개**입니다. `MAX_TREND_CATEGORIES` 환경변수로 조절할 수 있지만 API 호출 제한과 비용/속도를 고려하세요.
- 쇼핑인사이트 결과는 **클릭량 상대지수**이고 시장 매출·검색량·실제 광고 전환을 뜻하지 않습니다.
- OpenAI 분석은 비용 관리를 위해 기본 **12개 업종만** 처리하며 `MAX_AI_CATEGORIES`로 조절합니다. `OPENAI_WEB_SEARCH=1`이면 유료 웹 검색을 켭니다. 웹 검색을 켜지 않으면 시계열 데이터/가설만 사용하며 최신 뉴스라고 표현하지 않습니다.
- 발급한 API 키를 대화창, 웹 페이지 또는 커밋에 올리지 마세요.

**자동화 구성**

```
.github/workflows/refresh.yml
 ├─ scripts/sync_categories.py   # 정식 네이버 커머스 전체 분류 GET /v1/categories
 ├─ scripts/sync_market.py       # 네이버 쇼핑인사이트 POST /shopping/categories
 ├─ scripts/sync_ai.py           # OpenAI Responses API, 옵션
 └─ data/*.json                  # 갱신 결과 정적 사이트에 반영
```

## 대량 카테고리 관리

- 공식 연동을 하지 않아도 **데이터 센터 → 카테고리 CSV/JSON 불러오기**로 전체 카테고리를 즉시 등록할 수 있습니다.
- 네이버 커머스 API의 JSON 원본 배열 `[{"id":"...","wholeCategoryName":"대분류>중분류>소분류",...}]` 또는 `{"categories":[...]}` 형태 지원.
- CSV는 `id,wholeCategoryName` 또는 `대분류,중분류` 형태 지원.
- 업로드는 **해당 브라우저에만 적용**됩니다. 그룹 전체 공유를 원하면 `data/categories.json`을 갱신해 저장소에 반영해야 합니다.
- 하위 분류를 많이 읽어 오더라도 UI에서 **대·중분류만 표시**하고 검색·페이지 분할 처리합니다.

## 영업 노트의 저장 방식 및 보안

- 모든 스크립트 입력값은 브라우저의 `localStorage`에 저장됩니다. 다른 사람, 다른 기기나 브라우저로 자동 공유되지 않습니다.
- JSON 다운로드/복원으로 이동할 수 있으나 **개인정보, 광고주 비밀정보, API 키**는 작성하지 마세요.
- **GitHub Pages 기본 배포 URL은 일반적으로 공개됩니다.** 내부 전용 시스템으로 쓰려면 인증된 호스팅/접근제어를 추가해야 합니다. HTML에 로그인 폼만 붙이는 것으로는 보호되지 않습니다.

## 다음 고도화 단계

1. 실제 API 발급·권한 확인 후 **공식 중분류 전체 동기화** 성공 테스트
2. 쇼핑인사이트 API 1,000회/일 등 제한을 고려해 **증분 업데이트 및 대량 배치**
3. 네이버 광고 성과 보고서/API 데이터와 합산해 업종별 CPC·CVR·ROAS 통계 (광고주 내부 데이터는 인증된 저장소로)
4. 그룹원 계정·권한·공동 스크립트 관리 (Supabase 또는 보호된 백엔드)
5. AI 결과 검수/승인·근거 URL·수정 기록·분석 신뢰도 표기

## 데이터 출처

- 네이버 커머스 전체 카테고리 API: https://apicenter.commerce.naver.com/docs/commerce-api/current/get-category-list-product
- 네이버 공식 쇼핑인사이트: https://developers.naver.com/docs/serviceapi/datalab/shopping/shopping.md
- 네이버 광고주센터: https://ads.naver.com/
- 네이버 카탈로그 판매: https://ads.naver.com/help/faq/1379
- OpenAI Responses API: https://platform.openai.com/docs/api-reference/responses

상단 출처는 **해당 정보를 가져올 공식 연결 경로**입니다. 초기 예시 중분류나 정성적 광고 전략을 네이버가 직접 제공하는 사실 데이터로 오인하지 마세요.
