# 지역/업종 사이트 스타터 킷

이 폴더는 **새 사이트를 빠르게 복제**하기 위한 시작 세트입니다.
`SITE-SPEC.md`(전체 사양 문서)와 함께 쓰세요.

```
starter/
 ├ template.html   ← 헤더·메뉴·전체 CSS·푸터·플로팅 전화버튼이 든 "빈 페이지 뼈대"
 └ README.md       ← 이 파일(사용법 + 교체 가이드)
SITE-SPEC.md       ← 디자인·메뉴·콘텐츠·SEO 전체 사양(상위 폴더)
```

## 1. 30초 시작
1. `template.html` 을 복사해 페이지를 만든다(예: `index.html`).
2. 아래 **교체 표**의 값들을 일괄 찾기·바꾸기(Find & Replace) 한다.
3. 브라우저로 열어 확인 → Cloudflare Pages 등 정적 호스팅에 올린다.

> 외부 폰트·JS·CSS 요청이 0개라 빌드 도구 없이 그대로 동작합니다.

## 2. 일괄 교체 표 (template.html 안의 플레이스홀더)
| 찾을 값 | 바꿀 내용 | 위치 |
|---|---|---|
| `사이트명` | 브랜드/사이트 이름 | 타이틀·헤더·OG·푸터 |
| `SITE TAGLINE` | 헤더 로고 밑 영문 태그라인 | 헤더 `.brand small` |
| `S`(`<span class="mark">S</span>`) | 로고 이니셜 1글자 | 헤더 로고 |
| `https://example.pages.dev` | 실제 도메인 | canonical·OG·hreflang |
| `/page-path/` | 해당 페이지 경로 | canonical·OG url |
| `+820000000000` | 전화(국제표기, 예 +8210...) | `tel:` 링크 전부 |
| `0000-0000-0000` | 전화(표시용) | CTA·푸터·플로팅 버튼 |
| `상호명` | 사업자 상호 | 푸터 회사정보 |
| `대표자명` | 대표자 / 개인정보보호책임자 | 푸터 회사정보 |
| `000-00-00000` | 사업자등록번호 | 푸터 |
| `사업장 주소` | 사업장 주소 | 푸터 |
| `2026` | 저작권 연도 | 푸터 |
| `페이지 제목` / `페이지 큰 제목(H1)` | 각 페이지 제목 | head·H1 |
| `페이지 설명…` | meta description | head·OG |

## 3. 메뉴/하위메뉴 늘리는 법 (template.html `<nav>`)
- **1뎁스 메뉴**: `<li><a>…</a></li>` 추가.
- **서브메뉴(드롭다운)**: 상위 `<li>` 안에 `<ul class="submenu">…</ul>`.
- **2뎁스(서브의 서브)**: 서브 `<li>` 에 `class="has-sub"` 부여 후 안에 `<ul class="submenu sub2">…</ul>`.
- 지역·역·테마처럼 항목이 많으면 같은 패턴으로 `<li>` 만 반복하면 됩니다.
- 모바일(≤1340px)에서는 햄버거 버튼으로 자동 전환(별도 작업 불필요).

## 4. 본문 레이아웃 컴포넌트 (그대로 복사해서 사용)
| 구성 | 클래스 |
|---|---|
| 상단 히어로 | `.lux-hero` `.lux-h1` `.lux-lead` `.byline` |
| 좌측 고정 목차 + 본문 | `.lux-body` `.lux-grid` `.toc` / `.lux-main` `.lux-sec` |
| 카드 그리드 | `.grid.g3` + `.card` (홈/목록용) |
| 요금 카드 | `.pmenu` `.pmenu-card`(`.best`) |
| FAQ 아코디언 | `details > summary + div` |
| 하단 예약 밴드 | `.cta-band` |
| 강조 박스 | `.data-box` |
| 스크롤 등장 | 요소에 `class="reveal"` 만 추가 |

## 5. 디자인 색상 바꾸기
`<style>` 최상단 `:root` 변수만 수정하면 사이트 전체 톤이 바뀝니다.
```css
--bg / --surface / --surface-2   /* 배경 계열 */
--text / --muted / --dim         /* 글자 계열 */
--gold / --rose / --copper       /* 포인트 */
--grad                           /* 버튼·강조 그라데이션 */
```
PWA/모바일 주소창 색은 `<meta name="theme-color">` 와 `site.webmanifest` 의 `theme_color`.

## 6. 함께 챙길 루트 파일(이 킷엔 미포함, 새로 만들기)
- `robots.txt` (Sitemap·Host = 새 도메인), `sitemap.xml`
- `site.webmanifest`, `favicon.ico/svg`, `apple-touch-icon.png`, `icon-192/512.png`
- `assets/og-cover.jpg` (1200×630)
- 정책 페이지: `/privacy/ /terms/ /youth/`

## 7. 콘텐츠(매거진) 자동 생성을 쓰려면
원본 저장소 `tools/` 의 생성기 패턴을 그대로 가져오세요.
- `articles_base.py`(틀) + `a_*.py`(카테고리별 글 데이터) + `gen_articles.py`(생성)
- 글 1편 = `A(slug, cat, title, h1, desc, lead, secs[(소제목,HTML)], related, faq, cta)`
- 권장 분량 **2,000~2,500자**, 글마다 본문·FAQ 개별 작성(복사·중복 금지).

자세한 전체 사양은 `SITE-SPEC.md` 참고.
