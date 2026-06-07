# 지역 기반 로컬 비즈니스 사이트 — 재사용 블루프린트 v2

> 이 문서는 **굿데이 강서 출장마사지**(gangseo-massage.pages.dev) 프로젝트에서
> 실제로 만든 메뉴 구조·다크 럭스 디자인·지역 페이지 템플릿·**도어웨이 회피 방법**·
> 구글 가이드라인 준수 패턴·색인 자동화를 **다음 프로젝트에 그대로 이식**하기 위한
> 실전 플레이북입니다. 모든 항목은 `tools/build.py`의 실제 구현 기준입니다.

핵심 철학: **순수 HTML + 인라인 CSS/JS(의존성 0) + Python 단일 생성기 + 전용 페이지 링크아웃**
= 빌드 도구 없음 / LCP 빠름 / E-E-A-T 충족 / 도어웨이 회피.

---

## 0. 기술 스택 / 아키텍처

| 항목 | 값 |
|---|---|
| 출력물 | 순수 정적 HTML (페이지당 단일 파일, 인라인 CSS/JS) |
| 런타임 의존성 | 0개 (외부 폰트·JS·CSS 요청 없음) |
| 생성기 | `tools/build.py` (Python 3, 표준 라이브러리만) |
| 아이콘/OG | `tools/gen_icons.py` (Pillow) — 파비콘·PWA·OG 1200×630 |
| 색인 자동화 | `tools/indexnow.py`, `tools/google_indexing.py`, GitHub Actions |
| 호스팅 | Cloudflare Pages (정적, repo 연결 자동배포) |
| 총 페이지 | 40 (홈1·소개1·강서대표1·지역허브1·권역5·동12·코스8·예약/가이드/후기/고객센터4·정책3·강서안내4) |

**왜 단일 Python 생성기인가**: 헤더/푸터/SEO/스키마를 한 곳에서 관리 → 40페이지 일관성.
출력은 순수 HTML이라 배포에 빌드 불필요. 공통 수정 시에만 `python3 tools/build.py`.

```
tools/build.py        # 전체 사이트 생성 (핵심)
tools/gen_icons.py    # 브랜드 이미지 생성
tools/indexnow.py     # 빙·네이버 즉시 색인 통보
tools/google_indexing.py
.github/workflows/indexnow.yml   # 푸시 시 자동 색인 통보
```

---

## 1. 메뉴 구조 (지역 SEO 핵심)

### 1.1 띄어쓰기 규칙
- 사용자는 **"강서 출장마사지"**(띄어쓰기)로 검색 → 브랜드·메뉴·H1·Title 모두 띄어쓰기 형.
- 피할 것: `강서출장마사지추천`, `강서출장마사지24시` 같은 키워드 결합형 메뉴명(인위적 스팸 신호).

### 1.2 상단 메뉴 (권역→동 3단 드롭다운)
```
홈
굿데이 소개      ├ 인사말 · 운영기준 · 위생관리 · FAQ
강서 출장마사지   ├ 안내 · 가능지역 · 예약시간 · 코스선택 · 확인사항 · 위생안전 · FAQ
지역별 안내       ├ 강서 출장마사지(→대표) · 강서구 출장 가능 지역(→허브)
                 ├ 염창·등촌권역 → 염창동 / 등촌동
                 ├ 화곡·우장산권역 → 화곡동 / 우장산동
                 ├ 가양·마곡권역 → 가양동 / 마곡동
                 ├ 발산권역 → 발산동 / 내발산동 / 외발산동
                 └ 공항·방화권역 → 공항동 / 방화동 / 개화동
코스안내         ├ 전체코스 · 피로회복 · 아로마 · 스포츠 · 커플가족 · 기업단체 · 가격 · 선택가이드
예약안내 · 이용가이드 · 고객후기 · 고객센터
[24시 예약] (골드 pill, tel:)
```
- **3단 중첩 드롭다운**: 데스크톱은 우측 플라이아웃, 모바일은 들여쓰기 평탄화.
- **키워드 충돌 방지**: 상단 "강서 출장마사지"와 지역별 첫 항목 "강서 출장마사지"를 **둘 다 같은 대표 페이지 `/gangseo-gu/`로 연결** → 핵심 키워드 신호 분산 방지.

### 1.3 URL 구조
```
/                          홈
/about/                    소개
/gangseo-gu/               강서 출장마사지 대표(핵심 랜딩)
/gangseo-gu/area/          지역 허브
/gangseo-gu/<권역>-area/    권역 5
/gangseo-gu/<동>-dong/      동 12
/gangseo-gu/hours|checklist|safety|faq/   강서 안내 4 (공통 정보 전용 페이지)
/course/                   코스 허브
/course/<slug>/            코스 7 (fatigue·aroma·sports·couple·group·price·guide)
/reservation/ /guide/ /reviews/ /customer/
/privacy/ /terms/ /youth/  정책 3
```
- **행정동 통합**: 화곡1~8동·방화1~3동·등촌1~3동 등 숫자 행정동은 **별도 페이지 금지** →
  대표 동 본문 H3·FAQ에서 흡수(도어웨이 회피). 역명(염창역 등)도 별도 페이지 금지, 본문 H3로 흡수.

---

## 2. 디자인 시스템 — 다크 럭스 스파

### 2.1 컬러 토큰
```css
:root{
  --bg:#0b0b0e; --surface:#13131a; --surface-2:#1a1a23; --line:rgba(255,255,255,.08);
  --text:#f3f3f5; --muted:#9a9aa3; --dim:#6c6c75;
  --gold:#d6b274; --rose:#e9b8a7; --copper:#c98a6b;
  --grad:linear-gradient(135deg,#f4d29c 0%,#e9b8a7 45%,#c98a6b 100%);
  --grad-soft:linear-gradient(135deg,rgba(244,210,156,.14),rgba(201,138,107,.06));
}
```
업종 전환 시 `--gold/--rose/--copper/--grad`만 교체(의료=쿨블루, 친환경=세이지 등).

### 2.2 폰트 (시스템 폰트 우선 — 다운로드 0)
```css
body{font-family:"Pretendard","Apple SD Gothic Neo","Noto Sans KR",system-ui,...;
  line-height:1.65; letter-spacing:-.01em}
.serif{font-family:"Cormorant Garamond","Noto Serif KR",Georgia,serif;font-style:italic} /* 숫자·강조 */
```

### 2.3 다크 럭스 지역 페이지 레이아웃 (핵심)
첨부 콘셉트 "다크 네이비 + 골드 + 좌측 고정 TOC + 높은 대비"를 본문까지 확장.
```css
/* 좌측 고정 목차 + 네이비 패널 */
.lux-grid{display:grid;grid-template-columns:240px 1fr;gap:46px;align-items:start}
.toc{position:sticky;top:86px}
.toc li a.active{color:var(--gold);border-left:2px solid var(--gold);background:rgba(244,210,156,.09)}
.lux-sec{background:linear-gradient(165deg,#121626,#0c0e16);border:1px solid rgba(255,255,255,.08);
  border-radius:18px;padding:28px 32px;margin-bottom:18px;position:relative}
.lux-sec::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--grad)} /* 골드 액센트 바 */
.lux-sec h2{color:#fff;font-weight:800}        /* 흰색 제목 = 고대비 */
.lux-sec h3{color:var(--gold)}                  /* 골드 소제목 */
.lux-sec p{color:#e4e5ec;line-height:1.9}       /* 밝은 본문 = 가독성 */
.lux-sec>ul li{padding-left:22px;border-bottom:1px solid rgba(255,255,255,.06)} /* 골드 도트+구분선 */
.lux-hero{background:radial-gradient(70% 120% at 88% -10%,rgba(233,184,167,.14),transparent),
          linear-gradient(180deg,#0d1018,#0b0b0e)}
@media(max-width:980px){.lux-grid{grid-template-columns:1fr}.toc{position:static} /* TOC→가로 칩 */}
```
- **TOC 스크롤 스파이**: IntersectionObserver로 현재 섹션을 골드 하이라이트(JS는 idle 로드).

### 2.4 재사용 컴포넌트
- **노트/패널 카드**: 좌측 3px 골드 바 + 호버 시 상승.
- **가격 카드**: 60·90·120분 시간 기준 `.pmenu`(90분 BEST 골드 강조).
- **FAQ**: 네이티브 `<details>` → JS 불필요, `FAQPage` 스키마와 1:1.
- **플로팅 전화예약 버튼**(전 페이지 고정): 오렌지(`#ff7a18`) + 전화 아이콘 흔들림 + 펄스링.
```css
.call-fab{position:fixed;right:20px;bottom:20px;z-index:90;background:linear-gradient(135deg,#ffa23c,#ff7a18,#f4600a)}
.call-fab-ic{animation:fabring 1.5s ease-in-out infinite}     /* 흔들림 */
.call-fab::before{border:2px solid #ff7a18;animation:fabpulse 1.8s infinite} /* 펄스링 */
@media(max-width:560px){.call-fab-tx{display:none}}            /* 모바일=아이콘만 */
@media(prefers-reduced-motion:reduce){.call-fab-ic,.call-fab::before{animation:none}}
```

### 2.5 성능 (Core Web Vitals)
- 모든 CSS/JS/아이콘 인라인 → 외부 요청 0.
- `content-visibility:auto` (화면 밖 섹션), 시스템 폰트(FOIT/FOUT 0).
- 비크리티컬 JS는 `requestIdleCallback`, `prefers-reduced-motion`/`@media(hover:none)` 대응.

---

## 3. 지역(동) 페이지 템플릿 — "염창동 구조"

모든 동 페이지가 동일 골격, **동 고유 데이터만 주입**.

```
H1: OO동 출장마사지 예약 안내
첫 문단(lead): "강서구 OO동(성격)에서 방문 마사지 예약을 찾는 분들을 위한 안내…
               OO동은 {역들} 인근 생활권과 가까워… 평균 N분 내외 도착."
상단 CTA: [예약문의] [코스안내] [강서 대표] [인접 동]
저자 표기(byline): 작성·굿데이 운영팀 | 감수·대표 | 최종 업데이트 날짜

H2 1. OO동 출장마사지 이용 안내   (동 성격·랜드마크 + 예약안내/이용가이드 링크)
H2 2. OO동 방문 가능 생활권        ← 동 고유 핵심
       · 방문 포인트별 평균 도착시간(역별 N분 — 1차 데이터)
       · H3 역/지역별(염창역·증미역…) + 주거지·숙소 방문 안내
H2 3. (권역) 함께 보기             (내부링크: 강서대표·가능지역·권역·인접동)
H2 4. OO동에서 많이 찾는 관리 코스  (1문장 + /course/* 링크 ← 상세 반복 금지)
H2 5. OO동 예약·준비·위생 안내      (1문장 + hours/checklist/safety/price 링크아웃)
FAQ: 5문항 — 전부 동명·역명·성격·도착시간 반영(고유)
CTA: "OO동 방문 예약, 지금 도와드릴까요?" (동 맞춤)
```

**동별 데이터 모델** (`DONG_ZONES` 등):
```python
{"slug":"yeomchang-dong","name":"염창동","arrival":28,
 "landmarks":"염창역(9호선), 한강공원, 강서한강자이 일대",
 "character":"한강 조망 아파트 단지가 밀집한 정주형 주거 권역",
 "sub_note": "...(선택) 행정동 통합 안내..."}
DONG_ZONES["yeomchang-dong"]=[("염창역 인근","9호선 염창역 중심 …"),("증미역 인근","…"),…]
```
- `character`·`landmarks`·`arrival`·`zones`가 페이지마다 달라 **고유성**을 만든다.
- 역명은 `zones`의 H3와 FAQ에서만 다룸(별도 페이지 X).

---

## 4. 도어웨이 회피 방법 (가장 중요) ★

지역 페이지는 "지역명만 바꾼 대량 복제"로 보이면 도어웨이 판정 위험. 아래로 **차단**.

### 4.1 측정 방법 (4-gram 자카드 유사도)
```python
def main_text(f):   # 헤더/푸터 제외한 본문 텍스트만
    h=open(f).read().split('</header>')[1].split('<footer')[0]
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',h)).strip()
def shingles(t,n=4): k=t.split(); return {tuple(k[i:i+n]) for i in range(len(k)-n+1)}
def sim(a,b): A,B=shingles(a),shingles(b); return len(A&B)/len(A|B)
```
페이지 그룹 내 **쌍별 평균/최대 유사도**를 측정. 목표: **40% 안팎 이하**.

### 4.2 우리가 적용한 차단 기법 (68% → 38%)
1. **링크아웃 아키텍처(핵심)**: 예약시간·준비물·위생·코스·가격처럼 **전용 페이지가 있는 공통 정보는
   동/권역 본문에서 반복하지 말고 링크만** 건다(`/gangseo-gu/hours|checklist|safety/`, `/course/*`).
   → 반복 블록 자체를 제거해 유사도 급감.
2. **고유 1차 데이터 주입**: 생활권 역별 평균 도착시간(동마다 다른 분), `character`, `landmarks`를
   lead·이용안내·코스·FAQ·CTA에 반영.
3. **고유 FAQ**: 5문항 전부 동명/역명/성격/도착시간 포함(공통 답변 최소화).
4. **공통 문장도 동명으로 차별화**: 남는 안내 문장 도입부에 동명·랜드마크 삽입.
5. **동 맞춤 CTA 제목**.
6. **행정동·역명 페이지 양산 금지**: 통합 흡수.

### 4.3 "정당한 공통 콘텐츠"는 허용
내비게이션·정책 고지·전용 페이지 링크·CTA·저자표기·가격표는 반복돼도 OK(구글이 명시적으로 허용).
**핵심 판정 기준 = 각 페이지에 고유 가치가 있는가** → 생활권/도착/성격/FAQ로 충족.

### 4.4 운영 권장
- **단계적 색인**: 검색 수요 큰 동부터 Search Console 제출 후 확장.
- 지리적으로 거의 같은 인접 동(예: 내·외발산동)이 계속 높으면 **권역 1페이지로 통합** 고려.
- **동을 무한정 늘리지 말 것**(12개 적정). 역명 페이지 추가는 금물.

---

## 5. 메인 페이지 + 허브 구성

**메인 `/`**: HERO(글래스 예약카드+플로팅칩) → 마키 → 대표 코스 4 → **코스별 기본 요금** →
권역 5 카드 → 진행 4단계 → 후기 3 → About(WHO·HOW·WHY 노트, E-E-A-T) → FAQ6 → 최종 CTA → 5단 푸터.

**강서 대표 `/gangseo-gu/`** (핵심 랜딩, 키워드 집중):
H1 "강서 출장마사지 예약 안내" + H2 8단(안내·가능지역·주요생활권·많이찾는코스·예약시간·이용전확인·위생안전·FAQ).
키워드는 Title·H1·첫문단·FAQ 1곳에만(반복 금지).

**지역 허브 `/gangseo-gu/area/`**: 권역→동 2단 카드 그리드, `CollectionPage` 스키마.

**권역 페이지**: 동 카드 그리드 + 동별 고유 라인(성격·랜드마크·도착) + 전용 안내 링크아웃(동과 동일 럭스 레이아웃).

**가격 노출**: 코스별 기본 요금(60/90/120분, 90분 BEST)은 홈·강서대표·허브·코스에 노출.
동/권역 본문에는 **반복 금지** → `/course/price/` 링크(도어웨이 회피와 양립).

---

## 6. SEO · E-E-A-T · 구글 가이드라인 준수

### 6.1 모든 페이지 공통
- `title`·`description`·`canonical` **100% 고유**(절대 URL).
- meta robots(`max-image-preview:large` 등), OG/Twitter(절대 og:image 1200×630), `author`, hreflang ko-KR/x-default.
- **Breadcrumb 전 페이지** + `BreadcrumbList` 구조화 데이터(구글이 탐색경로로 분류에 사용).
- 파비콘 5종 + `site.webmanifest`.

### 6.2 JSON-LD (페이지 타입별)
| 페이지 | 스키마 |
|---|---|
| 홈 | Organization·WebSite·LocalBusiness(HealthAndBeautyBusiness)·OfferCatalog·FAQPage |
| 코스/안내 | Article·Service·OfferCatalog·FAQPage·BreadcrumbList |
| 동/권역 | Article·Service·LocalBusiness·OfferCatalog·FAQPage·BreadcrumbList |
| 허브 | CollectionPage·BreadcrumbList |
| 후기 | ItemList·Review |
- **FAQ 스키마는 실제 페이지에 보이는 Q/A만**(없는 내용 금지).
- **LocalBusiness는 실제 사업자 정보(상호·주소·전화·영업시간)가 사실일 때만**.

### 6.3 E-E-A-T 신호 (YMYL 대응)
- **Experience**: 현장 운영 메모(권역별 도착시간·예약 시간대 = 1차 데이터).
- **Authoritativeness/Trust**: 저자·감수 byline, 푸터 사업자 6필드(상호·대표·사업자번호·주소·통신판매신고·개인정보책임자).
- **Who/How/Why**: About 페이지 + 운영 원칙 명시. AI 사용 여부보다 결과물 가치·책임 저자가 핵심.
- **합법 고지**: "의료 행위 아닌 건강관리·이완 목적", "만 19세 이상", 정책 3종(개인정보·약관·청소년보호).

### 6.4 도움되는 콘텐츠 / 스팸 정책 대응
- 본문은 어디서나 보는 요약이 아닌 **지역 1차 정보**(정보 이득) 중심.
- 금지: 대량 저가치 양산, 키워드 스터핑, 클로킹, 링크스킴, **도어웨이**(§4로 차단).
- 본문 분량 가이드: 동/코스 페이지 ≈ 1,800~2,800자(억지 패딩 금지, 실질 정보로).

### 6.5 robots.txt / sitemap.xml
```
User-agent: *  Allow: /   Disallow: /tools/
User-agent: GPTBot/ClaudeBot/Google-Extended  Allow: /
Sitemap: https://<도메인>/sitemap.xml
```
sitemap 우선순위: `/` 1.0, 카테고리 0.8~0.9, leaf 0.75.

---

## 7. 색인 즉시 통보 (자동화)

### 7.1 IndexNow (빙·네이버·얀덱스, 무료·무설정) — 권장
- 빌드 시 인증 키 파일 `<KEY>.txt` 자동 생성(루트 노출). 상수 `INDEXNOW_KEY`.
- `tools/indexnow.py --all | --changed | <URL> [--dry-run]` (단일 엔드포인트 → 참여 엔진 전파, 의존성 0).
- `.github/workflows/indexnow.yml`: **main 푸시(페이지/사이트맵 변경) 시 자동 제출**(시크릿 불필요).
- 네이버 서치어드바이저에 사이트 등록 + IndexNow 사용 설정 1회.

### 7.2 Google Indexing API (보조)
- `tools/google_indexing.py` (서비스계정 + google-auth). CI 시크릿 `GOOGLE_INDEXING_SA`로 연동.
- ⚠️ **공식 지원은 JobPosting/BroadcastEvent 한정** → 일반 페이지는 Search Console+sitemap이 정공법.

### 7.3 sitemap ping
- **구글·빙 ping 엔드포인트는 2023년 폐지(404)**. 대신 Search Console/Bing Webmaster에 sitemap 1회 제출 + IndexNow로 대체.

---

## 8. 다음 프로젝트 재사용 워크플로

1. 이 문서 + `tools/build.py`를 새 repo로 복사.
2. **상수 교체**: `BASE_URL`(도메인)·`BRAND`·`PHONE_*`·`COMPANY`·`INDEXNOW_KEY`(새로 생성).
3. **컬러 토큰** `--gold/--rose/--copper/--grad`만 업종에 맞게 교체.
4. **데이터 모델 정의**: `REGIONS`(권역·동·landmarks·character·arrival)·`DONG_ZONES`·`COURSES`.
5. `python3 tools/build.py` → 40+페이지 일괄 생성, `gen_icons.py` → 브랜드 이미지.
6. **도어웨이 점검**: §4.1 스크립트로 동/권역 유사도 측정 → 40% 이하 확인(아니면 §4.2 적용).
7. **무결성 점검**: 제목 고유·JSON-LD 0오류·broken link 0(아래 스니펫).
8. Cloudflare Pages 연결, Search Console/네이버/Bing 등록, sitemap 제출.
9. IndexNow 워크플로 동작 확인.

**무결성 점검 스니펫**:
```python
# 제목 중복 / JSON-LD 파싱 / broken link 0 확인
import re,glob,json
for f in glob.glob('**/index.html',recursive=True):
    h=open(f,encoding='utf-8').read()
    for m in re.findall(r'application/ld\+json">(.*?)</script>',h,re.S): json.loads(m)  # 예외=오류
```

---

## 9. 핵심 체크리스트 (배포 전)

```
[ ] title/description/canonical 100% 고유(절대 URL)
[ ] JSON-LD 전부 파싱 유효, FAQ는 화면에 보이는 것만
[ ] Breadcrumb 전 페이지 + BreadcrumbList
[ ] 동/권역 유사도 ≤ ~40% (도어웨이 회피)  ← §4
[ ] 공통 정보는 전용 페이지로 링크아웃(반복 금지)
[ ] 역명·숫자 행정동 별도 페이지 없음(본문 흡수)
[ ] 실제 전화번호 + (이메일 쓰면 실제), placeholder 0
[ ] 사업자 6필드 푸터 + 비의료·19세 고지 + 정책 3종
[ ] LocalBusiness는 실제 정보일 때만
[ ] 시스템 폰트·인라인·content-visibility(LCP)
[ ] 플로팅 전화 버튼 전 페이지
[ ] IndexNow 키 파일 도메인에서 열림 + 워크플로 동작
[ ] robots.txt + sitemap.xml + Search Console/네이버/Bing 등록
```

> 한 줄 요약:
> **순수 HTML + Python 단일 생성기 + 다크 럭스(네이비·골드·좌측 TOC) + 전용 페이지 링크아웃으로
> 도어웨이를 구조적으로 차단 + E-E-A-T/구조화 데이터 풀스택 + IndexNow 자동 색인 = 재사용 가능한 지역 SEO 사이트.**
