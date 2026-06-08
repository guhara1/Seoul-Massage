# -*- coding: utf-8 -*-
"""재사용 스타터 킷 빌드: starter/template.html + starter/README.md 생성 후
   SITE-SPEC.md 와 함께 site-starter-kit.zip 으로 묶는다.
   디자인 CSS·푸터·플로팅 버튼은 실제 페이지에서 추출해 그대로 사용한다."""
import os, re, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "magazine/swedish-vs-aroma/index.html")
src = open(SRC, encoding="utf-8").read()

STYLE = src[src.index("<style>"):src.index("</style>")+8]
FOOTER = src[src.index('<footer class="site-footer">'):src.index("</footer>")+9]
FAB = src[src.index('<a class="call-fab"'):src.index("</a>", src.index('<a class="call-fab"'))+4]

# ── 푸터·버튼의 실제 값을 일반 플레이스홀더로 치환 ──────────────
def genericize(s):
    s = s.replace("tel:+825082024743", "tel:+820000000000")
    s = s.replace("0508-202-4743", "0000-0000-0000")
    s = s.replace("Seoul 마사지", "사이트명")
    s = s.replace("815-26-00585", "000-00-00000")
    s = s.replace("경기도 파주시 청석로 268", "사업장 주소")
    s = s.replace("YH LAB", "상호명")
    s = s.replace("김유환", "대표자명")
    s = s.replace("© 2026", "© 2026")
    s = s.replace("서울 전역 방문 건강관리(출장마사지·홈타이) 예약 안내 페이지입니다. 지역·지하철역·테마별 안내와 예약 전 확인사항을 제공합니다.",
                  "(사이트 한 줄 소개) 지역·테마·코스별 안내와 예약 정보를 제공합니다.")
    return s

FOOTER = genericize(FOOTER)
FAB = genericize(FAB)

# ── 헤더 내비(메뉴/하위메뉴 패턴) ─────────────────────────────
NAV = '''<header><nav class="nav" aria-label="주 메뉴">
  <a class="brand" href="/" aria-label="사이트명 홈"><span class="mark">S</span><span>사이트명<small>SITE TAGLINE</small></span></a>
  <button class="toggle" aria-expanded="false" aria-controls="primary-menu" aria-label="메뉴 열기">☰</button>
  <ul id="primary-menu" class="menu">
    <li><a href="/">홈</a></li>

    <!-- 1뎁스 + 서브메뉴 -->
    <li><a href="/service/" aria-haspopup="true">서비스 안내</a>
      <ul class="submenu">
        <li><a href="/service/">서비스 소개</a></li>
        <li><a href="/reservation/hours/">예약 가능 시간</a></li>
        <li><a href="/course/guide/">코스 선택 안내</a></li>
        <li><a href="/guide/checklist/">이용 전 확인사항</a></li>
        <li><a href="/guide/safety/">위생 및 안전 안내</a></li>
        <li><a href="/service/faq/">자주 묻는 질문</a></li>
      </ul>
    </li>

    <!-- 2뎁스 서브메뉴(지역/권역 → 세부) : .has-sub > .sub2 -->
    <li><a href="/area/" aria-haspopup="true">지역별 안내</a>
      <ul class="submenu">
        <li><a href="/area/">전체 지역</a></li>
        <li class="has-sub"><a href="/area/#zone-1" aria-haspopup="true">권역 1</a>
          <ul class="submenu sub2">
            <li><a href="/area/district-a/">지역 A</a></li>
            <li><a href="/area/district-b/">지역 B</a></li>
            <!-- 지역 수만큼 <li> 추가 -->
          </ul>
        </li>
        <li class="has-sub"><a href="/area/#zone-2" aria-haspopup="true">권역 2</a>
          <ul class="submenu sub2">
            <li><a href="/area/district-c/">지역 C</a></li>
            <li><a href="/area/district-d/">지역 D</a></li>
          </ul>
        </li>
        <!-- 권역 수만큼 .has-sub <li> 추가 -->
      </ul>
    </li>

    <li><a href="/theme/" aria-haspopup="true">테마별 안내</a>
      <ul class="submenu">
        <li><a href="/theme/">전체 테마</a></li>
        <li><a href="/theme/theme-1/">테마 1</a></li>
        <li><a href="/theme/theme-2/">테마 2</a></li>
        <!-- 테마 수만큼 추가 -->
      </ul>
    </li>

    <li><a href="/course/" aria-haspopup="true">코스안내</a>
      <ul class="submenu">
        <li><a href="/course/">전체 코스</a></li>
        <li><a href="/course/price/">가격 안내</a></li>
        <li><a href="/course/guide/">코스 선택 가이드</a></li>
      </ul>
    </li>

    <li><a href="/reservation/" aria-haspopup="true">예약안내</a>
      <ul class="submenu">
        <li><a href="/reservation/">예약 방법</a></li>
        <li><a href="/reservation/hours/">예약 가능 시간</a></li>
        <li><a href="/reservation/place/">방문 가능 장소</a></li>
        <li><a href="/reservation/payment/">결제 안내</a></li>
        <li><a href="/reservation/change/">변경·취소 안내</a></li>
      </ul>
    </li>

    <li><a href="/guide/" aria-haspopup="true">이용가이드</a>
      <ul class="submenu">
        <li><a href="/guide/">처음 이용하시는 분</a></li>
        <li><a href="/guide/prepare/">방문 전 준비사항</a></li>
        <li><a href="/guide/safety/">위생 및 안전 기준</a></li>
        <li><a href="/guide/aftercare/">관리 후 주의사항</a></li>
        <li><a href="/guide/faq/">이용 FAQ</a></li>
      </ul>
    </li>

    <li><a href="/reviews/">후기</a></li>

    <li><a href="/magazine/" aria-haspopup="true">매거진</a>
      <ul class="submenu">
        <li><a href="/magazine/">전체 매거진</a></li>
        <li><a href="/magazine/category/category-1/">카테고리 1</a></li>
        <li><a href="/magazine/category/category-2/">카테고리 2</a></li>
      </ul>
    </li>

    <li><a href="/customer/" aria-haspopup="true">고객센터</a>
      <ul class="submenu">
        <li><a href="/customer/#notice">공지사항</a></li>
        <li><a href="/customer/#qna">자주 묻는 질문</a></li>
        <li><a href="/customer/#inquiry">1:1 문의</a></li>
        <li><a href="/privacy/">개인정보처리방침</a></li>
        <li><a href="/terms/">이용약관</a></li>
      </ul>
    </li>

    <li><a class="cta-pill" href="tel:+820000000000">24시 예약</a></li>
  </ul>
</nav></header>'''

# ── 본문(샘플): 브레드크럼 + 럭스 히어로 + 좌측 TOC + 섹션 + FAQ + CTA ──
BODY = '''<div class="wrap"><nav class="crumb" aria-label="탐색경로"><a href="/">홈</a> › <a href="/magazine/">매거진</a> › <b>페이지 제목</b></nav></div>

<section class="lux-hero"><div class="wrap">
  <span class="eyebrow"><span class="pulse"></span>EYEBROW · 분류</span>
  <h1 class="lux-h1">페이지 큰 제목(H1)</h1>
  <p class="lux-lead">페이지를 한두 문장으로 소개하는 리드 문구가 들어갑니다.</p>
  <div class="byline"><span class="au">발행 · 2026.00.00</span><span>최종 업데이트 · 2026.00.00</span></div>
  <div class="actions" style="margin-top:22px">
    <a class="btn btn-primary" href="tel:+820000000000">예약문의</a>
    <a class="btn btn-ghost" href="/magazine/">목록으로</a>
  </div>
</div></section>

<section class="block lux-body" style="padding-top:34px"><div class="wrap"><div class="lux-grid">
  <aside class="toc"><div class="toc-inner"><span class="toc-label">목차</span>
    <ul>
      <li><a href="#sec-1">첫 번째 섹션</a></li>
      <li><a href="#sec-2">두 번째 섹션</a></li>
    </ul>
  </div></aside>
  <div class="lux-main">
    <section class="lux-sec reveal" id="sec-1"><h2>첫 번째 섹션 제목</h2>
      <p>본문 문단입니다. 내부링크는 <a href="/theme/theme-1/">이렇게</a> 넣습니다.</p>
      <ul><li>리스트 항목 1</li><li>리스트 항목 2</li></ul>
    </section>
    <section class="lux-sec reveal" id="sec-2"><h2>두 번째 섹션 제목</h2>
      <p>두 번째 섹션 본문입니다.</p>
      <div class="data-box"><b>강조 박스</b><p>골드 강조 박스(운영 메모 등)에 쓰는 영역입니다.</p></div>
    </section>
  </div>
</div></div></section>

<section class="block" id="faq"><div class="wrap">
  <span class="eyebrow"><span class="pulse"></span>FAQ</span>
  <h2 class="sec">자주 묻는 질문</h2>
  <div style="margin-top:26px;max-width:820px">
    <details><summary>질문 1<span>+</span></summary><div>답변 1</div></details>
    <details><summary>질문 2<span>+</span></summary><div>답변 2</div></details>
  </div>
</div></section>

<section class="cta-band"><div>
  <span class="eyebrow"><span class="pulse"></span>RESERVE</span>
  <h2>하단 예약 유도 문구</h2>
  <p>연중무휴 · 24시간 상담 · 전화 한 통으로 안내드립니다.</p>
  <div class="actions" style="justify-content:center">
    <a class="btn btn-primary" href="tel:+820000000000">0000-0000-0000 전화하기 →</a>
    <a class="btn btn-ghost" href="/reservation/">예약 안내 보기</a>
  </div>
</div></section>'''

# ── 스크립트(메뉴 토글 + 스크롤 등장 + TOC 스파이) ─────────────
SCRIPT = '''<script>
(function(){
  var t=document.querySelector('.toggle'),m=document.getElementById('primary-menu');
  if(t&&m){t.addEventListener('click',function(){var o=m.classList.toggle('open');t.setAttribute('aria-expanded',o);});}
  document.addEventListener('keydown',function(e){if(e.key==='Escape'&&m){m.classList.remove('open');}});
  function idle(fn){if('requestIdleCallback'in window){requestIdleCallback(fn,{timeout:1500});}else{setTimeout(fn,1);}}
  idle(function(){
    if(!('IntersectionObserver'in window)){document.querySelectorAll('.reveal').forEach(function(el){el.classList.add('in');});return;}
    var io=new IntersectionObserver(function(es){es.forEach(function(e){
      if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});},{threshold:.12,rootMargin:'80px'});
    document.querySelectorAll('.reveal').forEach(function(el){io.observe(el);});
    var secs=[].slice.call(document.querySelectorAll('.lux-sec')),links=[].slice.call(document.querySelectorAll('.toc a'));
    if(secs.length&&links.length){
      var spy=new IntersectionObserver(function(es){es.forEach(function(e){
        if(e.isIntersecting){var id=e.target.id;links.forEach(function(a){a.classList.toggle('active',a.getAttribute('href')==='#'+id);});}});
      },{rootMargin:'-35% 0px -55% 0px'});
      secs.forEach(function(s){spy.observe(s);});
    }
  });
})();
</script>'''

HEAD = '''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b0b0e">
<meta name="format-detection" content="telephone=no">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<title>페이지 제목 | 사이트명</title>
<meta name="description" content="페이지 설명(검색 결과 노출 문구). 120자 내외로 작성하세요.">
<meta name="author" content="사이트명 운영팀">
<link rel="canonical" href="https://example.pages.dev/page-path/">
<link rel="alternate" hreflang="ko-KR" href="https://example.pages.dev/page-path/">
<link rel="alternate" hreflang="x-default" href="https://example.pages.dev/page-path/">
<meta property="og:type" content="article">
<meta property="og:site_name" content="사이트명">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="페이지 제목 | 사이트명">
<meta property="og:description" content="페이지 설명(검색 결과 노출 문구).">
<meta property="og:url" content="https://example.pages.dev/page-path/">
<meta property="og:image" content="https://example.pages.dev/assets/og-cover.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
'''

template = HEAD + STYLE + "\n</head>\n<body>\n" + NAV + "\n" + BODY + "\n" + FOOTER + "\n" + FAB + "\n" + SCRIPT + "\n</body>\n</html>\n"

os.makedirs(os.path.join(ROOT, "starter"), exist_ok=True)
open(os.path.join(ROOT, "starter/template.html"), "w", encoding="utf-8").write(template)
print("template.html:", len(template), "chars")
PY_DONE_MARK = True
