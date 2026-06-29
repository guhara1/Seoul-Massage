# -*- coding: utf-8 -*-
"""매거진 신규 50편 생성 + 인덱스/카테고리/사이트맵 갱신.

정적 부분(헤더 내비·스타일·푸터)은 기존 swedish-vs-aroma 페이지에서
추출해 재사용하고, 본문은 articles_data / articles_data2 의 고유 콘텐츠로 채운다.
"""
import os, re, datetime, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import articles_base            # noqa: framework
import a_region, a_swedish, a_visiting, a_korean, a_thai  # noqa: populate ARTICLES
from articles_base import ARTICLES, CATS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://seoul-massage1.netlify.app"
TEL = "tel:+825082024743"

def slice_between(s, start, end, inclusive=True):
    i = s.index(start)
    j = s.index(end, i) + (len(end) if inclusive else 0)
    return s[i:j]

# ── 정적 블록 추출 ────────────────────────────────────────────
tpl = open(os.path.join(ROOT, "magazine/swedish-vs-aroma/index.html"), encoding="utf-8").read()
STYLE = slice_between(tpl, "<style>", "</style>")
NAV = slice_between(tpl, "<header>", "</header>")
FOOTER = tpl[tpl.index('<footer class="site-footer">'):]   # footer + call-fab + scripts + </html>

# ── 날짜 부여 (최신순, 2026-06-06 부터 2일 간격으로 과거로) ──
BASE_DATE = datetime.date(2026, 6, 6)
UPDATED = "2026-06-07"
for i, a in enumerate(ARTICLES):
    d = BASE_DATE - datetime.timedelta(days=i * 2)
    a["date"] = d.isoformat()
    a["date_dot"] = d.strftime("%Y.%m.%d")

def card_desc(a):
    t = re.sub(r"\s+", " ", a["desc"]).strip()
    return (t[:58] + "…") if len(t) > 58 else t

def esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;")

# ── 글 페이지 빌드 ────────────────────────────────────────────
def build_page(a):
    cat = CATS[a["cat"]]
    url = f"{BASE}/magazine/{a['slug']}/"
    secs = list(a["secs"])
    # 관련 내부링크 섹션
    rel_li = "".join(f'<li><a href="{h}">{t}</a></li>' for h, t in a["related"])
    secs.append(("함께 보면 좋은 안내",
                 f"<p>아래 안내도 함께 확인해 보세요. 원하는 코스·지역·예약 정보로 바로 이동할 수 있습니다.</p><ul>{rel_li}</ul>"))
    # 이용 안내(컴플라이언스) 섹션
    secs.append(("이용 시 알아두면 좋은 점",
                 "<p>본 안내의 모든 관리는 의료 행위가 아닌 이완·휴식 목적의 건강관리 서비스입니다.</p>"
                 "<p>만 19세 이상 성인을 대상으로 하며, 불법·퇴폐 행위는 일절 제공하지 않습니다.</p>"
                 "<p>통증·부상이 있는 부위는 무리하지 않으며, 해당 증상은 의료기관 진료를 먼저 권유드립니다.</p>"))

    toc = "".join(f'<li><a href="#sec-{i+1}">{h}</a></li>' for i, (h, _) in enumerate(secs))
    body = "".join(
        f'<section class="lux-sec reveal" id="sec-{i+1}"><h2>{h}</h2>{b}</section>'
        for i, (h, b) in enumerate(secs)
    )
    faq = "".join(
        f'<details><summary>{q}<span>+</span></summary><div>{ans}</div></details>'
        for q, ans in a["faq"]
    )

    # JSON-LD
    crumb_json = (
        '{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":['
        '{"@type":"ListItem","position":1,"name":"홈","item":"%s/"},'
        '{"@type":"ListItem","position":2,"name":"매거진","item":"%s/magazine/"},'
        '{"@type":"ListItem","position":3,"name":"%s","item":"%s%s"},'
        '{"@type":"ListItem","position":4,"name":"%s"}]}'
    ) % (BASE, BASE, cat["name"], BASE, cat["path"], esc(a["h1"]))
    post_json = (
        '{"@context":"https://schema.org","@type":"BlogPosting","headline":"%s",'
        '"description":"%s","datePublished":"%s","dateModified":"%s",'
        '"author":{"@type":"Organization","name":"YH LAB 운영팀"},'
        '"publisher":{"@type":"Organization","name":"Seoul 마사지"},'
        '"mainEntityOfPage":"%s","inLanguage":"ko-KR"}'
    ) % (esc(a["title"]), esc(a["desc"]), a["date"], UPDATED, url)

    head = f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b0b0e">
<meta name="format-detection" content="telephone=no">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="googlebot" content="index,follow">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{a["title"]}</title>
<meta name="description" content="{esc(a["desc"])}">
<meta name="author" content="YH LAB 운영팀">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="ko-KR" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Seoul 마사지">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{esc(a["title"])}">
<meta property="og:description" content="{esc(a["desc"])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/og-cover.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(a["title"])}">
<meta name="twitter:description" content="{esc(a["desc"])}">
<meta name="twitter:image" content="{BASE}/assets/og-cover.jpg">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
{STYLE}
<script type="application/ld+json">{crumb_json}</script>
<script type="application/ld+json">{post_json}</script>
</head>
<body>
'''

    crumb = (f'<div class="wrap"><nav class="crumb" aria-label="탐색경로">'
             f'<a href="/">홈</a> › <a href="/magazine/">매거진</a> › '
             f'<a href="{cat["path"]}">{cat["name"]}</a> › <b>{a["h1"]}</b></nav></div>')

    hero = (f'<section class="lux-hero"><div class="wrap">'
            f'<span class="eyebrow"><span class="pulse"></span>MAGAZINE · {cat["name"]}</span>'
            f'<h1 class="lux-h1">{a["h1"]}</h1>'
            f'<p class="lux-lead">{a["lead"]}</p>'
            f'<div class="byline"><span class="au">발행 · {a["date_dot"]}</span>'
            f'<span>최종 업데이트 · {UPDATED.replace("-", ".")}</span></div>'
            f'<div class="actions" style="margin-top:22px">'
            f'<a class="btn btn-primary" href="{TEL}">예약문의</a>'
            f'<a class="btn btn-ghost" href="/magazine/">매거진 전체</a>'
            f'<a class="btn btn-ghost" href="{cat["path"]}">{cat["name"]} 더보기</a>'
            f'<a class="btn btn-ghost" href="/seoul/area/">지역별 안내</a></div></div></section>')

    main = (f'<section class="block lux-body" style="padding-top:34px"><div class="wrap">'
            f'<div class="lux-grid"><aside class="toc"><div class="toc-inner">'
            f'<span class="toc-label">목차</span><ul>{toc}</ul></div></aside>'
            f'<div class="lux-main">{body}</div></div></div></section>')

    faq_sec = (f'<section class="block" id="faq"><div class="wrap">'
               f'<span class="eyebrow"><span class="pulse"></span>FAQ</span>'
               f'<h2 class="sec">자주 묻는 질문</h2>'
               f'<div style="margin-top:26px;max-width:820px">{faq}</div></div></section>')

    cta = (f'<section class="cta-band"><div>'
           f'<span class="eyebrow"><span class="pulse"></span>RESERVE</span>'
           f'<h2>{a["cta"]}</h2>'
           f'<p>연중무휴 · 24시간 상담 · 전화 한 통으로 방문 일정과 코스를 안내드립니다.</p>'
           f'<div class="actions" style="justify-content:center">'
           f'<a class="btn btn-primary" href="{TEL}">0508-202-4743 전화하기 →</a>'
           f'<a class="btn btn-ghost" href="/reservation/">예약 안내 보기</a></div></div></section>')

    return head + NAV + crumb + hero + main + faq_sec + cta + FOOTER

# ── 글 파일 쓰기 ──────────────────────────────────────────────
written = []
for a in ARTICLES:
    d = os.path.join(ROOT, "magazine", a["slug"])
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_page(a))
    written.append(a["slug"])
print(f"글 {len(written)}편 생성")

# ── 카드 마크업 ───────────────────────────────────────────────
def card_html(a):
    cat = CATS[a["cat"]]
    return (f'<a class="card reveal" href="/magazine/{a["slug"]}/">'
            f'<div class="k">{cat["name"]}</div><h3>{a["card_title"]}</h3>'
            f'<p>{card_desc(a)}</p>'
            f'<div style="color:var(--dim);font-size:12.5px;margin-top:12px">'
            f'<time datetime="{a["date"]}">{a["date_dot"]}</time> · {cat["name"]}</div>'
            f'<span class="more">글 보기 →</span></a>')

def post_ld(a):
    return ('{"@type":"BlogPosting","headline":"%s","datePublished":"%s","url":"%s/magazine/%s/"}'
            % (esc(a["title"]), a["date"], BASE, a["slug"]))

# 최신순 정렬
ordered = sorted(ARTICLES, key=lambda x: x["date"], reverse=True)
MYSLUGS = {a["slug"] for a in ARTICLES}

# 재실행 안전(idempotent) 헬퍼: 기존에 삽입한 내 카드/JSON-LD를 먼저 제거
GRID_RE = re.compile(r'<div class="grid g3"[^>]*style="margin-top:26px">')

def strip_my_cards(html):
    for slug in MYSLUGS:
        html = re.sub(r'<a class="card reveal" href="/magazine/' + re.escape(slug) + r'/">.*?</a>',
                      '', html, flags=re.S)
    return html

def strip_my_ld(html):
    for slug in MYSLUGS:
        html = re.sub(r'\{"@type":"BlogPosting"[^{}]*?/magazine/' + re.escape(slug) + r'/"\},?',
                      '', html)
    # 콤마 정리
    html = html.replace('"blogPost":[,', '"blogPost":[')
    html = re.sub(r',\s*,', ',', html)
    html = html.replace(',]', ']')
    return html

def insert_after_grid(html, cards):
    m = GRID_RE.search(html)
    if not m:
        raise SystemExit("grid marker not found")
    return html[:m.end()] + cards + html[m.end():]

# ── 매거진 인덱스 갱신 ────────────────────────────────────────
idx_path = os.path.join(ROOT, "magazine/index.html")
idx = open(idx_path, encoding="utf-8").read()
idx = strip_my_cards(idx)
idx = insert_after_grid(idx, "".join(card_html(a) for a in ordered))
idx = strip_my_ld(idx)
lds = ",".join(post_ld(a) for a in ordered)
idx = idx.replace('"blogPost":[', '"blogPost":[' + lds + ",", 1)
idx = idx.replace('"blogPost":[' + lds + ",]", '"blogPost":[' + lds + "]")  # 비었던 경우
open(idx_path, "w", encoding="utf-8").write(idx)
print("매거진 인덱스 갱신 완료")

# ── 카테고리 페이지 갱신 ──────────────────────────────────────
empty_p = '<p class="sec-lead">등록된 글이 없습니다.</p>'
for cat_key, cat in CATS.items():
    cpath = os.path.join(ROOT, "magazine/category", cat_key, "index.html")
    if not os.path.exists(cpath):
        print("  (없음) " + cpath); continue
    c = open(cpath, encoding="utf-8").read()
    items = [a for a in ordered if a["cat"] == cat_key]
    cards_c = "".join(card_html(a) for a in items)
    c = strip_my_cards(c).replace(empty_p, "")
    c = insert_after_grid(c, cards_c)
    c = strip_my_ld(c)
    if '"blogPost":[' in c:
        lds_c = ",".join(post_ld(a) for a in items)
        c = c.replace('"blogPost":[]', '"blogPost":[' + lds_c + "]", 1)
        c = c.replace('"blogPost":[{', '"blogPost":[' + lds_c + ",{", 1)
    open(cpath, "w", encoding="utf-8").write(c)
    print(f"  카테고리 {cat_key}: {len(items)}편")

# ── 사이트맵 갱신 ─────────────────────────────────────────────
sm_path = os.path.join(ROOT, "sitemap.xml")
sm = open(sm_path, encoding="utf-8").read()
new_urls = "".join(
    f'  <url><loc>{BASE}/magazine/{a["slug"]}/</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>\n'
    for a in ordered
    if f'{BASE}/magazine/{a["slug"]}/</loc>' not in sm
)
sm = sm.replace("</urlset>", new_urls + "</urlset>", 1)
open(sm_path, "w", encoding="utf-8").write(sm)
print(f"사이트맵 {new_urls.count('<url>')}개 URL 추가")
print("완료")
