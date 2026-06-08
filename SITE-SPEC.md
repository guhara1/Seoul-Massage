# Seoul 마사지 — 사이트 전체 사양서 (재사용용)

> 이 문서는 **seoul-massage-at6.pages.dev** 사이트의 디자인·메뉴·콘텐츠·푸터·SEO·
> 생성 시스템을 **한 곳에 정리**한 사양서입니다. 다른 지역/업종 사이트를 만들 때
> 이 문서의 값만 바꾸면 동일한 구조를 그대로 복제할 수 있도록 작성했습니다.
>
> (참고: `BLUEPRINT.md`는 이전 프로젝트의 범용 플레이북이고, 본 문서는 **현재 사이트의 실제 사양**입니다.)

최종 정리: 2026-06-08

---

## 0. 개요 / 기술 스택

| 항목 | 값 |
|---|---|
| 사이트명 | Seoul 마사지 (서울 출장마사지·홈타이 안내) |
| 운영 도메인 | `https://seoul-massage-at6.pages.dev` |
| 호스팅 | Cloudflare Pages (정적, GitHub repo 연결 자동배포) |
| 업종 | 지역 기반 방문 건강관리(출장마사지·홈타이) 예약 안내 |
| 출력물 | 순수 정적 HTML — 페이지당 단일 파일, **인라인 CSS/JS** (외부 의존성 0) |
| 폰트/아이콘 | 외부 폰트 요청 없음(시스템/웹폰트 fallback), 파비콘·PWA·OG 이미지는 `assets/`·루트에 보관 |
| 콘텐츠 생성기 | `tools/gen_articles.py` (Python 3 표준 라이브러리) — 매거진 글 자동 생성 |
| 색인 자동화 | `tools/indexnow.py`, `.github/` 워크플로 |
| 총 페이지 규모 | 자치구 25 · 지하철역 324 · 테마 14 · 코스 8 · 매거진 글 60 등 수백 페이지 |

**철학**: 순수 HTML + 인라인 CSS/JS + Python 단일 생성기 → 빌드 도구 불필요, LCP 빠름, 일관성 유지.

---

## 1. 사업자 / 연락처 정보 (푸터 공통)

> 새 사이트에서 **반드시 교체**해야 하는 값들입니다.

| 항목 | 값 |
|---|---|
| 상호 | YH LAB |
| 대표 | 김유환 |
| 사업자등록번호 | 815-26-00585 |
| 주소 | 경기도 파주시 청석로 268 |
| 개인정보보호책임자 | 김유환 |
| 대표 전화(예약·상담) | 0508-202-4743 → 링크 `tel:+825082024743` |
| 운영 시간 | 연중무휴 · 24시간 상담 |
| 저작권 | © 2026 YH LAB. All rights reserved. |

**법적 고지(전 페이지 푸터 고정)**
> 본 서비스는 의료 행위가 아닌 건강관리(이완·휴식) 목적의 방문 관리 서비스이며,
> 만 19세 이상 성인을 대상으로 합니다. 불법·퇴폐 행위는 일절 제공하지 않습니다.

---

## 2. 디자인 시스템 (다크 럭스)

### 2.1 색상 토큰 (`:root` CSS 변수)
```css
:root{
  --bg:#0b0b0e;          /* 배경(딥 블랙) */
  --surface:#13131a;     /* 카드 배경 */
  --surface-2:#1a1a23;   /* 카드 그라데이션 끝 */
  --line:rgba(255,255,255,.08);  /* 보더/구분선 */
  --text:#f3f3f5;        /* 본문 텍스트 */
  --muted:#9a9aa3;       /* 보조 텍스트 */
  --dim:#6c6c75;         /* 흐린 텍스트(날짜 등) */
  --gold:#d6b274;        /* 강조 골드 */
  --rose:#e9b8a7;        /* 포인트 로즈 */
  --copper:#c98a6b;      /* 코퍼 */
  --grad:linear-gradient(135deg,#f4d29c 0%,#e9b8a7 45%,#c98a6b 100%);     /* 메인 그라데이션(버튼·강조) */
  --grad-soft:linear-gradient(135deg,rgba(244,210,156,.14),rgba(201,138,107,.06)); /* 연한 배경 */
}
```
- `theme-color` / PWA `theme_color`·`background_color`: `#0b0b0e`

### 2.2 폰트
| 용도 | font-family |
|---|---|
| 본문(산세리프) | `"Pretendard","Apple SD Gothic Neo","Noto Sans KR",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif` |
| 장식(세리프·이탤릭) | `"Cormorant Garamond","Noto Serif KR",Georgia,serif` (`.serif`, 숫자 강조 등) |
- 본문 기본: `line-height:1.65; letter-spacing:-.01em`

### 2.3 핵심 컴포넌트 클래스
| 클래스 | 용도 |
|---|---|
| `.wrap` | 콘텐츠 컨테이너 `max-width:1240px; padding:0 24px` |
| `header` + `.nav` `.brand` `.menu` `.submenu` `.sub2` | 스티키 헤더 + 2뎁스 드롭다운 메뉴 |
| `.eyebrow` + `.pulse` | 섹션 상단 골드 라벨 + 점멸 점 |
| `.btn` `.btn-primary` `.btn-ghost` | 버튼(그라데이션 / 고스트) |
| `.grid` `.g2` `.g3` `.g4` | 반응형 카드 그리드(`auto-fit minmax`) |
| `.card` | 기본 카드(hover 부상 효과) |
| `.note-card` `.note-num` | 번호형 노트 카드 |
| `.price-card` `.pmenu` `.pmenu-card` | 요금/코스 카드 |
| `.chips` `.chip` | 태그 칩 |
| `details`/`summary` | FAQ 아코디언 (`+` 회전 아이콘) |
| `.crumb` | 브레드크럼 |
| `.review` | 후기 카드 |
| `.cta-band` | 하단 예약 유도 밴드 |
| `.site-footer` `.footer-grid` `.footer-ops` `.company-info` `.footer-policies` | 푸터 |
| `.call-fab` | **플로팅 전화예약 버튼**(전 페이지 우하단, 오렌지 그라데이션 `#ffa23c→#ff7a18→#f4600a`, 펄스·링 애니메이션) |
| `.reveal`/`.in` | 스크롤 등장 애니메이션(IntersectionObserver) |
| `.pager` `.pg` | **매거진 페이지네이션**(번호 넘김, 9개/페이지) |

### 2.4 콘텐츠/아티클 레이아웃 (다크 럭스 — 매거진·지역 페이지)
| 클래스 | 용도 |
|---|---|
| `.lux-hero` `.lux-h1` `.lux-lead` | 상단 히어로(네이비 그라데이션 + 골드) |
| `.byline` | 발행·수정일 표기 (E-E-A-T) |
| `.lux-body` `.lux-grid` | 본문 영역(좌측 TOC 240px + 본문 1fr) |
| `.toc` `.toc-inner` | 좌측 고정 목차(스크롤 스파이, 모바일은 칩 형태) |
| `.lux-main` `.lux-sec` | 본문 섹션 카드(좌측 골드 바, h2/h3/p/ul) |
| `.data-box` | 골드 강조 박스(운영 메모 등) |

### 2.5 반응형 브레이크포인트
| 폭 | 변화 |
|---|---|
| ≤1340px | 햄버거 메뉴 전환(`.toggle` 노출, `.menu` 풀스크린 드로어) |
| ≤1100px | 히어로/푸터 그리드 1~2열로 축소 |
| ≤980px | `.lux-grid` 1열, TOC를 상단 칩으로 |
| ≤760px | `.pmenu` 1열 |
| ≤560px | 푸터/회사정보 1열, `.call-fab` 텍스트 숨김(아이콘만) |
| `prefers-reduced-motion` | 애니메이션 비활성 |

### 2.6 성능 패턴
- `content-visibility:auto` 로 하단 섹션 지연 렌더
- `IntersectionObserver` + `requestIdleCallback` 로 등장/스크롤스파이 지연 실행
- 외부 리소스 0 → LCP·CLS 양호

---

## 3. 메뉴 구조 (메인 + 서브 전체 트리)

> 헤더 내비게이션은 **모든 페이지 동일**. 2뎁스 드롭다운(`.submenu` → `.sub2`).

```
홈  (/)

서울 출장마사지  (/seoul/)
 ├ 서울 출장마사지 안내      /seoul/
 ├ 서울 홈타이 안내          /seoul/#home
 ├ 서울 전지역 출장 가능 안내 /seoul/#allarea
 ├ 서울 지하철역 인근 안내    /seoul/#station
 ├ 예약 가능 시간            /reservation/hours/
 ├ 코스 선택 안내            /course/guide/
 ├ 이용 전 확인사항          /guide/checklist/
 ├ 위생 및 안전 안내         /guide/safety/
 └ 자주 묻는 질문            /seoul/faq/

지역별 안내  (/seoul/area/)
 ├ 서울 전체                /seoul/area/
 ├ 강남권 ▸ 강남구·서초구·송파구·강동구
 ├ 강서권 ▸ 강서구·양천구·구로구·금천구
 ├ 서남권 ▸ 관악구·동작구·영등포구
 ├ 동북권 ▸ 광진구·성동구·동대문구·중랑구·성북구·강북구·도봉구·노원구
 ├ 도심권 ▸ 종로구·중구·용산구
 └ 서북권 ▸ 마포구·서대문구·은평구
        (각 구: /seoul/<gu>-gu/  예: /seoul/gangnam-gu/)

지하철역별 안내  (/seoul/stations/)
 ├ 서울 지하철역 전체        /seoul/stations/
 └ 노선별 ▸ 1~9호선 · 신림선 · 우이신설선 · 신분당선 · 수인분당선 ·
            경의중앙선 · 경춘선 · 공항철도 · 서해선
        (각 역: /seoul/stations/<station>-station/)

테마별 안내  (/theme/)
 └ 전체 테마 · 스웨디시 · 로미로미 · 타이마사지 · 중국마사지 · 아로마테라피 ·
   홈케어 · 호텔식마사지 · 발마사지 · 스포츠·경락 · 스킨케어 · 왁싱 ·
   커플 관리 · 24시간 · 수면 가능

코스안내  (/course/)
 └ 전체 코스 · 피로 회복 관리 · 아로마 관리 · 스포츠 관리 · 홈타이 코스 ·
   커플·가족 방문 관리 · 기업·단체 방문 관리 · 가격 안내 · 코스 선택 가이드

예약안내  (/reservation/)
 └ 예약 방법 · 예약 가능 시간 · 방문 가능 장소 · 결제 안내 ·
   변경·취소 안내 · 예약 전 체크사항

이용가이드  (/guide/)
 └ 처음 이용하시는 분 · 방문 전 준비사항 · 위생 및 안전 기준 ·
   관리 후 주의사항 · 금지행위 안내 · 이용 FAQ

후기  (/reviews/)

매거진  (/magazine/)
 └ 전체 매거진 · 이용가이드 · 코스·테마 · 활용팁 · 지역·역세권 ·
   지역별 마사지 · 스웨디시 · 출장마사지 · 한국인 관리사 · 태국 관리사

고객센터  (/customer/)
 └ 공지사항(#notice) · 자주 묻는 질문(#qna) · 1:1 문의(#inquiry) ·
   제휴·기업 문의(#partner) · 개인정보처리방침 · 이용약관

[CTA] 24시 예약  →  tel:+825082024743
```

---

## 4. 사이트 디렉터리 / 페이지 구조

```
/                     홈 (index.html)
/seoul/               서울 출장마사지 허브 + faq/ + area/ + stations/ + <gu>-gu/(25) + 동 페이지
/seoul/area/          권역·자치구 안내 허브
/seoul/stations/      지하철역 허브 + line-N/ + <station>-station/(324)
/theme/               테마 허브 + 14개 테마 페이지
/course/              코스 허브 + 8개 코스 페이지(aroma·couple·fatigue·group·guide·home·price·sports)
/reservation/         예약 허브 + 6개(change·checklist·hours·payment·place + 방법)
/guide/               이용가이드 허브 + 6개(aftercare·checklist·faq·forbidden·prepare·safety)
/reviews/             후기
/customer/            고객센터
/magazine/            매거진 허브 + category/(9) + 글 60편
/privacy/ /terms/ /youth/   정책(개인정보·약관·청소년보호)
/assets/              og-cover.jpg 등
/tools/               생성 스크립트(robots.txt에서 Disallow)
루트 파일: favicon.ico/svg, apple-touch-icon.png, icon-192/512/maskable, site.webmanifest,
          robots.txt, sitemap.xml
```

---

## 5. 콘텐츠 목록

### 5.1 테마 14종 (`/theme/<slug>/`)
`swedish`(스웨디시) · `aroma-therapy`(아로마테라피) · `thai-massage`(타이마사지) ·
`lomi-lomi`(로미로미) · `chinese-massage`(중국마사지) · `sports-massage`(스포츠·경락) ·
`foot-massage`(발마사지) · `home-care`(홈케어) · `hotel-massage`(호텔식마사지) ·
`skin-care`(스킨케어) · `waxing`(왁싱) · `couple`(커플 관리) · `24hours`(24시간) ·
`sleep-available`(수면 가능)

### 5.2 코스 8종 + 기본 요금
`fatigue`(피로 회복 관리) · `aroma`(아로마 관리) · `sports`(스포츠 관리) ·
`home`(홈타이 코스) · `couple`(커플·가족 방문) · `group`(기업·단체 방문) ·
`price`(가격 안내) · `guide`(코스 선택 가이드)

| 코스 | 시간 | 기본 요금 |
|---|---|---|
| 60분 코스 | 60분 | 90,000원 |
| 90분 코스 | 90분 | 150,000원 |
| 120분 코스 | 120분 | 180,000원 |

### 5.3 매거진 카테고리 9종 (`/magazine/category/<slug>/`)
`guide`(이용가이드) · `course-theme`(코스·테마) · `tips`(활용팁) ·
`area-station`(지역·역세권) · `region`(지역별 마사지) · `swedish`(스웨디시) ·
`visiting`(출장마사지) · `korean-therapist`(한국인 관리사) · `thai-therapist`(태국 관리사)

### 5.4 매거진 글 60편 (최신순 정렬, 카드+JSON-LD 자동 등록)
**기본 10편**: chuljang-massage-first-guide, swedish-vs-aroma, office-worker-recovery,
couple-anniversary-home-care, hygiene-safety-checklist, station-area-tips,
sports-recovery-massage, sleep-aroma-routine, price-time-guide, area-guide-by-life

**지역별(region) 10**: gangnam-massage-guide, hongdae-mapo-massage, jamsil-songpa-massage,
yeouido-office-massage, itaewon-yongsan-massage, seongsu-seongdong-massage,
guro-gasan-massage, jongno-junggu-massage, gangbuk-nowon-massage, seocho-massage-guide

**스웨디시(swedish) 10**: swedish-massage-basics, swedish-first-time, swedish-pressure-guide,
swedish-oil-guide, swedish-vs-deep-tissue, swedish-for-office-worker, swedish-time-60-90-120,
swedish-aftercare, swedish-couple-care, swedish-for-sleep

**출장마사지(visiting) 10**: visiting-how-it-works, visiting-vs-shop, visiting-home-prepare,
visiting-hotel-guide, visiting-reservation-tips, visiting-payment-guide, visiting-late-night,
visiting-safety-for-women, visiting-officetel-studio, visiting-first-checklist

**한국인 관리사(korean-therapist) 10**: korean-therapist-features, korean-therapist-communication,
korean-therapist-vs-foreign, korean-therapist-for-women, korean-therapist-swedish,
korean-therapist-aroma, korean-therapist-request, korean-therapist-professional,
korean-therapist-first-time, korean-therapist-couple

**태국 관리사(thai-therapist) 10**: thai-therapist-features, thai-massage-basics,
thai-therapist-stretch, thai-vs-swedish, thai-therapist-aroma-oil, thai-therapist-foot,
thai-therapist-first-time, thai-therapist-flexibility, thai-therapist-communication,
thai-therapist-couple

---

## 6. 지역 / 역세권 체계

- **자치구 25개**: 강남·서초·송파·강동 / 강서·양천·구로·금천 / 관악·동작·영등포 /
  광진·성동·동대문·중랑·성북·강북·도봉·노원 / 종로·중구·용산 / 마포·서대문·은평
  (권역 6분류: 강남권·강서권·서남권·동북권·도심권·서북권)
- **지하철역 324개**: 1~9호선 + 신림선·우이신설선·신분당선·수인분당선·경의중앙선·
  경춘선·공항철도·서해선 (`/seoul/stations/<station>-station/`)
- 자치구 하위에 주요 **동(洞) 페이지**도 존재 (예: `/seoul/gangnam-gu/cheongdam-dong/`)

---

## 7. SEO / 메타 규칙 (모든 페이지 공통)

`<head>` 표준 구성:
- `<title>` : `핵심키워드 | 보조설명` 패턴
- `meta description` (요약), `meta author = "YH LAB 운영팀"`
- `link canonical` = 자기 절대 URL (도메인 `seoul-massage-at6.pages.dev`)
- `hreflang` : `ko-KR` + `x-default` (자기 URL)
- Open Graph: `og:type`(website/article), `og:site_name="Seoul 마사지"`, `og:locale=ko_KR`,
  `og:title/description/url`, `og:image=/assets/og-cover.jpg` (1200×630)
- Twitter: `summary_large_image`
- robots: `index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1`
- 아이콘: favicon.ico/svg, apple-touch-icon, manifest

**구조화 데이터(JSON-LD)**
- 매거진 글: `BreadcrumbList` + `BlogPosting`(headline·description·datePublished·dateModified·author·publisher·inLanguage)
- 매거진/카테고리 목록: `Blog` + `blogPost[]`

**파일**
- `robots.txt`: 전체 Allow, `/tools/` Disallow, GPTBot·ClaudeBot·Google-Extended Allow,
  `Sitemap:`·`Host:` = 운영 도메인
- `sitemap.xml`: 전 페이지 `<loc>`(매거진 글 priority 0.8/weekly 등)

---

## 8. 매거진 자동 생성 시스템 (`tools/`)

콘텐츠를 코드로 관리 → 헤더/푸터/스타일/SEO 일관성 유지.

```
tools/articles_base.py   # CATS(카테고리 정의) + ARTICLES 리스트 + A() 등록 헬퍼
tools/a_region.py        # 지역별 10편  (A(...) 호출)
tools/a_swedish.py       # 스웨디시 10편
tools/a_visiting.py      # 출장마사지 10편
tools/a_korean.py        # 한국인 관리사 10편
tools/a_thai.py          # 태국 관리사 10편
tools/gen_articles.py    # 생성기: 글 HTML + 매거진/카테고리 카드·JSON-LD + sitemap 갱신
tools/add_pagination.py  # 매거진/카테고리에 페이지네이션 주입(9개/페이지)
```

**글 1편 데이터 구조**
```python
A(slug=, cat=, title=, h1=, desc=, lead=,
  card_title=, card_eyebrow=,
  secs=[(소제목, "<p>..</p>"), ...],   # 본문 섹션(고유 작성)
  related=[(href, label), ...],        # 내부링크 섹션 "함께 보면 좋은 안내"
  faq=[(질문, 답), ...],
  cta="하단 예약 밴드 문구")
```
- 생성기가 자동 추가: 발행/수정일(최신순), TOC, "함께 보면 좋은 안내"·"이용 시 알아두면 좋은 점"
  섹션, FAQ, CTA, BreadcrumbList·BlogPosting JSON-LD.
- 정적 부분(헤더 내비·`<style>`·푸터/스크립트)은 `magazine/swedish-vs-aroma/index.html`에서 추출해 재사용.
- 재실행 안전(idempotent): 기존 카드/JSON-LD를 slug 기준으로 제거 후 재삽입.

**실행**: `python3 tools/gen_articles.py`

### 콘텐츠 작성 규칙 (중요)
- **글 분량 2,000~2,500자**(리드+본문 섹션+FAQ 기준, 공백 포함).
- 스팸·복사·중복·반복 금지 → 글마다 본문·FAQ·메타를 **개별 작성**.
- 표준 컴플라이언스 문구(의료행위 아님/19세 이상/통증 시 진료 권유)는 모든 글 공통 허용.
- 본문에 관련 테마·코스·지역·예약 페이지로 **내부링크** 다수 삽입.

---

## 9. 새 사이트 만들 때 교체 체크리스트

1. **도메인**: 전 파일 `seoul-massage-at6.pages.dev` → 신규 도메인 일괄 치환
   (canonical/OG/sitemap/robots `Host`·`Sitemap` 포함).
2. **사업자 정보**(§1): 상호·대표·사업자번호·주소·전화(`tel:`)·개인정보책임자.
3. **사이트명/브랜드**: `Seoul 마사지`, 헤더 `.brand`(이니셜 S), `og:site_name`.
4. **지역 체계**(§6): 대상 도시의 자치구/구역·역 목록으로 교체(메뉴 §3 + `/seoul/` 구조).
5. **요금표**(§5.2): 코스·시간·금액.
6. **테마/코스 목록**(§5.1·5.2): 업종에 맞게 가감.
7. **매거진 콘텐츠**(§5.4·§8): `tools/a_*.py` 글을 신규 지역/주제로 재작성 후 `gen_articles.py` 실행.
8. **OG 이미지·파비콘**: `assets/og-cover.jpg`, 루트 아이콘 교체.
9. **디자인 토큰**(§2.1): 브랜드 컬러를 바꾸려면 `:root` 변수만 수정(그라데이션·골드 등).
10. **법적 고지·정책 페이지**: `/privacy/ /terms/ /youth/` 내용 갱신.

---

## 10. 핵심 UX 디테일 (그대로 이식 권장)
- 전 페이지 **우하단 플로팅 전화버튼**(`.call-fab`) — 모바일 전환 최우선 동선.
- 헤더 **2뎁스 드롭다운** + 모바일 풀스크린 드로어(ESC 닫기).
- 매거진 목록 **번호 페이지네이션**(9개/페이지) — 글이 늘어도 화면이 길어지지 않음.
- 본문 **좌측 고정 TOC + 스크롤 스파이**(모바일은 상단 칩).
- 발행/수정일 `byline` 표기(E-E-A-T) + 정찰 요금 명시(신뢰).
