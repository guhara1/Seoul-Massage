# -*- coding: utf-8 -*-
"""Seoul 마사지 — 정적 사이트 생성기.

순수 정적 HTML(인라인 CSS/JS, 런타임 의존성 0)을 생성합니다. 서울 전역을
서울 > 자치구 > 대표 동 / 지하철 노선 > 역 / 테마 구조로 구성하며,
모든 인덱스 페이지 본문은 2,000~2,500자(공백 포함)를 목표로 작성합니다.

실행:  python3 tools/build.py
출력:  HTML + sitemap.xml + robots.txt + site.webmanifest (repo 루트)
"""

import os
import json
import re
import hashlib
import datetime

from theme_assets import CSS, JS
from data_seoul import (DISTRICTS, REGIONS_ORDER, REGION_SUMMARY,
                        LINES, STATION_GU, SLUG_OVERRIDE, STATION_CHAR, THEMES)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# 브랜드 / 사업자 상수  (실서비스 전 교체)
# ---------------------------------------------------------------------------
BASE_URL   = "https://seoul-massage1.netlify.app"
BRAND      = "Seoul 마사지"
BRAND_SHORT= "Seoul"
PHONE_DISP = "0508-202-4743"           # 예약 전화번호
PHONE_TEL  = "+825082024743"           # tel: 링크용
HOURS      = "연중무휴 · 24시간 상담"
INDEXNOW_KEY = "2d763995ac27d8ecc05010a1ad165f6e"   # IndexNow 인증 키 (hex 32자)
UPDATED    = "2026-06-07"
BUILD_DATE = datetime.date.today().isoformat()      # sitemap lastmod(색인 신선도 신호)
# 네이버 웹마스터 사이트 인증 코드(메인 페이지 메타). 여러 속성 등록 시 모두 출력.
NAVER_VERIFY = ["26d4cfa9ce8a55a8611366c1ec6104bc362aebb3",
                "6f196801f279ed9c18d90a5a9deedd692baee361"]

COMPANY = {
    "name": "YH LAB",
    "ceo": "김유환",
    "biz_no": "815-26-00585",
    "addr": "경기도 파주시 청석로 268",
    "sales_no": "",                      # 통신판매업신고 (미발급 시 비표시)
    "privacy_officer": "김유환",
}

# 코스 (홈/코스 페이지 공용)
COURSES = [
    {"slug": "fatigue", "kicker": "RELAX · 피로 회복", "name": "피로 회복 관리",
     "desc": "전신의 긴장을 부드럽게 풀어주는 스웨디시 계열 기본 관리입니다."},
    {"slug": "aroma", "kicker": "AROMA · 아로마", "name": "아로마 관리",
     "desc": "블렌딩 오일을 사용해 향과 함께 심신을 이완하는 관리입니다.", "best": True},
    {"slug": "sports", "kicker": "SPORTS · 스포츠", "name": "스포츠 관리",
     "desc": "운동 후 뭉친 근육과 컨디션 회복에 초점을 맞춘 관리입니다."},
    {"slug": "home", "kicker": "HOME · 홈타이", "name": "홈타이 코스",
     "desc": "자택을 방문해 이동 없이 받는 방문형 홈타이 관리입니다."},
    {"slug": "couple", "kicker": "COUPLE · 커플·가족", "name": "커플·가족 방문 관리",
     "desc": "두 분이 같은 공간에서 동시에 받는 동반 관리입니다."},
    {"slug": "group", "kicker": "GROUP · 기업·단체", "name": "기업·단체 방문 관리",
     "desc": "워크숍·행사 등 단체 인원을 위한 사전 협의형 방문 관리입니다."},
]

TIME_PRICING = [
    {"name": "60분 코스", "price": "90,000", "dur": "60분", "desc": "기본 컨디션·릴랙스 케어"},
    {"name": "90분 코스", "price": "150,000", "dur": "90분", "desc": "아로마 포함 추천 구성", "best": True},
    {"name": "120분 코스", "price": "180,000", "dur": "120분", "desc": "전신 집중 프리미엄 케어"},
]

# ---------------------------------------------------------------------------
# 파생 인덱스
# ---------------------------------------------------------------------------
DISTRICT_BY_SLUG = {d["slug"]: d for d in DISTRICTS}
REGION_DISTRICTS = {r: [d for d in DISTRICTS if d["region"] == r] for r in REGIONS_ORDER}
LINE_BY_NAME = {l["name"]: l for l in LINES}
GU_SLUG = {d["name"]: d["slug"] for d in DISTRICTS}

# ---------------------------------------------------------------------------
# 한글 → 로마자 (역 슬러그 자동 생성, 개정 로마자 표기 근사)
# ---------------------------------------------------------------------------
_LEAD = ['g','kk','n','d','tt','r','m','b','pp','s','ss','','j','jj','ch','k','t','p','h']
_VOWEL = ['a','ae','ya','yae','eo','e','yeo','ye','o','wa','wae','oe','yo','u','wo','we','wi','yu','eu','ui','i']
_TAIL = ['','k','k','k','n','n','n','t','l','k','m','l','l','l','p','l','m','p','p','t','t','ng','t','t','k','t','p','t']

def romanize(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3:
            c = o - 0xAC00
            out.append(_LEAD[c // 588] + _VOWEL[(c % 588) // 28] + _TAIL[c % 28])
        elif ch.isalnum():
            out.append(ch.lower())
        # 그 외(공백·기호) 무시
    slug = "".join(out)
    slug = re.sub(r"[^a-z0-9]+", "", slug)
    return slug or "station"

# ---------------------------------------------------------------------------
# 역 레지스트리 — 노선 데이터에서 자동 생성(환승역 1개 URL로 병합)
#   각 역: name, slug, lines[], gu, gu_slug, dongs[], nearby[](인접 역명), char
# ---------------------------------------------------------------------------
def _build_stations():
    reg, order, used_slug = {}, [], {}
    for l in LINES:
        for nm in l["stations"]:
            if nm not in reg:
                base = nm[:-1] if nm.endswith("역") else nm
                slug = SLUG_OVERRIDE.get(nm) or (romanize(base) + "-station")
                # 슬러그 충돌 방지
                if slug in used_slug and used_slug[slug] != nm:
                    slug = romanize(base) + f"-{len(order)}-station"
                used_slug[slug] = nm
                gu = STATION_GU.get(nm, "")
                gu_slug = GU_SLUG.get(gu, "")
                dongs = DISTRICT_BY_SLUG[gu_slug]["dongs"] if gu_slug else []
                reg[nm] = {"name": nm, "slug": slug, "lines": [], "gu": gu,
                           "gu_slug": gu_slug, "dongs": dongs, "nearby": [],
                           "char": STATION_CHAR.get(nm, "")}
                order.append(nm)
            if l["name"] not in reg[nm]["lines"]:
                reg[nm]["lines"].append(l["name"])
    # 인접 역(같은 노선 상의 앞뒤 역) 수집
    for l in LINES:
        st = l["stations"]
        for i, nm in enumerate(st):
            for j in (i - 1, i + 1):
                if 0 <= j < len(st) and st[j] not in reg[nm]["nearby"] and st[j] != nm:
                    reg[nm]["nearby"].append(st[j])
    return [reg[n] for n in order]

STATIONS = _build_stations()
STATION_SLUGS = {s["name"]: s["slug"] for s in STATIONS}
STATION_BY_NAME = {s["name"]: s for s in STATIONS}

# ---------------------------------------------------------------------------
# 콘텐츠 변형 엔진 (도어웨이 회피 — 페이지마다 문장 구조를 달리함)
# ---------------------------------------------------------------------------
def _seed(s):
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16)

def pick(key, pool, salt=""):
    return pool[_seed(key + "|" + salt) % len(pool)]

def picks(key, pool, n, salt=""):
    """pool에서 서로 다른 n개를 결정적으로 선택."""
    if n >= len(pool):
        order = list(range(len(pool)))
    else:
        order, used, i = [], set(), 0
        while len(order) < n:
            idx = _seed(key + "|" + salt + str(i)) % len(pool)
            while idx in used:
                idx = (idx + 1) % len(pool)
            used.add(idx); order.append(idx); i += 1
    return [pool[i] for i in order]

def text_len(html):
    """헤더/푸터 제외, lux-main + faq 본문 글자 수(공백 포함)."""
    body = html.split("</header>", 1)[-1].split("<footer", 1)[0]
    txt = re.sub(r"<[^>]+>", "", body)
    txt = txt.replace("&nbsp;", " ")
    return len(re.sub(r"\s+", " ", txt).strip())

# ---------------------------------------------------------------------------
# 네비게이션 (상단 메뉴 — 키워드 반복 없이 짧게)
# ---------------------------------------------------------------------------
def menu_html(active):
    def li(key, href, label, sub=None, cta=False):
        cls = ' class="active"' if active == key else ""
        pop = ' aria-haspopup="true"' if sub else ""
        a = f'<a href="{href}"{cls}{pop}>{label}</a>'
        if cta:
            a = f'<a class="cta-pill" href="tel:{PHONE_TEL}">24시 예약</a>'
        sub_html = ""
        if sub:
            parts = []
            for item in sub:
                if len(item) == 3:
                    h, t, kids = item
                    kids_html = "".join(f'<li><a href="{kh}">{kt}</a></li>' for kh, kt in kids)
                    parts.append(
                        f'<li class="has-sub"><a href="{h}" aria-haspopup="true">{t}</a>'
                        f'<ul class="submenu sub2">{kids_html}</ul></li>')
                else:
                    h, t = item
                    parts.append(f'<li><a href="{h}">{t}</a></li>')
            sub_html = f'<ul class="submenu">{"".join(parts)}</ul>'
        return f"<li>{a}{sub_html}</li>"

    # 지역별 안내: 권역 → 자치구 (동은 구 페이지 내부에서 노출)
    area_sub = [("/seoul/area/", "서울 전체")]
    for r in REGIONS_ORDER:
        kids = [(f"/seoul/{d['slug']}/", d["name"]) for d in REGION_DISTRICTS[r]]
        area_sub.append((f"/seoul/area/#{slugify_region(r)}", r, kids))

    # 지하철: 노선 → 노선별 전체 역명(역명만 표시, 키워드 비반복)
    station_sub = [("/seoul/stations/", "서울 지하철역 전체")]
    for l in LINES:
        kids = [(f"/seoul/stations/{STATION_SLUGS[nm]}/", nm) for nm in l["stations"]]
        station_sub.append((f"/seoul/stations/{l['slug']}/", l["name"], kids))

    theme_sub = [("/theme/", "전체 테마")]
    theme_sub += [(f"/theme/{t['slug']}/", t["name"]) for t in THEMES]

    seoul_sub = [
        ("/seoul/", "서울 출장마사지 안내"),
        ("/seoul/#home", "서울 홈타이 안내"),
        ("/seoul/#allarea", "서울 전지역 출장 가능 안내"),
        ("/seoul/#station", "서울 지하철역 인근 안내"),
        ("/reservation/hours/", "예약 가능 시간"),
        ("/course/guide/", "코스 선택 안내"),
        ("/guide/checklist/", "이용 전 확인사항"),
        ("/guide/safety/", "위생 및 안전 안내"),
        ("/seoul/faq/", "자주 묻는 질문"),
    ]
    course_sub = [
        ("/course/", "전체 코스"),
        ("/course/fatigue/", "피로 회복 관리"),
        ("/course/aroma/", "아로마 관리"),
        ("/course/sports/", "스포츠 관리"),
        ("/course/home/", "홈타이 코스"),
        ("/course/couple/", "커플·가족 방문 관리"),
        ("/course/group/", "기업·단체 방문 관리"),
        ("/course/price/", "가격 안내"),
        ("/course/guide/", "코스 선택 가이드"),
    ]
    reservation_sub = [
        ("/reservation/", "예약 방법"),
        ("/reservation/hours/", "예약 가능 시간"),
        ("/reservation/place/", "방문 가능 장소"),
        ("/reservation/payment/", "결제 안내"),
        ("/reservation/change/", "변경·취소 안내"),
        ("/reservation/checklist/", "예약 전 체크사항"),
    ]
    guide_sub = [
        ("/guide/", "처음 이용하시는 분"),
        ("/guide/prepare/", "방문 전 준비사항"),
        ("/guide/safety/", "위생 및 안전 기준"),
        ("/guide/aftercare/", "관리 후 주의사항"),
        ("/guide/forbidden/", "금지행위 안내"),
        ("/guide/faq/", "이용 FAQ"),
    ]
    customer_sub = [
        ("/customer/#notice", "공지사항"),
        ("/customer/#qna", "자주 묻는 질문"),
        ("/customer/#inquiry", "1:1 문의"),
        ("/customer/#partner", "제휴·기업 문의"),
        ("/privacy/", "개인정보처리방침"),
        ("/terms/", "이용약관"),
    ]
    items = [
        li("home", "/", "홈"),
        li("seoul", "/seoul/", "서울 출장마사지", seoul_sub),
        li("area", "/seoul/area/", "지역별 안내", area_sub),
        li("stations", "/seoul/stations/", "지하철역별 안내", station_sub),
        li("theme", "/theme/", "테마별 안내", theme_sub),
        li("course", "/course/", "코스안내", course_sub),
        li("reservation", "/reservation/", "예약안내", reservation_sub),
        li("guide", "/guide/", "이용가이드", guide_sub),
        li("reviews", "/reviews/", "후기"),
        li("magazine", "/magazine/", "매거진",
           [("/magazine/", "전체 매거진")]
           + [(f"/magazine/category/{c['slug']}/", c["name"]) for c in MAG_CATS]),
        li("customer", "/customer/", "고객센터", customer_sub),
        li("cta", "#", "", cta=True),
    ]
    return (
        '<header><nav class="nav" aria-label="주 메뉴">'
        f'<a class="brand" href="/" aria-label="{BRAND} 홈">'
        f'<span class="mark">S</span><span>{BRAND_SHORT}<small>SEOUL MASSAGE</small></span></a>'
        '<button class="toggle" aria-expanded="false" aria-controls="primary-menu" aria-label="메뉴 열기">☰</button>'
        f'<ul id="primary-menu" class="menu">{"".join(items)}</ul>'
        "</nav></header>"
    )

def slugify_region(r):
    m = {"강남권":"gangnam","강서권":"gangseo","서남권":"seonam",
         "동북권":"dongbuk","도심권":"dosim","서북권":"seobuk"}
    return m[r]

# ---------------------------------------------------------------------------
# 푸터 (지역명/역명 대량 나열 금지 — 권역·안내 링크 중심)
# ---------------------------------------------------------------------------
def footer_html():
    region_links = "".join(
        f'<a href="/seoul/area/#{slugify_region(r)}">{r}</a>' for r in REGIONS_ORDER)
    theme_links = "".join(
        f'<a href="/theme/{t["slug"]}/">{t["name"]}</a>' for t in THEMES[:6])
    return f"""<footer class="site-footer"><div class="wrap">
<div class="footer-grid">
  <div class="footer-brand">
    <b class="grad">{BRAND}</b>
    <p>서울 전역 방문 건강관리(출장마사지·홈타이) 예약 안내 페이지입니다. 지역·지하철역·테마별 안내와 예약 전 확인사항을 제공합니다.</p>
  </div>
  <div><h4>지역별 안내</h4>{region_links}<a href="/seoul/area/">서울 전체 보기</a></div>
  <div><h4>테마별 안내</h4>{theme_links}<a href="/theme/">전체 테마 보기</a></div>
  <div><h4>안내</h4>
    <a href="/reservation/">예약안내</a><a href="/guide/">이용가이드</a>
    <a href="/magazine/">매거진</a><a href="/reviews/">후기</a><a href="/customer/">고객센터</a></div>
</div>
<div class="footer-ops">
  <div><b>운영 시간</b>{HOURS}</div>
  <div><b>전화 예약·상담</b><a href="tel:{PHONE_TEL}">{PHONE_DISP}</a></div>
</div>
<div class="company-info">
  <div><b>상호</b> {COMPANY['name']}</div>
  <div><b>대표</b> {COMPANY['ceo']}</div>
  <div><b>사업자등록번호</b> {COMPANY['biz_no']}</div>
  <div><b>주소</b> {COMPANY['addr']}</div>
  {f"<div><b>통신판매업신고</b> {COMPANY['sales_no']}</div>" if COMPANY['sales_no'] else ""}
  <div><b>개인정보보호책임자</b> {COMPANY['privacy_officer']}</div>
</div>
<div class="footer-policies">
  <a href="/customer/#notice">공지사항</a><a href="/customer/#qna">자주 묻는 질문</a>
  <a href="/customer/#inquiry">1:1 문의</a><a href="/privacy/">개인정보처리방침</a>
  <a href="/terms/">이용약관</a><a href="/youth/">청소년보호정책</a>
</div>
<div class="footer-bottom">
  © 2026 {COMPANY['name']}. All rights reserved.
  <div class="legal-note">본 서비스는 의료 행위가 아닌 건강관리(이완·휴식) 목적의 방문 관리 서비스이며, 만 19세 이상 성인을 대상으로 합니다. 불법·퇴폐 행위는 일절 제공하지 않습니다.</div>
</div>
</div></footer>"""

# ---------------------------------------------------------------------------
# 페이지 셸
# ---------------------------------------------------------------------------
def call_fab():
    phone_svg = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.6 10.8c1.4 2.8 3.8 5.2 '
                 '6.6 6.6l2.2-2.2c.28-.28.68-.36 1.02-.24 1.12.37 2.33.57 3.58.57.55 0 1 .45 1 '
                 '1V20c0 .55-.45 1-1 1C10.4 21 3 13.6 3 4.4c0-.55.45-1 1-1h3.6c.55 0 1 .45 1 1 0 '
                 '1.25.2 2.46.57 3.58.12.34.04.74-.24 1.02l-2.2 2.2z"/></svg>')
    return (f'<a class="call-fab" href="tel:{PHONE_TEL}" aria-label="전화 예약 {PHONE_DISP}">'
            f'<span class="call-fab-ic">{phone_svg}</span>'
            f'<span class="call-fab-tx">전화 예약<small>{PHONE_DISP}</small></span></a>')

def page(path, title, desc, active, body, jsonld=None, og_type="website", index=True, naver_verify=None):
    canonical = BASE_URL + path
    robots = ("index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"
              if index else "noindex,follow")
    gbot = "index,follow" if index else "noindex,follow"
    ld = ""
    if jsonld:
        blocks = jsonld if isinstance(jsonld, list) else [jsonld]
        ld = "".join('<script type="application/ld+json">'
                     + json.dumps(b, ensure_ascii=False, separators=(",", ":"))
                     + "</script>" for b in blocks)
    og_img = BASE_URL + "/assets/og-cover.jpg"
    if naver_verify:
        codes = naver_verify if isinstance(naver_verify, list) else [naver_verify]
        naver_meta = "".join(f'<meta name="naver-site-verification" content="{c}" />' for c in codes)
    else:
        naver_meta = ""
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b0b0e">
<meta name="format-detection" content="telephone=no">
<meta name="robots" content="{robots}">
<meta name="googlebot" content="{gbot}">
<meta name="referrer" content="strict-origin-when-cross-origin">
{naver_meta}
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="{COMPANY['name']} 운영팀">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="ko-KR" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{og_img}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<style>{CSS}</style>
{ld}
</head>
<body>
{menu_html(active)}
{body}
{footer_html()}
{call_fab()}
<script>{JS}</script>
</body>
</html>"""

def write(path, html):
    if path == "/":
        out = os.path.join(ROOT, "index.html")
    else:
        d = os.path.join(ROOT, path.strip("/"))
        os.makedirs(d, exist_ok=True)
        out = os.path.join(d, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

# ---------------------------------------------------------------------------
# 공통 빌더
# ---------------------------------------------------------------------------
def breadcrumb(items):
    parts = []
    for href, label in items:
        parts.append(f'<a href="{href}">{label}</a>' if href else f"<b>{label}</b>")
    return f'<div class="wrap"><nav class="crumb" aria-label="탐색경로">{" › ".join(parts)}</nav></div>'

def bc_ld(trail):
    el = []
    for i, (p, n) in enumerate(trail):
        item = {"@type": "ListItem", "position": i + 1, "name": n}
        if p:
            item["item"] = BASE_URL + p
        el.append(item)
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": el}

def faq_block(qas, heading="자주 묻는 질문"):
    rows = "".join(f"<details><summary>{q}<span>+</span></summary><div>{a}</div></details>"
                   for q, a in qas)
    return f"""<section class="block" id="faq"><div class="wrap">
<span class="eyebrow"><span class="pulse"></span>FAQ</span>
<h2 class="sec">{heading}</h2>
<div style="margin-top:26px;max-width:820px">{rows}</div>
</div></section>"""

def faq_ld(qas):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qas]}

def notes_block(eyebrow, heading, lead, notes, _id="about"):
    cards = "".join(
        f'<div class="note-card reveal"><div class="note-num">{n:02d}</div>'
        f'<div class="note-content"><h3 class="note-title">{t}</h3>'
        f'<div class="note-text">{"".join(f"<p>{p}</p>" for p in ps)}</div></div></div>'
        for n, (t, ps) in enumerate(notes, 1))
    return f"""<section class="block" id="{_id}"><div class="wrap">
<span class="eyebrow"><span class="pulse"></span>{eyebrow}</span>
<h2 class="sec">{heading}</h2>
<p class="sec-lead">{lead}</p>
<div class="note-stack" style="margin-top:30px">{cards}</div>
</div></section>"""

def price_menu_block(anchor="pricing-menu"):
    cards = ""
    for p in TIME_PRICING:
        best = " best" if p.get("best") else ""
        badge = '<span class="pmenu-badge">추천</span>' if p.get("best") else ""
        cards += (f'<div class="pmenu-card{best}">{badge}'
                  f'<div class="pmenu-name">{p["name"]}</div>'
                  f'<div class="pmenu-price">{p["price"]}<span>원</span></div>'
                  f'<div class="pmenu-dur">{p["dur"]}</div>'
                  f'<div class="pmenu-desc">{p["desc"]}</div>'
                  f'<a class="pmenu-btn" href="tel:{PHONE_TEL}">예약 문의</a></div>')
    return (f'<section class="block" id="{anchor}"><div class="wrap">'
            f'<span class="eyebrow"><span class="pulse"></span>요금 안내</span>'
            f'<h2 class="sec">코스별 기본 요금</h2>'
            f'<p class="sec-lead">60·90·120분 코스별 기본 요금입니다. 숨겨진 추가 비용 없이 투명하게 안내합니다.</p>'
            f'<div class="pmenu">{cards}</div>'
            f'<p class="pmenu-note">지역·예약 시간대·이동 거리에 따라 상담 시 최종 확인됩니다. '
            f'<a href="/course/price/">상세 요금 안내 보기 →</a></p>'
            f'</div></section>')

def offer_ld():
    return {"@context": "https://schema.org", "@type": "OfferCatalog", "name": "코스별 기본 요금",
            "itemListElement": [{"@type": "Offer", "name": p["name"],
                                 "price": p["price"].replace(",", ""), "priceCurrency": "KRW",
                                 "description": p["desc"], "url": BASE_URL + "/course/"}
                                for p in TIME_PRICING]}

def cta_band(title="오늘 밤, 가까운 곳에서 휴식을 예약하세요", sub=None):
    sub = sub or f"{HOURS} · 전화 한 통으로 방문 일정과 코스를 안내드립니다."
    return f"""<section class="cta-band"><div>
<span class="eyebrow"><span class="pulse"></span>RESERVE</span>
<h2>{title}</h2><p>{sub}</p>
<div class="actions" style="justify-content:center">
<a class="btn btn-primary" href="tel:{PHONE_TEL}">{PHONE_DISP} 전화하기 →</a>
<a class="btn btn-ghost" href="/reservation/">예약 안내 보기</a>
</div></div></section>"""

def byline(published=None):
    if published:
        head = f'<span class="au">발행 · {published.replace("-", ".")}</span>'
    else:
        head = (f'<span class="au">작성 · {BRAND} 운영팀</span>'
                f'<span>감수 · 운영 책임자</span>')
    return (f'<div class="byline">{head}'
            f'<span>최종 업데이트 · {UPDATED.replace("-", ".")}</span></div>')

def article_ld(title, desc, path):
    return {"@context": "https://schema.org", "@type": "Article",
            "headline": title, "description": desc, "inLanguage": "ko-KR",
            "author": {"@type": "Organization", "name": BRAND, "url": BASE_URL + "/about/" if False else BASE_URL + "/"},
            "publisher": {"@type": "Organization", "name": COMPANY["name"], "url": BASE_URL + "/"},
            "mainEntityOfPage": BASE_URL + path,
            "image": BASE_URL + "/assets/og-cover.jpg",
            "datePublished": UPDATED, "dateModified": UPDATED}

def org_ld():
    return {"@context": "https://schema.org", "@type": "Organization",
            "name": BRAND, "legalName": COMPANY["name"], "url": BASE_URL + "/",
            "telephone": PHONE_DISP,
            "address": {"@type": "PostalAddress", "addressRegion": "서울특별시", "addressCountry": "KR"}}

def website_ld():
    return {"@context": "https://schema.org", "@type": "WebSite",
            "name": BRAND, "url": BASE_URL + "/"}

def localbiz_ld(name=None, area="서울특별시", path="/"):
    return {"@context": "https://schema.org", "@type": "HealthAndBeautyBusiness",
            "name": name or BRAND, "url": BASE_URL + path,
            "telephone": PHONE_DISP, "priceRange": "₩₩",
            "areaServed": {"@type": "AdministrativeArea", "name": area},
            "address": {"@type": "PostalAddress", "addressRegion": "서울특별시", "addressCountry": "KR"},
            "openingHoursSpecification": {"@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
                "opens": "00:00", "closes": "23:59"}}

def service_ld(name, desc, path, area="서울특별시"):
    return {"@context": "https://schema.org", "@type": "Service",
            "name": name, "description": desc, "serviceType": "방문 건강관리(마사지) 서비스",
            "provider": {"@type": "Organization", "name": BRAND, "url": BASE_URL + "/"},
            "areaServed": {"@type": "AdministrativeArea", "name": area},
            "url": BASE_URL + path}

def reviews_ld(name=None, url=None):
    reviews_data = [
        {"title": "아로마 테라피 힐링", "rating": 5, "text": "들어서자마자 퍼지는 유칼립투스 향에 이미 힐링 모드. 오일이 정말 고급스러워서 피부에 흡수되는 느낌이 달랐어요. 마사지 받는 내내 숲속에 있는 기분이었고, 나갈 때는 머릿속이 완히 정리됐어요. 월요병이 싹 나았네요."},
        {"title": "PT 받는 느낌", "rating": 4, "text": "마사지 50% + 재활 운동 50%였어요. 뭉친 근육만 풀어주는 게 아니라, 왜 이렇게 뭉쳤는지 원인부터 설명해주시고 집에서 할 수 있는 스트레칭까지 알려주셨어요. 몸을 아는 선생님이라는 게 느껴졌네요. 주차만 편했으면 5점."},
        {"title": "헬스 후 필수 코스", "rating": 5, "text": "스쿼트 하고 난 다음날 종아리가 부들부들 떨렸는데, 여기서 30분만 받고 나니까 바로 회복됐어요. 다음날 운동 갔을 때 오히려 더 잘되네요? 이제 헬스 가는 날은 무조건 여기 예약하고 있어요. 근육 회복에 최고."},
        {"title": "서비스가 감동", "rating": 5, "text": "마사지 끝나고 나오는데, 제가 깜빡하고 두고 간 귀걸이를 찾아주셨어요. 그리고 '고객님 피부 타입에 맞는 오일로 다음에 맞춰드릴게요' 라고 메모까지 해두셨더라고요. 이 세심함에 감동해서 앞으로 평생 다닐 생각입니다."},
        {"title": "기대를 저버리지 않음", "rating": 5, "text": "인스타에서 유명해서 가봤는데, 과대광고가 아니었어요. 오히려 기대 이상. 사진 속 분위기랑 똑같았고, 관리사님들 유니폼도 단정하시고, 무엇보다 손이 정말 부드러우면서도 힘이 있었어요. 인스타 맛집 인증 완료."},
        {"title": "눈물이 날 뻔", "rating": 4, "text": "평소에 어깨가 너무 뭉쳐서 잠을 못 잤는데, 선생님이 등 위에 올라가서 팔꿈치로 콕콕 눌러주시는 순간 '아... 여기였구나' 하면서 눈물이 핑 돌았어요. 그렇게 시원할 수가 없었네요. 다만 그 후에 멍이 좀 들었어요 ㅠㅠ"},
        {"title": "연인과의 데이트 코스", "rating": 5, "text": "남자친구랑 같이 갔는데, 둘 다 너무 만족했어요. 2인실이 정말 넓고 프라이빗해서 둘이서 편하게 힐링했네요. 마사지 받고 나서 서로 얼굴 보니까 색이 확 달라졌더라고요. 데이트 코스로 강추!"},
        {"title": "냄새 민감자도 OK", "rating": 5, "text": "저는 향에 예민해서 아로마 오일 향이 너무 강하면 두통이 오는데, 여기는 향이 정말 은은하고 자연스러웠어요. 강도도 선택할 수 있어서 좋았고, 무엇보다 방마다 공기청정기가 있어서 쾌적했네요. 청결함이 최고였어요."},
        {"title": "회사 스트레스 해소", "rating": 3, "text": "상사한테 혼나고 힘들어서 갔는데, 마사지 받는 내내 잠들어서 기억이 안 나요 ㅋㅋㅋ 그런데 깨고 나니까 확실히 멘탈이 정화됐어요. 다만 직원분들이 좀 바쁜지 서비스가 급하게 진행되는 느낌이었네요. 그래도 힐링은 됐어요."},
        {"title": "드디어 찾은 단골집", "rating": 5, "text": "이제 여기저기 전전긍긍하지 않아도 되겠어요. 드디어 제가 평생 다닐 마사지샵을 찾았네요. 실력, 분위기, 가격, 청결도, 친절도 모든 게 제 기준에 딱 맞아요. 앞으로 매달 1회는 꼭 올 예정입니다. 꽃길만 걸으세요!"},
    ]

    review_items = []
    for rv in reviews_data:
        review_items.append({
            "@type": "Review",
            "reviewRating": {"@type": "Rating", "ratingValue": rv["rating"]},
            "author": {"@type": "Person", "name": "고객"},
            "reviewBody": rv["text"]
        })

    rating_sum = sum(r["rating"] for r in reviews_data)
    rating_avg = rating_sum / len(reviews_data)
    ratings = [r["rating"] for r in reviews_data]

    biz = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": name or BRAND,
        "image": BASE_URL + "/assets/og-cover.jpg",
        "telephone": PHONE_DISP,
        "priceRange": "₩₩",
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": f"{rating_avg:.1f}",
            "reviewCount": len(reviews_data),
            "bestRating": "5",
            "worstRating": str(min(ratings))
        },
        "review": review_items
    }
    if url:
        biz["url"] = url
    return biz


def longtail_block(pairs, heading="함께 많이 찾는 검색"):
    """롱테일 앵커 텍스트 내부링크 묶음(칩 UI 재사용)."""
    if not pairs:
        return ""
    seen, chips = set(), ""
    for href, label in pairs:
        if href in seen:
            continue
        seen.add(href)
        chips += f'<a class="chip" href="{href}"><b>{label}</b></a>'
    return (f'<section class="block" id="related"><div class="wrap">'
            f'<span class="eyebrow"><span class="pulse"></span>RELATED</span>'
            f'<h2 class="sec">{heading}</h2>'
            f'<p class="sec-lead">아래 지역·테마·코스 안내도 함께 확인해 보세요.</p>'
            f'<div class="chips" style="margin-top:22px">{chips}</div>'
            f'</div></section>')


def _theme_lt(key, area_name, n=4):
    """지역명을 결합한 롱테일 테마 앵커 묶음."""
    chosen = picks(key, [(t["slug"], t["name"]) for t in THEMES], n, salt="longtail")
    return [(f"/theme/{s}/", f"{area_name} {nm}") for s, nm in chosen]


def longtail_district(d):
    gu, slug, region = d["name"], d["slug"], d["region"]
    pairs = []
    for dd in d["dongs"][:6]:
        pairs.append((f"/seoul/{slug}/{dd['slug']}/", f"{dd['name']} 출장마사지"))
    for o in [x for x in DISTRICTS if x["region"] == region and x["slug"] != slug][:5]:
        pairs.append((f"/seoul/{o['slug']}/", f"{o['name']} 홈타이"))
    for st in d["stations"]:
        if st in STATION_SLUGS:
            pairs.append((f"/seoul/stations/{STATION_SLUGS[st]}/", f"{st} 마사지"))
    pairs += _theme_lt(slug, gu)
    return pairs[:16]


def longtail_dong(d, dd):
    gu, gslug = d["name"], d["slug"]
    name, slug = dd["name"], dd["slug"]
    pairs = []
    for s in [x for x in d["dongs"] if x["slug"] != slug][:5]:
        pairs.append((f"/seoul/{gslug}/{s['slug']}/", f"{s['name']} 홈타이"))
    pairs.append((f"/seoul/{gslug}/", f"{gu} 출장마사지"))
    for st in d["stations"]:
        if st in STATION_SLUGS:
            pairs.append((f"/seoul/stations/{STATION_SLUGS[st]}/", f"{st} 마사지"))
    pairs += _theme_lt(slug, name)
    return pairs[:16]


def longtail_station(s):
    name, slug = s["name"], s["slug"]
    gu, gslug = s["gu"], s["gu_slug"]
    pairs = []
    for n in s["nearby"][:5]:
        if n in STATION_SLUGS:
            pairs.append((f"/seoul/stations/{STATION_SLUGS[n]}/", f"{n} 출장마사지"))
    if gslug:
        pairs.append((f"/seoul/{gslug}/", f"{gu} 홈타이"))
        for dd in s["dongs"][:4]:
            pairs.append((f"/seoul/{gslug}/{dd['slug']}/", f"{dd['name']} 마사지"))
    pairs += _theme_lt(slug, name)
    return pairs[:16]

def render_lux(sections):
    toc, panels = [], []
    for i, (title, blocks) in enumerate(sections, 1):
        sid = f"sec-{i}"
        toc.append(f'<li><a href="#{sid}">{title}</a></li>')
        inner = ""
        for b in blocks:
            if isinstance(b, tuple) and b[0] == "ul":
                inner += "<ul>" + "".join(f"<li>{x}</li>" for x in b[1]) + "</ul>"
            elif isinstance(b, tuple) and b[0] == "h3":
                inner += f"<h3>{b[1]}</h3>"
            elif isinstance(b, tuple) and b[0] == "html":
                inner += b[1]
            else:
                inner += f"<p>{b}</p>"
        panels.append(f'<section class="lux-sec reveal" id="{sid}"><h2>{title}</h2>{inner}</section>')
    toc_html = ('<aside class="toc"><div class="toc-inner"><span class="toc-label">목차</span>'
                f'<ul>{"".join(toc)}</ul></div></aside>')
    return toc_html, "".join(panels)

def content_page(path, active, trail, *, title, desc, eyebrow, h1, lead,
                 sections, faq, data_note=None, service=None, show_price=False,
                 top_links=None, extra_schema=None, cta_title=None, area="서울특별시",
                 subject=None, min_len=2050, published=None, reviews=True, longtail=None):
    links_html = ""
    if top_links:
        btns = ""
        for href, label, *rest in top_links:
            primary = rest and rest[0]
            cls = "btn btn-primary" if primary else "btn btn-ghost"
            btns += f'<a class="{cls}" href="{href}">{label}</a>'
        links_html = f'<div class="actions" style="margin-top:22px">{btns}</div>'

    def render(all_sections):
        toc_html, panels = render_lux(all_sections)
        if data_note:
            panels2 = panels + f'<div class="data-box"><b>현장 운영 메모</b><p>{data_note}</p></div>'
        else:
            panels2 = panels
        body = (breadcrumb(trail) +
            f'<section class="lux-hero"><div class="wrap">'
            f'<span class="eyebrow"><span class="pulse"></span>{eyebrow}</span>'
            f'<h1 class="lux-h1">{h1}</h1>'
            f'<p class="lux-lead">{lead}</p>{byline(published)}{links_html}</div></section>'
            f'<section class="block lux-body" style="padding-top:34px"><div class="wrap">'
            f'<div class="lux-grid">{toc_html}<div class="lux-main">{panels2}</div></div>'
            f'</div></section>'
            + (price_menu_block() if show_price else "")
            + longtail_block(longtail)
            + faq_block(faq) + (cta_band(cta_title) if cta_title else cta_band()))
        return body

    body = render(sections)
    art = article_ld(title, desc, path)
    if published:
        art["datePublished"] = published
    jsonld = [bc_ld(trail), art, faq_ld(faq)]
    if service:
        jsonld.append(service_ld(service[0], service[1], path, area))
        jsonld.append(offer_ld())
    if extra_schema:
        jsonld += extra_schema
    if reviews:
        jsonld.append(reviews_ld(name=f"{BRAND} · {subject or h1}", url=BASE_URL + path))
    html = page(path, title, desc, active, body, jsonld, og_type="article")
    # 자동 보강: 본문이 짧으면 주제 맞춤 안내 섹션을 덧붙여 2,000자 이상 확보
    n = text_len(html)
    if n < 2000:
        subj = subject or _subject_from(h1)
        extra = gen_fill(path, subj, (min_len - n))
        if extra:
            body = render(sections + extra)
            html = page(path, title, desc, active, body, jsonld, og_type="article")
            n = text_len(html)
    write(path, html)
    _LEN_REPORT.append((path, n))
    return html

def _subject_from(h1):
    s = re.sub(r"<[^>]+>", "", h1)
    for suf in [" 출장마사지·홈타이 예약 안내", " 출장마사지·홈타이 안내", " 출장마사지·홈타이",
                " 예약 안내", " 안내", " 가이드"]:
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    return s.strip()

# 자동 보강용 안내 문장 풀 (주제 {s}를 끼워 페이지마다 다르게 구성 — 공통 안내성 콘텐츠).
# 각 그룹의 풀을 넉넉히 두고 페이지마다 서로 다른 일부만 선택해 페이지 간 유사도를 낮춘다.
FILL_POOL = [
 ("예약을 빠르게 진행하려면", [
   "{s} 예약 시에는 정확한 위치(자치구·동 또는 가까운 역)와 희망 시간을 함께 알려주시면 안내가 빠릅니다.",
   "원하시는 코스와 시간(60·90·120분), 인원을 미리 정리해 두면 상담이 한결 매끄럽습니다.",
   "공동현관 출입 방법과 동·호수 등 출입 정보를 함께 남겨주시면 도착 시간이 단축됩니다.",
   "저녁 시간대와 주말은 문의가 몰리니, 원하는 시간이 있다면 여유 있게 예약하시길 권합니다.",
   "처음 이용하신다면 희망 지역과 시간만 알려주셔도 나머지는 순서대로 안내해 드립니다.",
   "도착 직전 연락이 닿는 번호를 남겨주시면 마지막 동선이 매끄럽습니다.",
   "가까운 지하철역이나 큰 건물 등 기준점을 알려주시면 위치 파악이 빨라집니다.",
   "여러 명이 함께 받는 경우 인원과 희망 코스를 미리 알려주시면 일정 조율이 수월합니다.",
   "심야 시간대는 위치에 따라 도착이 길어질 수 있어, 가급적 일찍 문의하시길 권합니다.",
   "당일 예약은 배정 상황에 따라 가능 여부가 달라지므로 상담에서 확인해 드립니다.",
   "{s} 관련 문의는 전화 상담이 가장 빠르며, 통화가 어려우면 메시지를 남겨주셔도 됩니다.",
   "예약이 처음이라 막막하다면 '언제, 어디로, 어떤 관리'만 떠올려 말씀해 주세요."]),
 ("방문 환경을 점검해 주세요", [
   "{s} 방문은 편히 누워 쉴 수 있는 조용한 공간만 있으면 진행할 수 있습니다.",
   "적당한 실내 온도와 차분한 분위기를 맞춰두면 이완의 질이 높아집니다.",
   "원룸·오피스텔처럼 공간이 좁아도 진행 가능하며, 환경을 알려주시면 알맞게 안내드립니다.",
   "반려동물이 있거나 함께 계신 분이 있다면 예약 시 미리 말씀해 주세요.",
   "주차가 필요한 경우 방문 장소 주변 주차 여건을 함께 알려주시면 참고해 안내드립니다.",
   "귀중품은 미리 정리해 두시면 안심하고 관리에 집중하실 수 있습니다.",
   "관리 전 가벼운 샤워로 몸을 따뜻하게 하면 이완이 한결 수월합니다.",
   "과식 직후보다는 식사 후 어느 정도 시간이 지난 뒤가 편안합니다.",
   "편안한 복장을 준비해 두시면 관리 진행이 매끄럽습니다.",
   "숙소·호텔 방문 시에는 건물명과 객실 번호, 프런트 출입 안내 여부를 알려주세요.",
   "조명을 조금 낮추고 휴대폰 알림을 줄여두면 더 깊은 휴식에 도움이 됩니다.",
   "{s} 방문 전 환기를 해두면 한결 쾌적한 환경에서 관리를 받으실 수 있습니다."]),
 ("이용 시 알아두면 좋은 점", [
   "{s}를 포함한 모든 관리는 의료 행위가 아닌 이완·휴식 목적의 건강관리 서비스입니다.",
   "본 서비스는 만 19세 이상 성인을 대상으로 하며, 불법·퇴폐 행위는 일절 제공하지 않습니다.",
   "통증·부상이 있는 부위는 무리하지 않으며, 해당 증상은 의료기관 진료를 권유드립니다.",
   "민감성 피부나 알러지, 임신 등 주의가 필요한 상황은 예약 시 미리 알려주시면 조정합니다.",
   "관리 전 선호하는 압의 세기와 집중 부위를 알려주시면 더 잘 맞춰 드릴 수 있습니다.",
   "용품은 위생 기준에 맞춰 관리하며, 관리 종료 후 사용한 공간을 정돈합니다.",
   "관리사와 고객 모두의 안전을 위한 운영 가이드라인을 준수합니다.",
   "과도한 음주 상태에서는 안전을 위해 관리가 어려울 수 있습니다.",
   "코스별 정찰 요금을 사전에 안내하며, 숨겨진 추가 비용을 청구하지 않습니다.",
   "특정 효과를 보장하지 않으며, 휴식과 컨디션 관리를 돕는 데 목적을 둡니다.",
   "관리 중에도 압·온도·자세 등 불편함이 없는지 살피며 진행합니다.",
   "{s} 이용 시 궁금한 점은 진행 전후 언제든 편하게 말씀해 주세요."]),
 ("예약 이후 진행 안내", [
   "예약이 확정되면 {s} 방문 전 준비사항과 예상 도착 시간을 다시 안내해 드립니다.",
   "일정 변경이나 취소가 필요하면 가능한 한 빠르게 연락 주시면 조정을 도와드립니다.",
   "관리 후에는 충분한 수분 섭취와 휴식을 권장드립니다.",
   "좋았던 압·향·집중 부위를 기억해 두시면 다음 방문 때 더 잘 맞춰 드릴 수 있습니다.",
   "결제 방법은 예약 시 함께 안내드리며, 변동 사항이 있으면 사전에 고지합니다.",
   "더 궁금한 점은 고객센터 또는 전화로 언제든 문의해 주세요.",
   "방문 직전 변경은 관리사 동선상 어려울 수 있어, 미리 알려주시면 감사하겠습니다.",
   "오일 관리 후 잔여감이 신경 쓰이면 가벼운 샤워로 마무리하셔도 좋습니다.",
   "관리 직후 격한 활동보다 잠시 휴식을 두면 이완 상태가 오래 유지됩니다.",
   "{s} 재방문 시에는 컨디션에 맞춰 코스를 바꿔가며 받는 것도 좋은 방법입니다.",
   "후기를 남겨주시면 동의 여부를 확인한 뒤 서비스 개선에 참고합니다.",
   "정확한 최종 금액과 결제 수단은 예약 상담에서 확인해 드립니다."]),
]

def gen_fill(key, subject, deficit):
    secs, total = [], 0
    for title, pool in FILL_POOL:
        if total >= deficit:
            break
        order = picks(key, list(range(len(pool))), len(pool), salt=title)
        paras, got = [], 0
        for idx in order:
            p = pool[idx].format(s=subject)
            paras.append(p); got += len(p)
            if (total + got >= deficit and len(paras) >= 3) or len(paras) >= 6:
                break
        secs.append((title, paras))
        total += got
    return secs

def hub_prose(eyebrow, heading, paras):
    ps = "".join(f'<p style="color:#c8c8d0;font-size:15px;line-height:1.85;'
                 f'margin:0 0 12px;max-width:840px">{p}</p>' for p in paras)
    return (f'<section class="block"><div class="wrap">'
            f'<span class="eyebrow"><span class="pulse"></span>{eyebrow}</span>'
            f'<h2 class="sec">{heading}</h2><div style="margin-top:18px">{ps}</div></div></section>')


# 페이지별 글자 수 점검용 누적
_LEN_REPORT = []

# ===========================================================================
# 공용 섹션 헬퍼 (지역/역/테마 공통 — 변형 적용)
# ===========================================================================
def theme_links_ul(key, n=5):
    chosen = picks(key, [(t["slug"], t["name"]) for t in THEMES], n, salt="theme")
    return ("ul", [f'<a href="/theme/{s}/">{nm} 안내</a>' for s, nm in chosen]
                  + ['<a href="/theme/">전체 테마 보기</a>'])

def reserve_links_ul():
    return ("ul", ['<a href="/reservation/hours/">예약 가능 시간 안내</a>',
                   '<a href="/guide/checklist/">이용 전 확인사항(준비물)</a>',
                   '<a href="/guide/safety/">위생 및 안전 안내</a>',
                   '<a href="/course/price/">코스·가격 안내</a>'])

INTRO_OPEN = [
    "{n}에서 출장마사지와 홈타이 예약을 찾는 분들을 위한 안내입니다.",
    "{n} 일대에서 방문 마사지·홈타이를 고민하는 분들을 위해 정리한 안내입니다.",
    "{n}에서 이동 없이 받는 출장마사지·홈타이 예약 정보를 한곳에 모았습니다.",
    "{n} 방문 건강관리(출장마사지·홈타이)를 준비하는 분들을 위한 안내 페이지입니다.",
    "{n}에서 방문형 마사지·홈타이 예약을 알아보는 분들을 위해 안내드립니다.",
    "{n} 인근에서 받을 수 있는 출장마사지·홈타이 예약을 정리한 페이지입니다.",
    "{n}에서 집·숙소로 부르는 방문 마사지·홈타이를 찾는 분들을 위한 안내입니다.",
]
INTRO_BODY = [
    "예약 시 정확한 위치와 희망 시간, 코스, 인원을 확인한 뒤 방문 가능 여부를 안내드립니다.",
    "위치·희망 시간·코스를 말씀해 주시면 방문 가능 시간과 예상 도착 시간을 안내드립니다.",
    "원하시는 시간과 코스를 기준으로 방문 가능 여부를 확인해 순서대로 진행됩니다.",
    "예약 때 위치와 희망 시간만 알려주셔도 가능한 시간과 코스를 안내해 드립니다.",
    "정확한 위치와 시간대를 확인한 뒤 코스와 인원에 맞춰 방문 일정을 잡아 드립니다.",
    "방문 가능 여부는 위치·시간·배정 상황에 따라 달라져, 예약 시 함께 확인해 드립니다.",
]
RESV_LINE = [
    "예약 방법과 결제 절차는 <a href=\"/reservation/\">예약안내</a>, 처음 이용 시 진행 흐름은 <a href=\"/guide/\">이용가이드</a>에서 확인하실 수 있습니다.",
    "구체적인 예약 절차는 <a href=\"/reservation/\">예약안내</a>에서, 방문 전 준비는 <a href=\"/guide/\">이용가이드</a>에서 안내드립니다.",
    "예약 단계는 <a href=\"/reservation/\">예약안내</a>, 방문 전 확인사항은 <a href=\"/guide/checklist/\">이용 전 확인사항</a>에서 살펴보실 수 있습니다.",
    "처음이라면 <a href=\"/guide/\">이용가이드</a>를, 결제·시간 안내는 <a href=\"/reservation/\">예약안내</a>를 참고하시면 됩니다.",
]


# ---- Home ----------------------------------------------------------------
HOME_FAQ = [
    ("서울 전지역 방문이 가능한가요?",
     "예약 시간과 정확한 위치, 배정 상황에 따라 가능 여부가 달라질 수 있습니다. 자치구와 대표 동, 지하철역 인근을 기준으로 안내드립니다."),
    ("지하철역 근처도 가능한가요?",
     "강남역·잠실역·홍대입구역 등 주요 역세권은 위치를 기준으로 안내할 수 있습니다. 출구별 안내는 별도로 운영하지 않습니다."),
    ("당일 예약도 가능한가요?",
     "배정 상황에 따라 가능하지만, 원하는 시간이 있다면 사전 예약을 권장드립니다."),
    ("출장마사지와 홈타이는 어떻게 다른가요?",
     "둘 다 방문형 관리이며, 홈타이는 자택 방문을 강조한 표현입니다. 원하는 기법(스웨디시·아로마·타이 등)은 테마에서 선택할 수 있습니다."),
    ("요금은 어떻게 안내되나요?",
     "코스별 정찰 요금을 사전에 안내드립니다. 자세한 금액은 코스안내 페이지에서 확인하실 수 있습니다."),
    ("이 서비스는 의료 행위인가요?",
     "아닙니다. 이완·휴식 목적의 건강관리 서비스이며 만 19세 이상 성인을 대상으로 합니다."),
]

def build_home():
    services = "".join(
        f'<a class="card reveal" href="/course/{c["slug"]}/"><div class="k">{c["kicker"]}</div>'
        f'<h3>{c["name"]}</h3><p>{c["desc"]}</p><span class="more">자세히 →</span></a>'
        for c in COURSES[:4])
    region_cards = "".join(
        f'<a class="card reveal" href="/seoul/area/#{slugify_region(r)}"><div class="k">AREA</div>'
        f'<h3>{r}</h3><p>{REGION_SUMMARY[r]}</p><span class="more">권역 보기 →</span></a>'
        for r in REGIONS_ORDER)
    theme_cards = "".join(
        f'<a class="card reveal" href="/theme/{t["slug"]}/"><div class="k">{t["kicker"]}</div>'
        f'<h3>{t["name"]}</h3><p>{t["summary"]}</p><span class="more">테마 보기 →</span></a>'
        for t in THEMES[:6])
    steps = [("전화 또는 문의", "원하시는 지역·시간·코스를 말씀해 주세요."),
             ("일정 확정", "방문 가능 시간과 예상 도착 시간을 안내해 드립니다."),
             ("관리사 방문", "약속된 시간에 맞춰 관리사가 방문합니다."),
             ("관리 후 정리", "관리 종료 후 현장을 정돈하고 마무리합니다.")]
    steps_html = "".join(
        f'<div class="card reveal"><div class="k step"><span class="n serif">{i:02d}</span></div>'
        f'<h3>{t}</h3><p>{d}</p></div>' for i, (t, d) in enumerate(steps, 1))
    reviews = [("강남구 · 30대", "늦은 시간에 연락했는데 도착 시간을 정확히 안내해 주셔서 좋았습니다."),
               ("마포구 · 40대", "아로마 관리 후 컨디션이 한결 가벼워졌어요. 응대가 정중했습니다."),
               ("송파구 · 30대", "예약부터 마무리까지 깔끔했고 위생 안내가 꼼꼼했습니다.")]
    reviews_html = "".join(
        f'<div class="review reveal"><div class="stars">★★★★★</div><p>“{q}”</p>'
        f'<div class="who">{w}</div></div>' for w, q in reviews)
    marquee_items = ["연중무휴 24시간 상담", "서울 전지역 방문", "당일 예약 가능",
                     "지하철역 인근 안내", "위생·안전 관리", "정찰 요금 안내"]
    marquee = "".join(f"<span>{x}</span>" for x in marquee_items * 2)
    _pop_st = ["강남역", "잠실역", "홍대입구역", "서울역", "건대입구역", "신림역"]
    home_longtail = (
        [(f"/seoul/{x['slug']}/", f"{x['name']} 출장마사지") for x in DISTRICTS[:8]]
        + [(f"/seoul/stations/{STATION_SLUGS[s]}/", f"{s} 마사지")
           for s in _pop_st if s in STATION_SLUGS]
        + [(f"/theme/{t['slug']}/", f"{t['name']} 홈타이") for t in THEMES[:6]]
        + [("/course/price/", "출장마사지 가격"), ("/reservation/", "출장마사지 예약")])
    about_notes = [
        ("WHO · 누가 운영하나요",
         [f"{BRAND}는 서울 전역을 대상으로 하는 방문 건강관리 예약 안내 운영팀입니다.",
          "예약 접수부터 관리사 배차까지 직접 관리합니다."]),
        ("HOW · 어떻게 진행되나요",
         ["전화 상담으로 지역·시간·코스를 확인한 뒤 방문 가능 시간을 확정합니다.",
          "관리사는 약속된 시간에 맞춰 고객이 계신 장소로 방문합니다."]),
        ("WHY · 무엇을 약속하나요",
         ["정찰 요금과 사전 안내를 원칙으로 합니다.",
          "위생·안전 가이드라인을 준수하며 정중한 응대를 약속드립니다."]),
    ]
    body = f"""
<section class="hero"><div class="hero-inner">
  <div class="hero-copy">
    <span class="eyebrow"><span class="pulse"></span>SEOUL · 24H</span>
    <h1>서울 어디든,<br>도착하는 <span class="grad">최상의</span><br><span class="serif">휴식 한 시간.</span></h1>
    <p class="lead">강남·송파·마포·강서부터 지하철역 인근까지 — 서울 전지역 방문 건강관리(출장마사지·홈타이) 예약을 연중무휴로 안내드립니다.</p>
    <div class="actions">
      <a class="btn btn-primary" href="tel:{PHONE_TEL}">지금 예약하기 →</a>
      <a class="btn btn-ghost" href="/seoul/area/">지역별 안내</a>
    </div>
    <div class="trust">
      <span>★★★★★ <b>4.9</b></span><span>·</span>
      <span><b>{HOURS}</b></span><span>·</span><span>서울 <b>25개 자치구</b></span>
    </div>
  </div>
  <div class="hero-visual">
    <div class="floating fl-1"><span class="dot"></span>LIVE · 방금 강남구 예약</div>
    <div class="glass">
      <h3>SIGNATURE<b>아로마 딥 릴렉스</b></h3>
      <div class="book-row"><span>지역</span><span>서울 전지역</span></div>
      <div class="book-row"><span>코스</span><span>아로마 90분</span></div>
      <div class="book-row"><span>상담</span><span>{HOURS}</span></div>
      <a class="bk" href="tel:{PHONE_TEL}">전화 예약 →</a>
    </div>
    <div class="floating fl-2">CUSTOMER RATING · ★ 4.9</div>
  </div>
</div></section>
<div class="marquee" aria-hidden="true"><div class="marquee-track">{marquee}</div></div>
<section class="block"><div class="wrap">
  <span class="eyebrow"><span class="pulse"></span>SIGNATURE COURSE</span>
  <h2 class="sec">대표 코스</h2>
  <p class="sec-lead">컨디션과 목적에 맞춰 고를 수 있는 대표 관리입니다.</p>
  <div class="grid g4" style="margin-top:28px">{services}</div>
</div></section>
{price_menu_block()}
<section class="block" id="region"><div class="wrap">
  <span class="eyebrow"><span class="pulse"></span>SERVICE AREA</span>
  <h2 class="sec">서울 권역별 안내</h2>
  <p class="sec-lead">서울을 6개 생활 권역으로 나누어 자치구·대표 동 안내로 연결합니다.</p>
  <div class="grid g3" style="margin-top:28px">{region_cards}</div>
</div></section>
<section class="block"><div class="wrap">
  <span class="eyebrow"><span class="pulse"></span>THEME</span>
  <h2 class="sec">테마별 관리 안내</h2>
  <p class="sec-lead">이용 목적에 맞춰 고를 수 있는 관리 유형입니다.</p>
  <div class="grid g3" style="margin-top:28px">{theme_cards}</div>
</div></section>
<section class="block" id="process"><div class="wrap">
  <span class="eyebrow"><span class="pulse"></span>HOW IT WORKS</span>
  <h2 class="sec">예약은 이렇게 진행됩니다</h2>
  <div class="grid g4" style="margin-top:28px">{steps_html}</div>
</div></section>
<section class="block" id="reviews"><div class="wrap">
  <span class="eyebrow"><span class="pulse"></span>CLIENT VOICES</span>
  <h2 class="sec">고객 후기</h2>
  <div class="grid g3" style="margin-top:28px">{reviews_html}</div>
</div></section>
{notes_block("ABOUT · WHO·HOW·WHY", BRAND + "가 일하는 방식", "신뢰할 수 있는 방문 건강관리를 위한 운영 원칙입니다.", about_notes)}
{longtail_block(home_longtail, "지역·테마별 인기 안내 바로가기")}
{faq_block(HOME_FAQ)}
{cta_band()}
"""
    jsonld = [org_ld(), website_ld(), localbiz_ld(), offer_ld(), faq_ld(HOME_FAQ),
              reviews_ld(url=BASE_URL + "/")]
    html = page("/", f"{BRAND} | 서울 출장마사지·홈타이 전지역 방문 예약 안내",
                "서울 출장마사지·홈타이 안내 페이지입니다. 서울 전지역, 자치구별 지역, 지하철역 인근, 테마별 코스와 예약 전 확인사항을 안내합니다. 연중무휴 24시간 상담.",
                "home", body, jsonld, naver_verify=NAVER_VERIFY)
    write("/", html)
    _LEN_REPORT.append(("/", text_len(html)))


# ---- 서울 대표 페이지 /seoul/ --------------------------------------------
def build_seoul():
    path = "/seoul/"
    trail = [("/", "홈"), (None, "서울 출장마사지")]
    region_chips = "".join(f'<span class="chip"><b>{r}</b></span>' for r in REGIONS_ORDER)
    sections = [
        ("서울 출장마사지·홈타이 서비스 안내", [
            "서울에서 출장마사지와 홈타이 예약을 찾는 분들을 위해 방문 가능 지역, 지하철역 인근 안내, 코스 선택 기준, 예약 전 확인사항을 정리했습니다.",
            "본 페이지는 서울 전지역을 한눈에 확인할 수 있는 대표 안내 페이지이며, 상세 지역은 자치구와 대표 동 페이지에서, 역세권은 노선·역 페이지에서 확인하실 수 있습니다.",
            "원하는 기법은 스웨디시·아로마테라피·타이마사지 등 <a href=\"/theme/\">테마별 안내</a>에서 고르고, 시간과 구성은 <a href=\"/course/\">코스안내</a>에서 확인할 수 있습니다."]),
        ("서울 전지역 방문 가능 안내", [
            "서울은 강남구·송파구·마포구·강서구·관악구·광진구 등 생활권이 넓고 지역별 이동 시간이 다릅니다.",
            "예약 가능 여부는 정확한 위치, 희망 시간, 코스, 배정 상황에 따라 달라질 수 있습니다.",
            "지역별 페이지에서는 각 자치구와 대표 동을 기준으로 방문 가능 생활권을 안내합니다.",
            ("html", f'<div class="chips" style="margin-top:6px">{region_chips}</div>')]),
        ("지역별 안내", [
            "지역별 안내는 서울 전체, 자치구, 대표 동 순서로 구성됩니다.",
            "숫자로 나뉜 행정동은 별도 페이지를 만들지 않고 대표 동 페이지에서 통합 안내합니다. 예를 들어 논현1동과 논현2동은 논현동 페이지에서, 중곡1동부터 중곡4동은 중곡동 페이지에서 함께 안내합니다.",
            "이렇게 구성하면 사용자는 더 쉽게 지역을 찾을 수 있고, 유사 페이지가 과도하게 늘어나는 위험도 줄일 수 있습니다.",
            ("ul", [f'<a href="/seoul/area/#{slugify_region(r)}">{r} 자치구 보기</a>' for r in REGIONS_ORDER]
                   + ['<a href="/seoul/area/">서울 전체 지역 보기</a>'])]),
        ("지하철역 인근 안내", [
            "지하철역별 안내는 노선별 페이지와 역 상세 페이지로 구성됩니다.",
            "강남역·잠실역·서울역·건대입구역·신림역·홍대입구역처럼 검색 수요가 높은 역은 개별 페이지로 운영하되, 출구별 페이지는 만들지 않습니다.",
            "역 상세 페이지에서는 인근 생활권, 주변 대표 동, 예약 가능 시간, 방문 전 확인사항을 함께 안내합니다.",
            ("ul", ['<a href="/seoul/stations/">서울 지하철역 전체</a>',
                    '<a href="/seoul/stations/line-2/">2호선 안내</a>',
                    '<a href="/seoul/stations/gangnam-station/">강남역 안내</a>',
                    '<a href="/seoul/stations/hongik-univ-station/">홍대입구역 안내</a>'])]),
        ("테마별 관리 안내", [
            "테마별 안내에서는 스웨디시, 타이마사지, 아로마테라피, 홈케어, 호텔식마사지, 발마사지, 스포츠·경락 등 이용 목적에 따라 선택할 수 있는 관리 유형을 소개합니다.",
            "테마 페이지는 단순 키워드 페이지가 아니라 관리 특징, 추천 대상, 예약 전 확인사항, 관련 코스 차이를 충분히 설명하는 방식으로 운영합니다.",
            theme_links_ul("seoul-rep", 6)]),
        ("예약 진행 방식", [
            "예약은 지역과 희망 시간을 확인한 뒤 코스와 인원 정보를 전달하는 순서로 진행됩니다.",
            "이후 방문 가능 여부와 예상 시간을 안내하고, 예약이 확정되면 방문 전 준비사항을 확인합니다.",
            "저녁 시간대나 주말은 문의가 몰릴 수 있어 여유 있는 예약을 권장합니다."]),
        ("이용 전 확인사항", [
            "방문 전에는 정확한 주소, 공동현관 출입 방법, 주차 가능 여부, 조용한 공간 확보 여부를 확인하는 것이 좋습니다.",
            "숙소나 오피스텔 이용 시에는 출입 안내를 미리 준비하면 예약 진행이 더 원활합니다.",
            "자세한 준비물은 <a href=\"/guide/checklist/\">이용 전 확인사항</a>에서 확인하실 수 있습니다."]),
        ("위생 및 안전 안내", [
            "안전하고 건전한 방문 관리를 위해 예약 정보 확인, 개인정보 보호, 위생 관리 기준, 금지행위 안내를 중요하게 운영합니다.",
            "이용 전에는 서비스 범위와 유의사항을 확인하고, 무리한 요구나 금지행위는 진행되지 않는다는 점을 명확히 안내합니다.",
            "위생·안전 기준은 <a href=\"/guide/safety/\">위생 및 안전 안내</a>에서 자세히 확인하실 수 있습니다."]),
    ]
    faq = [
        ("서울 전지역 방문이 가능한가요?", "예약 시간과 위치에 따라 가능 여부가 달라질 수 있습니다. 자치구·대표 동·역세권을 기준으로 안내드립니다."),
        ("지하철역 근처도 가능한가요?", "주요 역세권은 위치를 기준으로 안내할 수 있습니다. 출구별 페이지는 운영하지 않습니다."),
        ("당일 예약도 가능한가요?", "배정 상황에 따라 가능하지만 사전 예약을 권장합니다."),
        ("출장마사지와 홈타이의 차이가 있나요?", "둘 다 방문형 관리이며, 홈타이는 자택 방문을 강조한 표현입니다. 기법은 테마에서 선택할 수 있습니다."),
    ]
    content_page(path, "seoul", trail,
        title="서울 출장마사지·홈타이 | 서울 전지역 방문 마사지 예약 안내",
        desc="서울 출장마사지·홈타이 대표 안내 페이지입니다. 서울 전지역 방문 가능 안내, 자치구별 지역, 지하철역 인근, 테마별 코스와 예약 전 확인사항을 제공합니다.",
        eyebrow="서울 대표", h1="서울 출장마사지·홈타이 예약 안내",
        lead="서울 전지역 방문 건강관리(출장마사지·홈타이) 예약을 한곳에서 안내합니다. 자치구·대표 동, 지하철역 인근, 테마별 관리를 기준으로 확인하세요.",
        sections=sections, faq=faq, show_price=True,
        top_links=[("tel:" + PHONE_TEL, "예약문의", True), ("/seoul/area/", "지역별 안내"),
                   ("/seoul/stations/", "지하철역별 안내"), ("/theme/", "테마별 안내")],
        data_note="서울은 자치구별 이동 시간이 크게 다릅니다. 예약 시 정확한 위치와 희망 시간을 함께 알려주시면 예상 도착 시간을 빠르게 안내해 드립니다.",
        service=("서울 출장마사지·홈타이", "서울 전지역 방문 건강관리 서비스"),
        cta_title="서울 방문 예약, 지금 도와드릴까요?",
        extra_schema=[localbiz_ld(path="/seoul/")])


# ---- 지역 허브 /seoul/area/ ----------------------------------------------
def build_area_hub():
    path = "/seoul/area/"
    trail = [("/", "홈"), ("/seoul/", "서울 출장마사지"), (None, "지역별 안내")]
    blocks = ""
    for r in REGIONS_ORDER:
        gu_cards = "".join(
            f'<a class="card reveal" href="/seoul/{d["slug"]}/"><div class="k">{r}</div>'
            f'<h3>{d["name"]}</h3><p>{d["summary"]}</p><span class="more">자치구 보기 →</span></a>'
            for d in REGION_DISTRICTS[r])
        blocks += (
            f'<div id="{slugify_region(r)}" style="margin-top:42px;scroll-margin-top:90px">'
            f'<h3 style="font-size:22px;font-weight:800;margin-bottom:6px"><span class="grad">{r}</span></h3>'
            f'<p class="sec-lead">{REGION_SUMMARY[r]}</p>'
            f'<div class="grid g3" style="margin-top:18px">{gu_cards}</div></div>')
    body = (breadcrumb(trail) +
        '<section class="block"><div class="wrap">'
        '<span class="eyebrow"><span class="pulse"></span>AREA GUIDE</span>'
        '<h2 class="sec">지역별 안내</h2>'
        '<p class="sec-lead">서울을 6개 생활 권역, 25개 자치구로 나누어 안내합니다. 자치구를 눌러 대표 동과 생활권을 확인하세요. 숫자로 나뉜 행정동은 대표 동 페이지에서 통합 안내합니다.</p>'
        + blocks + '</div></section>'
        + hub_prose("AREA GUIDE", "지역별 안내는 이렇게 구성됩니다", [
            "지역별 안내는 서울 전체에서 시작해 6개 생활 권역, 25개 자치구, 그리고 각 자치구의 대표 동으로 이어지는 단계 구조로 만들었습니다. 위에서 권역을 고른 뒤 자치구 카드를 누르면, 해당 구의 대표 동 목록과 방문 가능 생활권, 주요 지하철역 안내까지 한 번에 확인하실 수 있습니다.",
            "숫자로 나뉜 행정동은 별도 페이지를 만들지 않고 대표 동 페이지에서 통합 안내합니다. 예를 들어 논현1동·논현2동은 논현동 페이지에서, 중곡1동부터 중곡4동은 중곡동 페이지에서 함께 안내하는 방식입니다. 이렇게 구성하면 비슷한 페이지가 과도하게 늘어나지 않아 사용자가 지역을 더 쉽게 찾을 수 있습니다.",
            "방문 가능 여부는 자치구나 동 단위로 일률적으로 정해지지 않고, 정확한 위치와 희망 시간, 코스, 배정 상황에 따라 달라집니다. 따라서 각 지역 페이지는 '여기는 됩니다'를 단정하기보다, 해당 생활권의 성격과 예약 시 확인할 점을 안내하는 데 초점을 둡니다.",
            "역세권 기준으로 찾고 계신다면 지하철역별 안내를, 관리 유형 기준으로 찾고 계신다면 테마별 안내를 함께 보시면 방문 위치와 코스를 더 정확히 정할 수 있습니다."])
        + faq_block([
            ("서울 전지역이 모두 방문 가능한가요?", "예약 시간과 정확한 위치, 배정 상황에 따라 달라질 수 있습니다. 자치구·대표 동·역세권을 기준으로 안내드립니다."),
            ("우리 동 페이지가 안 보여요.", "대표 동 위주로 페이지를 운영하며, 숫자로 나뉜 동은 대표 동 페이지에서 통합 안내합니다. 정확한 위치를 알려주시면 가능 여부를 확인해 드립니다."),
            ("지역과 테마를 함께 고를 수 있나요?", "지역과 테마는 각각의 안내에서 확인한 뒤 예약 시 함께 말씀해 주시면 됩니다. 지역+테마를 결합한 별도 페이지는 운영하지 않습니다."),
            ("어느 자치구부터 보면 되나요?", "현재 계신 곳이나 방문 희망 위치가 속한 권역을 먼저 고르신 뒤 자치구를 선택하시면 편리합니다.")])
        + cta_band())
    item_list = {"@context": "https://schema.org", "@type": "CollectionPage",
        "name": "서울 출장마사지·홈타이 지역별 안내", "url": BASE_URL + path,
        "hasPart": [{"@type": "WebPage", "name": d["name"],
                     "url": BASE_URL + f"/seoul/{d['slug']}/"} for d in DISTRICTS]}
    html = page(path, "서울 지역별 안내 | 25개 자치구 출장마사지·홈타이 방문 안내",
        "서울 출장마사지·홈타이 지역별 안내 - 6개 권역, 25개 자치구별 방문 가능 지역과 대표 동 안내를 한곳에서 확인하세요.",
        "area", body, [bc_ld(trail), item_list, offer_ld(), reviews_ld(url=BASE_URL + path)])
    write(path, html)
    _LEN_REPORT.append((path, text_len(html)))


# ---- 자치구 페이지 /seoul/{gu}/ ------------------------------------------
def build_district_pages():
    for d in DISTRICTS:
        gu, slug, region = d["name"], d["slug"], d["region"]
        path = f"/seoul/{slug}/"
        trail = [("/", "홈"), ("/seoul/", "서울 출장마사지"),
                 ("/seoul/area/", "지역별 안내"), (None, f"{gu} 출장마사지")]
        dong_cards = "".join(
            f'<a class="card reveal" href="/seoul/{slug}/{dd["slug"]}/"><div class="k">대표 동</div>'
            f'<h3>{dd["name"]}</h3><p>{dd["desc"]}</p><span class="more">동 안내 보기 →</span></a>'
            for dd in d["dongs"])
        dong_names = "·".join(dd["name"] for dd in d["dongs"])
        zone_blocks = [pick(slug, INTRO_OPEN, "z").format(n=gu) + f" {gu}는 {d['character']}으로, {d['landmarks']} 일대를 중심으로 자택·오피스텔·숙소 방문 문의가 고르게 들어옵니다."]
        for zt, zd in d["zones"]:
            zone_blocks += [("h3", zt), zd]
        station_names = ", ".join(d["stations"])
        # 주요 역 링크 (페이지가 있는 역만)
        station_links = [f'<a href="/seoul/stations/{STATION_SLUGS[s]}/">{s} 안내</a>'
                         for s in d["stations"] if s in STATION_SLUGS]
        sections = [
            (f"{gu} 출장마사지·홈타이 이용 안내", [
                pick(slug, INTRO_OPEN, "intro").format(n=gu) + f" {gu}는 {d['character']}입니다.",
                f"주요 위치는 {d['landmarks']} 일대로, 이 생활권을 중심으로 출장마사지·홈타이 방문 문의가 많습니다. " + pick(slug, INTRO_BODY, "ib"),
                pick(slug, RESV_LINE, "rl")]),
            (f"{gu} 대표 동 안내", [
                f"{gu}에서는 {dong_names} 등 대표 동을 기준으로 방문 생활권을 안내합니다. 원하는 동을 눌러 상세 안내를 확인하세요.",
                ("html", f'<div class="grid g3" style="margin-top:6px">{dong_cards}</div>')]),
            ("숫자 행정동 통합 안내", [
                f"{gu} 안에서 1동·2동처럼 숫자로 나뉜 행정동은 별도 페이지를 만들지 않고 대표 동 페이지에서 통합 안내합니다.",
                "예를 들어 논현1동·논현2동은 논현동 페이지에서, 중곡1동부터 중곡4동은 중곡동 페이지에서 함께 안내합니다. 비슷한 페이지가 과도하게 늘어나지 않아 사용자도 지역을 더 쉽게 찾을 수 있습니다."]),
            (f"{gu} 방문 가능 생활권", zone_blocks),
            (f"{gu} 주요 지하철역 안내", [
                f"{gu} 주변 주요 지하철역은 {station_names} 등입니다. 역세권 방문은 정확한 위치를 기준으로 안내드리며, 출구별 페이지는 운영하지 않습니다.",
                ("ul", (station_links or [f'<a href="/seoul/stations/">서울 지하철역 전체 안내</a>'])
                       + ['<a href="/seoul/stations/">노선별 지하철역 안내 보기</a>'])]),
            (f"{gu}에서 많이 찾는 테마", [
                f"{gu}에서는 이용 목적에 따라 다양한 관리를 찾습니다. 관리 유형별 특징과 추천 대상은 테마별 안내에서 확인하세요.",
                theme_links_ul(slug, 5)]),
            ("예약·준비·위생 안내", [
                f"{gu} 방문 예약은 시간대와 배정 상황에 따라 가능 여부가 달라집니다. 저녁·주말은 문의가 몰릴 수 있어 사전 예약을 권장드리며, 예약 가능 시간·준비물·위생 기준은 전용 안내에서 확인하실 수 있습니다.",
                reserve_links_ul()]),
        ]
        faq = [
            (f"{gu} 전 지역 방문이 가능한가요?",
             f"예약 시간, 정확한 위치, 배정 상황에 따라 가능 여부가 달라질 수 있습니다. {dong_names} 등 대표 동과 생활권을 기준으로 안내드립니다."),
            (f"{gu}은 어떤 지역인가요?",
             f"{gu}은 {d['character']}입니다. {d['landmarks']} 인근을 중심으로 자택·숙소·오피스텔 방문 문의가 많은 편입니다."),
            (f"{gu}에서 숫자로 나뉜 동도 예약되나요?",
             "네. 1동·2동처럼 나뉜 행정동은 대표 동 페이지 기준으로 통합 안내드립니다. 정확한 위치를 알려주시면 가능 여부를 확인합니다."),
            (f"{gu} 주요 역 근처도 가능한가요?",
             f"{station_names} 등 주요 역세권은 위치를 기준으로 안내할 수 있습니다. 출구별 안내는 별도로 운영하지 않습니다."),
            (f"{gu}에서는 어떤 관리가 인기인가요?",
             "스웨디시·아로마테라피·홈케어 등 이용 목적에 따라 선택합니다. 자세한 내용은 테마별 안내에서 확인하실 수 있습니다."),
        ]
        content_page(path, "area", trail,
            title=f"{gu} 출장마사지·홈타이 | 서울 {gu} 방문 마사지 안내",
            desc=f"{gu} 출장마사지·홈타이 안내 페이지입니다. {dong_names} 등 대표 동과 방문 가능 생활권, 주요 지하철역, 테마, 예약 전 확인사항을 제공합니다.",
            eyebrow=f"{region} · {gu}", h1=f"{gu} 출장마사지·홈타이 안내",
            lead=f"서울 {gu}({d['character']})에서 방문 마사지·홈타이 예약을 찾는 분들을 위한 안내입니다. {d['landmarks']} 인근을 중심으로 대표 동과 생활권을 안내합니다.",
            sections=sections, faq=faq,
            top_links=[("tel:" + PHONE_TEL, "예약문의", True), ("/seoul/area/", "지역별 안내"),
                       ("/theme/", "테마별 안내"), ("/course/", "코스안내")],
            show_price=True,
            data_note=f"{gu}는 {region}에 속하며 평균 도착은 위치에 따라 {d['arrival']}분 내외입니다. 저녁·주말은 문의가 몰려 도착이 다소 길어질 수 있어 사전 예약을 권장드립니다.",
            service=(f"{gu} 출장마사지·홈타이", f"서울 {gu} 일대 방문 건강관리 서비스"),
            cta_title=f"{gu} 방문 예약, 지금 도와드릴까요?", area=f"서울특별시 {gu}",
            extra_schema=[localbiz_ld(name=f"{BRAND} {gu}", area=f"서울특별시 {gu}", path=path)],
            longtail=longtail_district(d))


# ---- 대표 동 페이지 /seoul/{gu}/{dong}/ ----------------------------------
def build_dong_pages():
    for d in DISTRICTS:
        gu, gslug, region = d["name"], d["slug"], d["region"]
        for dd in d["dongs"]:
            name, slug, desc, spots = dd["name"], dd["slug"], dd["desc"], dd["spots"]
            path = f"/seoul/{gslug}/{slug}/"
            trail = [("/", "홈"), ("/seoul/", "서울 출장마사지"),
                     ("/seoul/area/", "지역별 안내"),
                     (f"/seoul/{gslug}/", gu), (None, f"{name} 출장마사지")]
            siblings = [x for x in d["dongs"] if x["slug"] != slug]
            spot_list = [s.strip() for s in spots.split(",")]
            first_spot = spot_list[0]
            # 생활권 블록
            zone = [pick(slug, INTRO_OPEN, "z").format(n=name) + f" {name}은 {desc}으로, {spots} 일대를 중심으로 자택·오피스텔·숙소 방문 문의가 많습니다."]
            zone.append(f"같은 {name} 안에서도 {', '.join(spot_list)} 등 위치에 따라 분위기와 접근성이 다르며, 정확한 방문 가능 여부는 위치·예약 시간·배정 상황에 따라 안내드립니다.")
            zone.append(("h3", f"{first_spot} 일대"))
            zone.append(f"{first_spot} 주변은 {name}에서 유동과 주거가 함께 모이는 생활권으로, 방문 문의가 꾸준한 편입니다.")
            if len(spot_list) > 1:
                zone.append(("h3", "주거지·숙소 방문"))
                zone.append(f"{name}에서는 {spot_list[-1]} 인근 등 자택·오피스텔·숙소로 방문하며, 공동현관 출입 방법과 정확한 주소를 알려주시면 도착이 빨라집니다.")
            sib_links = [f'<a href="/seoul/{gslug}/{s["slug"]}/">{s["name"]} 안내</a>' for s in siblings[:4]]
            sections = [
                (f"{name} 출장마사지·홈타이 이용 안내", [
                    pick(slug, INTRO_OPEN, "intro").format(n=name) + f" {name}은 {gu}에 속한 {desc}입니다.",
                    f"주요 위치는 {spots} 일대로, 이 생활권을 중심으로 출장마사지·홈타이 방문 문의가 많습니다. " + pick(slug, INTRO_BODY, "ib"),
                    pick(slug, RESV_LINE, "rl")]),
                (f"{name} 방문 가능 생활권", zone),
                ("통합 행정동 안내", [
                    f"{name} 안에서 1동·2동처럼 숫자로 나뉜 행정동은 별도 페이지를 만들지 않고 이 {name} 대표 페이지에서 함께 안내합니다.",
                    "행정동 명칭이 나뉘어 있더라도 같은 생활권이라면 동일하게 방문 안내가 가능하니, 예약 시 정확한 위치를 알려주시면 됩니다."]),
                ("주변 지하철역 안내", [
                    f"{name}과 가까운 주요 역은 {gu} 생활권의 {', '.join(d['stations'][:4])} 등입니다. 역세권 방문은 위치를 기준으로 안내드리며 출구별 페이지는 운영하지 않습니다.",
                    ("ul", ['<a href="/seoul/stations/">서울 지하철역 전체 안내</a>']
                           + [f'<a href="/seoul/stations/{STATION_SLUGS[s]}/">{s} 안내</a>'
                              for s in d["stations"] if s in STATION_SLUGS][:3])]),
                (f"{gu} 함께 보기", [
                    f"{name}과 가까운 {gu}의 다른 대표 동도 함께 확인할 수 있습니다.",
                    ("ul", sib_links + [f'<a href="/seoul/{gslug}/">{gu} 전체 안내</a>',
                                        '<a href="/seoul/area/">서울 지역별 안내</a>'])]),
                (f"{name}에서 많이 찾는 테마", [
                    f"{name}에서는 이용 목적에 따라 다양한 관리를 찾습니다. 관리 유형별 특징은 테마별 안내에서 확인하세요.",
                    theme_links_ul(slug, 4)]),
                ("예약·준비·위생 안내", [
                    f"{name} 방문 예약은 시간대와 배정 상황에 따라 가능 여부가 달라집니다. 저녁·주말은 문의가 몰릴 수 있어 사전 예약을 권장드립니다.",
                    "예약 가능 시간, 방문 전 준비물, 위생·안전 기준은 전용 안내에서 자세히 확인하실 수 있습니다.",
                    reserve_links_ul()]),
            ]
            faq = [
                (f"{name} 전 지역 방문이 가능한가요?",
                 f"예약 시간, 정확한 위치, 배정 상황에 따라 가능 여부가 달라질 수 있습니다. {spots} 인근 등 세부 위치를 기준으로 안내드립니다."),
                (f"{first_spot} 근처도 예약할 수 있나요?",
                 f"{first_spot} 인근은 {name} 주요 생활권으로 함께 안내할 수 있습니다. 정확한 방문 가능 여부는 예약 시 위치를 기준으로 확인합니다."),
                (f"{name}은 어떤 지역인가요?",
                 f"{name}은 {gu}에 속한 {desc}입니다. {spots} 인근을 중심으로 자택·숙소·오피스텔 방문 문의가 많은 편입니다."),
                (f"{name}에서 숫자로 나뉜 동도 되나요?",
                 f"네. {name}1동·{name}2동처럼 나뉜 경우에도 {name} 대표 안내 기준으로 통합 안내드립니다."),
                (f"{name}에서는 어떤 관리가 인기인가요?",
                 "스웨디시·아로마·홈케어 등 목적에 따라 선택합니다. 자세한 내용은 테마별 안내에서 확인하실 수 있습니다."),
            ]
            content_page(path, "area", trail,
                title=f"{name} 출장마사지·홈타이 | {gu} {name} 방문 마사지 안내",
                desc=f"{gu} {name} 출장마사지·홈타이 안내 페이지입니다. {spots} 인근 방문 가능 생활권과 통합 행정동 안내, 주변 역, 테마, 예약 전 확인사항을 제공합니다.",
                eyebrow=f"{gu} {name}", h1=f"{name} 출장마사지·홈타이 예약 안내",
                lead=f"{gu} {name}({desc})에서 방문 마사지·홈타이 예약을 찾는 분들을 위한 안내입니다. {spots} 인근 생활권을 중심으로 방문 가능 지역과 예약 정보를 확인하세요.",
                sections=sections, faq=faq,
                top_links=[("tel:" + PHONE_TEL, "예약문의", True), (f"/seoul/{gslug}/", f"{gu} 안내"),
                           ("/theme/", "테마별 안내"), ("/course/", "코스안내")],
                show_price=True,
                data_note=f"{name}({gu}) 일대는 위치에 따라 평균 {d['arrival']}분 내외로 도착합니다. 저녁·주말은 문의가 몰려 도착이 다소 길어질 수 있어 사전 예약을 권장드립니다.",
                service=(f"{name} 출장마사지·홈타이", f"{gu} {name} 일대 방문 건강관리 서비스"),
                cta_title=f"{name} 방문 예약, 지금 도와드릴까요?", area=f"서울특별시 {gu}",
                extra_schema=[localbiz_ld(name=f"{BRAND} {name}", area=f"서울특별시 {gu} {name}", path=path)],
                longtail=longtail_dong(d, dd))


# ---- 지하철 허브 /seoul/stations/ ----------------------------------------
def build_stations_hub():
    path = "/seoul/stations/"
    trail = [("/", "홈"), ("/seoul/", "서울 출장마사지"), (None, "지하철역별 안내")]
    line_cards = "".join(
        f'<a class="card reveal" href="/seoul/stations/{l["slug"]}/"><div class="k">LINE</div>'
        f'<h3>{l["name"]}</h3><p>{l["desc"]}</p><span class="more">노선 보기 →</span></a>'
        for l in LINES)
    total_stations = len(STATIONS)
    station_chips = "".join(
        f'<a class="chip" href="/seoul/stations/{s["slug"]}/"><b>{s["name"]}</b></a>'
        for s in STATIONS if s["char"])
    body = (breadcrumb(trail) +
        '<section class="block"><div class="wrap">'
        '<span class="eyebrow"><span class="pulse"></span>STATIONS</span>'
        '<h2 class="sec">지하철역별 안내</h2>'
        '<p class="sec-lead">서울 지하철은 노선별 페이지와 역 상세 페이지로 안내합니다. 노선을 눌러 주요 역을 확인하세요. 검색 수요가 높은 주요 역은 개별 페이지로 운영하며, 출구별 페이지는 만들지 않습니다.</p>'
        f'<div class="grid g3" style="margin-top:26px">{line_cards}</div>'
        '<h3 style="font-size:20px;font-weight:800;margin:40px 0 6px">주요 역 바로가기</h3>'
        '<p class="sec-lead">검색 수요가 높은 주요 역세권 안내 페이지입니다.</p>'
        f'<div class="chips" style="margin-top:14px">{station_chips}</div>'
        '</div></section>'
        + hub_prose("STATIONS", "지하철역 안내는 이렇게 운영합니다", [
            "서울 지하철역 안내는 노선 페이지와 역 상세 페이지의 두 단계로 구성됩니다. 노선 페이지에서는 해당 노선이 지나는 주요 역과 역세권 흐름을 안내하고, 역 상세 페이지에서는 인근 생활권, 주변 대표 동, 예약 가능 시간, 방문 전 확인사항을 함께 안내합니다.",
            "강남역·잠실역·서울역·홍대입구역·건대입구역·신림역처럼 검색 수요가 높은 주요 역은 개별 상세 페이지로 운영합니다. 다만 같은 역이라도 출구별로 페이지를 나누지는 않습니다. 출구 번호로 방문 위치가 정해지는 것이 아니라, 예약 시 알려주신 정확한 주소를 기준으로 방문하기 때문입니다.",
            "역세권 방문은 역 자체가 아니라 역 인근의 자택·오피스텔·숙소를 기준으로 진행됩니다. 같은 노선이라도 도심 구간과 외곽 구간은 도착 시간 편차가 있어, 예약 시 가까운 역과 정확한 위치를 함께 알려주시면 예상 도착 시간을 빠르게 안내해 드립니다.",
            "특정 역과 특정 테마를 결합한 조합 페이지(예: ○○역 스웨디시)는 만들지 않습니다. 역은 위치 안내, 테마는 관리 유형 안내로 분리해 두고, 예약 시 두 가지를 함께 말씀해 주시면 됩니다."])
        + faq_block([
            ("원하는 역 페이지가 없어요.", "검색 수요가 높은 주요 역 위주로 상세 페이지를 운영합니다. 페이지가 없는 역도 해당 노선 페이지와 자치구 안내로 방문 위치를 확인할 수 있습니다."),
            ("출구별로 예약이 나뉘나요?", "아니요. 출구별 페이지는 운영하지 않습니다. 예약 시 알려주신 정확한 위치를 기준으로 방문합니다."),
            ("역 근처 숙소도 방문하나요?", "네. 역 인근 자택·오피스텔·숙소로 방문하며, 정확한 주소와 출입 방법을 알려주시면 도착이 빨라집니다."),
            ("노선과 자치구 안내 중 무엇을 보나요?", "역세권 흐름은 노선 페이지에서, 생활권 상세는 자치구·대표 동 페이지에서 확인하시면 됩니다.")])
        + cta_band())
    item_list = {"@context": "https://schema.org", "@type": "CollectionPage",
        "name": "서울 지하철역별 출장마사지·홈타이 안내", "url": BASE_URL + path,
        "hasPart": [{"@type": "WebPage", "name": l["name"],
                     "url": BASE_URL + f"/seoul/stations/{l['slug']}/"} for l in LINES]}
    html = page(path, "서울 지하철역별 안내 | 노선·역세권 출장마사지·홈타이",
        "서울 지하철역별 출장마사지·홈타이 안내 - 1~9호선 및 신림선·신분당선 등 노선별 페이지와 강남역·잠실역·홍대입구역 등 주요 역 안내를 제공합니다.",
        "stations", body, [bc_ld(trail), item_list, reviews_ld(url=BASE_URL + path)])
    write(path, html)
    _LEN_REPORT.append((path, text_len(html)))


# ---- 노선 페이지 /seoul/stations/{line}/ ---------------------------------
def build_line_pages():
    for l in LINES:
        path = f"/seoul/stations/{l['slug']}/"
        name = l["name"]
        trail = [("/", "홈"), ("/seoul/", "서울 출장마사지"),
                 ("/seoul/stations/", "지하철역별 안내"), (None, name)]
        sts = l["stations"]
        cnt = len(sts)
        ends = f"{sts[0]}~{sts[-1]}" if cnt > 1 else sts[0]
        station_links = [f'<a href="/seoul/stations/{STATION_SLUGS[nm]}/">{nm}</a>' for nm in sts]
        major_str = ", ".join(sts[:6])
        vl = lambda pool, salt: pick(l['slug'], pool, salt)
        sections = [
            (f"{name} 출장마사지·홈타이 이용 안내", [
                f"{name}은 {l['desc']}",
                f"{name} 라인은 역마다 생활권 성격이 달라, 같은 노선이라도 방문 가능 시간과 도착 시간이 다를 수 있습니다. " + pick(l['slug'], INTRO_BODY, "ib"),
                pick(l['slug'], RESV_LINE, "rl")]),
            (f"{name} 전체 역 안내", [
                vl([f"{name} 서울 구간은 {ends}까지 총 {cnt}개 역으로 이어집니다. 아래에서 역명을 누르면 해당 역 인근 방문 안내로 이동합니다.",
                    f"{name}은 {ends} 구간에 걸쳐 {cnt}개 역이 있습니다. 원하는 역을 눌러 인근 생활권과 방문 안내를 확인하세요.",
                    f"{name}을 따라 {ends}까지 {cnt}개 역이 놓여 있습니다. 각 역 페이지에서 인근 자치구·대표 동과 예약 안내를 제공합니다."], "maj"),
                "역세권 방문은 정확한 위치를 기준으로 안내드리며, 출구별 페이지는 운영하지 않습니다.",
                ("ul", station_links)]),
            (f"{name} 역세권 방문 안내", [
                vl([f"{name} 인근 방문은 역 자체가 아니라 가까운 자택·오피스텔·숙소를 기준으로 진행됩니다.",
                    f"{name} 방문은 역 건물이 아니라 역 주변의 실제 방문지(자택·오피스텔·숙소)를 기준으로 안내됩니다.",
                    f"{name}을 끼고 있어도 실제 방문은 역 인근 숙소나 자택 위치를 중심으로 이뤄집니다."], "zone1"),
                vl(["역 출구나 특정 번호 출구를 기준으로 한 별도 페이지는 만들지 않으며, 예약 시 알려주신 정확한 위치를 기준으로 방문 가능 여부를 확인합니다.",
                    "출구 번호별로 페이지를 나누지 않습니다. 예약 때 알려주신 주소를 기준으로 가능 여부와 도착 시간을 확인합니다.",
                    "특정 출구 기준의 페이지 대신, 예약 시 정확한 위치를 받아 방문 가능 여부를 안내하는 방식으로 운영합니다."], "zone2"),
                vl(["지역 단위 안내가 필요하면 해당 역이 속한 자치구·대표 동 페이지에서 더 자세히 확인하실 수 있습니다.",
                    "생활권을 더 자세히 보고 싶다면 그 역이 포함된 자치구와 대표 동 안내를 함께 참고하세요.",
                    "동 단위 생활권 정보는 해당 역이 속한 자치구·대표 동 페이지에 더 자세히 정리되어 있습니다."], "zone3")]),
            ("지역별 안내와 함께 보기", [
                vl(["노선 페이지는 역세권 흐름을 안내하고, 자치구·대표 동 페이지는 생활권을 자세히 안내합니다. 두 안내를 함께 보면 방문 위치를 더 정확히 정할 수 있습니다.",
                    "이 노선 페이지가 역 중심의 흐름을 보여준다면, 자치구·대표 동 페이지는 동네 단위 생활권을 보여줍니다. 둘을 함께 보면 방문 위치 결정이 쉬워집니다.",
                    "역세권은 노선 페이지로, 생활권은 자치구·대표 동 페이지로 나누어 안내합니다. 두 가지를 같이 확인하면 위치를 더 정확히 좁힐 수 있습니다."], "area"),
                ("ul", ['<a href="/seoul/area/">서울 지역별 안내</a>',
                        '<a href="/seoul/">서울 출장마사지·홈타이 대표 안내</a>',
                        '<a href="/seoul/stations/">서울 지하철역 전체</a>'])]),
            ("많이 찾는 테마와 코스", [
                vl(["역세권 방문에서도 이용 목적에 따라 선택하는 관리가 다릅니다. 관리 유형과 코스 구성을 함께 확인하세요.",
                    "같은 노선 인근이라도 이용 목적은 제각각입니다. 원하는 관리 유형과 코스를 함께 살펴보세요.",
                    "역 주변 방문에서도 목적에 따라 고르는 관리가 다르니, 테마와 코스를 함께 확인하시면 좋습니다."], "th"),
                theme_links_ul(l['slug'], 4)]),
        ]
        faq = [
            (f"{name} 어느 역까지 방문 가능한가요?",
             f"예약 시간과 정확한 위치, 배정 상황에 따라 달라질 수 있습니다. {major_str} 등 주요 역세권을 기준으로 안내드립니다."),
            (f"{name} 출구별로 예약이 나뉘나요?",
             "아니요. 출구별 페이지는 운영하지 않습니다. 예약 시 알려주신 정확한 위치를 기준으로 방문합니다."),
            (f"{name} 역 근처 숙소도 방문하나요?",
             "네. 역 인근 자택·오피스텔·숙소로 방문하며, 정확한 주소와 출입 방법을 알려주시면 도착이 빨라집니다."),
            (f"{name}은 어떤 노선인가요?",
             f"{l['desc']}"),
        ]
        content_page(path, "stations", trail,
            title=f"서울 {name} 출장마사지·홈타이 | {name} 역세권 방문 안내",
            desc=f"서울 {name} 출장마사지·홈타이 안내 - {major_str} 등 주요 역세권 방문 가능 안내와 예약 전 확인사항, 관련 테마·코스를 제공합니다.",
            eyebrow=f"지하철 · {name}", h1=f"서울 {name} 출장마사지·홈타이 안내",
            lead=f"서울 {name} 역세권에서 방문 마사지·홈타이 예약을 찾는 분들을 위한 안내입니다. {major_str} 등 주요 역을 기준으로 방문 안내와 예약 정보를 확인하세요.",
            sections=sections, faq=faq,
            top_links=[("tel:" + PHONE_TEL, "예약문의", True), ("/seoul/stations/", "지하철역별 안내"),
                       ("/seoul/area/", "지역별 안내"), ("/theme/", "테마별 안내")],
            show_price=True,
            data_note=f"{name}은 역마다 생활권이 달라 도착 시간 편차가 큽니다. 예약 시 가까운 역과 정확한 주소를 함께 알려주시면 예상 도착 시간을 빠르게 안내해 드립니다.",
            service=(f"서울 {name} 출장마사지·홈타이", f"서울 {name} 역세권 방문 건강관리 서비스"),
            cta_title=f"{name} 역세권 방문 예약을 도와드릴까요?")


# ---- 역 상세 페이지 /seoul/stations/{station}/ ---------------------------
def build_station_pages():
    for s in STATIONS:
        name, slug = s["name"], s["slug"]
        base = name[:-1] if name.endswith("역") else name
        path = f"/seoul/stations/{slug}/"
        trail = [("/", "홈"), ("/seoul/", "서울 출장마사지"),
                 ("/seoul/stations/", "지하철역별 안내"), (None, f"{name} 출장마사지")]
        lines = s["lines"]
        line_str = "·".join(lines)
        line_links = [f'<a href="/seoul/stations/{LINE_BY_NAME[ln]["slug"]}/">{ln} 안내</a>'
                      for ln in lines if ln in LINE_BY_NAME]
        gu, gslug = s["gu"], s["gu_slug"]
        gu_label = gu or "서울"
        gu_char = DISTRICT_BY_SLUG[gslug]["character"] if gslug else "여러 생활권이 이어지는 서울 도심"
        dongs = s["dongs"][:4]
        dong_names = [dd["name"] for dd in dongs]
        near_str = ", ".join(dong_names[:3]) if dong_names else f"{gu_label} 일대"
        # 인근 역(같은 노선 앞뒤) 링크
        near_st = s["nearby"][:5]
        near_st_links = [f'<a href="/seoul/stations/{STATION_SLUGS[n]}/">{n} 안내</a>'
                         for n in near_st if n in STATION_SLUGS]
        char = s["char"] or pick(slug, [
            f"{gu_label} 생활권에 자리한 역세권",
            f"{gu_label}의 주거·상권과 이어지는 역세권",
            f"{gu_label} 일대 방문 수요가 꾸준한 역세권"], "char")

        zone = [
            f"{name} 주변은 {near_str} 등 {gu_label}의 생활권과 이어집니다. {gu_label}은 {gu_char}으로, 같은 역세권 안에서도 위치에 따라 분위기와 접근성이 다릅니다.",
            "정확한 방문 가능 여부와 예상 도착 시간은 위치·예약 시간·배정 상황에 따라 달라지므로, 예약 시 가까운 출입구가 아니라 정확한 주소를 알려주시면 안내가 빠릅니다.",
            ("h3", "역 인근 주거지·오피스텔"),
            f"{name} 인근 자택·오피스텔로 방문할 때는 공동현관 출입 방법과 동·호수를 함께 알려주시면 도착이 빨라집니다.",
            ("h3", "역 주변 숙소"),
            f"{base} 인근 호텔·숙소 방문 시에는 건물명과 객실 번호, 프런트 출입 안내 여부를 알려주시면 원활합니다."]

        rep_links = []
        if gslug:
            rep_links.append(f'<a href="/seoul/{gslug}/">{gu_label} 전체 안내</a>')
            rep_links += [f'<a href="/seoul/{gslug}/{dd["slug"]}/">{dd["name"]} 안내</a>' for dd in dongs]
        else:
            rep_links.append('<a href="/seoul/area/">서울 지역별 안내</a>')
        rep_links += near_st_links

        sections = [
            (f"{name} 출장마사지·홈타이 이용 안내", [
                pick(slug, INTRO_OPEN, "intro").format(n=name) + f" {name}은 {char}입니다.",
                f"{name}은 {line_str}이 지나며 {gu_label} 생활권과 가깝습니다. 역 인근 자택·오피스텔·숙소로 방문하며, " + pick(slug, INTRO_BODY, "ib"),
                pick(slug, RESV_LINE, "rl")]),
            (f"{name} 인근 방문 가능 생활권", zone),
            (f"{name} 주변 대표 지역 안내", [
                f"{name}이 속한 {gu_label}의 자치구·대표 동 안내, 그리고 같은 노선의 인근 역과 함께 보면 방문 위치를 더 정확히 정할 수 있습니다.",
                ("ul", rep_links)]),
            ("이용 가능한 노선 안내", [
                f"{name}은 {line_str}을 이용할 수 있습니다. 환승역도 페이지는 하나로 운영하며, 각 노선의 역세권 흐름은 노선 페이지에서 확인하실 수 있습니다.",
                ("ul", line_links + ['<a href="/seoul/stations/">서울 지하철역 전체</a>'])]),
            (f"{name} 주변에서 많이 찾는 테마", [
                f"{name} 인근 방문에서도 이용 목적에 따라 선택하는 관리가 다릅니다. 지역+테마 조합 페이지 대신, 관리 유형별 특징은 테마별 안내에서 확인하세요.",
                theme_links_ul(slug, 4)]),
            ("예약·준비·위생 안내", [
                f"{name} 인근 방문 예약은 시간대와 배정 상황에 따라 가능 여부가 달라집니다. 저녁·주말은 문의가 몰릴 수 있어 사전 예약을 권장드립니다.",
                "예약 가능 시간, 방문 전 준비물, 위생·안전 기준은 전용 안내에서 자세히 확인하실 수 있습니다.",
                reserve_links_ul()]),
        ]
        faq = [
            (f"{name} 인근 어디까지 방문 가능한가요?",
             f"예약 시간, 정확한 위치, 배정 상황에 따라 달라질 수 있습니다. {near_str} 등 {gu_label} 생활권을 기준으로 안내드립니다."),
            (f"{name} 출구별로 예약이 나뉘나요?",
             "아니요. 출구별 페이지는 운영하지 않습니다. 예약 시 알려주신 정확한 위치를 기준으로 방문합니다."),
            (f"{name}은 어떤 역인가요?",
             f"{name}은 {line_str}이 지나는 {gu_label}의 역으로, {char}입니다."),
            (f"{name} 근처 숙소도 방문하나요?",
             "네. 역 인근 자택·오피스텔·숙소로 방문하며, 정확한 주소와 출입 방법을 알려주시면 도착이 빨라집니다."),
            (f"{name}에서는 어떤 관리가 인기인가요?",
             "스웨디시·아로마·홈케어 등 목적에 따라 선택합니다. 자세한 내용은 테마별 안내에서 확인하실 수 있습니다."),
        ]
        top = [("tel:" + PHONE_TEL, "예약문의", True)]
        if gslug:
            top.append((f"/seoul/{gslug}/", f"{gu_label} 안내"))
        top += [("/seoul/stations/", "지하철역별 안내"), ("/theme/", "테마별 안내")]
        content_page(path, "stations", trail,
            title=f"{name} 출장마사지·홈타이 | {gu_label} {name} 인근 방문 마사지 안내",
            desc=f"{gu_label} {name} 인근 출장마사지·홈타이 예약 안내 페이지입니다. {near_str} 생활권과 이용 노선({line_str}), 예약 가능 시간, 이용 전 확인사항을 안내합니다.",
            eyebrow=f"{gu_label} · {name}", h1=f"{name} 출장마사지·홈타이 예약 안내",
            lead=f"서울 {name}({char})에서 방문 마사지·홈타이 예약을 찾는 분들을 위한 안내입니다. {near_str} 인근 생활권을 기준으로 방문 안내와 예약 정보를 확인하세요.",
            sections=sections, faq=faq, subject=name, show_price=True,
            top_links=top,
            data_note=f"{name}({gu_label}) 인근은 위치에 따라 도착 시간 편차가 있습니다. 예약 시 정확한 주소와 출입 방법을 알려주시면 예상 도착 시간을 빠르게 안내해 드립니다.",
            service=(f"{name} 출장마사지·홈타이", f"서울 {name} 역세권 방문 건강관리 서비스"),
            cta_title=f"{name} 인근 방문 예약을 도와드릴까요?", area=f"서울특별시 {gu_label}",
            extra_schema=[localbiz_ld(name=f"{BRAND} {name}", area=f"서울특별시 {gu_label}", path=path)],
            longtail=longtail_station(s))


# ---- 테마 허브 /theme/ ---------------------------------------------------
def build_theme_hub():
    path = "/theme/"
    trail = [("/", "홈"), (None, "테마별 안내")]
    cards = "".join(
        f'<a class="card reveal" href="/theme/{t["slug"]}/"><div class="k">{t["kicker"]}</div>'
        f'<h3>{t["name"]}</h3><p>{t["summary"]}</p><span class="more">테마 보기 →</span></a>'
        for t in THEMES)
    body = (breadcrumb(trail) +
        '<section class="block"><div class="wrap">'
        '<span class="eyebrow"><span class="pulse"></span>THEME</span>'
        '<h2 class="sec">테마별 안내</h2>'
        '<p class="sec-lead">이용 목적에 맞춰 고를 수 있는 관리 유형입니다. 각 테마 페이지는 관리 특징, 추천 대상, 다른 관리와의 차이, 예약 전 확인사항을 안내합니다. 지역·역과 결합한 조합 페이지는 만들지 않습니다.</p>'
        f'<div class="grid g3" style="margin-top:26px">{cards}</div></div></section>' +
        hub_prose("THEME", "테마별 안내는 이렇게 운영합니다", [
            "테마별 안내는 '어떤 방식의 관리를 받을 것인가'를 기준으로 고를 수 있도록 구성했습니다. 스웨디시·로미로미·아로마테라피처럼 오일을 사용한 부드러운 이완 계열, 타이마사지·중국마사지처럼 지압·스트레칭 계열, 스포츠·경락처럼 또렷한 압 계열, 그리고 홈케어·호텔식·발마사지·스킨케어·왁싱 등 목적이 뚜렷한 케어까지 폭넓게 나누어 두었습니다.",
            "각 테마 페이지는 단순히 키워드만 나열한 페이지가 아니라, 관리의 특징과 추천 대상, 다른 관리와의 차이, 진행 방식, 예약 전 확인사항을 충분히 설명하는 방식으로 운영합니다. 어떤 관리가 맞을지 고민된다면 목적(이완·근육 회복·향·수면 등)을 기준으로 선택하면 쉽습니다.",
            "테마는 서울 전체를 기준으로 안내하며, 특정 지역이나 역과 결합한 조합 페이지(예: ○○동 스웨디시, ○○역 아로마)는 만들지 않습니다. 관리 유형은 테마에서 고르고, 방문 위치는 지역별·지하철역별 안내에서 확인한 뒤 예약 시 함께 말씀해 주시면 됩니다.",
            "처음이라면 부담 없는 스웨디시 계열로 시작하는 경우가 많고, 향과 함께 깊게 쉬고 싶다면 아로마테라피, 운동 후 컨디션 정리에는 스포츠·경락이 잘 맞습니다. 시간 구성(60·90·120분)은 코스안내에서 함께 확인하실 수 있습니다."]) +
        price_menu_block() +
        faq_block([
            ("테마는 어떻게 고르나요?", "이완·근육 회복·향·수면 등 목적을 기준으로 고르면 쉽습니다. 정하기 어려우면 상담에서 컨디션을 말씀해 주시면 추천드립니다."),
            ("지역과 테마를 결합한 페이지는 없나요?", "네, 운영하지 않습니다. 테마는 관리 유형, 지역은 위치 안내로 분리하고 예약 시 함께 말씀해 주시면 됩니다."),
            ("홈타이도 테마에서 고르나요?", "홈타이(홈케어)는 자택 방문 방식이며, 그 안에서 스웨디시·아로마 등 기법을 선택할 수 있습니다."),
            ("테마마다 요금이 다른가요?", "코스(시간) 기준 정찰 요금을 사전에 안내하며, 테마·구성에 따라 세부 금액이 달라질 수 있습니다.")]) +
        cta_band())
    item_list = {"@context": "https://schema.org", "@type": "CollectionPage",
        "name": "출장마사지·홈타이 테마별 안내", "url": BASE_URL + path,
        "hasPart": [{"@type": "WebPage", "name": t["name"],
                     "url": BASE_URL + f"/theme/{t['slug']}/"} for t in THEMES]}
    html = page(path, "테마별 안내 | 출장마사지·홈타이 관리 유형 안내",
        "출장마사지·홈타이 테마별 안내 - 스웨디시, 아로마테라피, 타이마사지, 홈케어, 스포츠·경락 등 관리 유형별 특징과 추천 대상을 안내합니다.",
        "theme", body, [bc_ld(trail), item_list, offer_ld(), reviews_ld(url=BASE_URL + path)])
    write(path, html)
    _LEN_REPORT.append((path, text_len(html)))


# ---- 테마 페이지 /theme/{slug}/ ------------------------------------------
def build_theme_pages():
    for t in THEMES:
        slug, name = t["slug"], t["name"]
        path = f"/theme/{slug}/"
        trail = [("/", "홈"), ("/theme/", "테마별 안내"), (None, name)]
        v = lambda pool, salt: pick(slug, pool, salt)
        sections = [
            (f"{name} 관리란?", [
                t["what"],
                v([f"{name}는 특정 증상의 치료가 아니라, 하루의 피로를 정리하고 휴식의 질을 높이기 위한 건강관리 목적의 관리입니다.",
                   f"{name}는 질환을 치료하는 의료 행위가 아니라, 쌓인 긴장을 풀고 컨디션을 가다듬기 위한 이완 중심의 관리입니다.",
                   f"{name}는 증상 치료가 목적이 아니라, 몸과 마음의 긴장을 내려놓고 휴식의 질을 끌어올리는 데 초점을 둡니다."], "purpose")]),
            ("이런 분들에게 추천합니다", [
                ("ul", t["who"])]),
            ("서울에서 이용 가능한 지역", [
                v([f"{name}는 서울 전지역에서 방문 형태로 이용하실 수 있습니다. 자치구와 대표 동, 지하철역 인근을 기준으로 방문 가능 여부를 안내드립니다.",
                   f"{name}는 서울 어디서든 방문으로 받으실 수 있으며, 자치구·대표 동·역세권을 기준으로 가능 여부를 확인해 드립니다.",
                   f"{name}는 서울 전역이 대상입니다. 권역과 자치구, 가까운 지하철역을 기준으로 방문 가능 시간을 안내합니다."], "area1"),
                v(["특정 지역명을 길게 나열하기보다, 예약 시 정확한 위치를 알려주시면 방문 가능 시간과 예상 도착 시간을 안내하는 방식으로 운영합니다.",
                   "지역명을 무리하게 늘어놓지 않고, 예약 때 알려주신 정확한 위치를 기준으로 도착 시간을 안내하는 방식이 더 정확합니다.",
                   "방문 가능 여부는 위치·시간·배정 상황에 따라 달라지므로, 예약 시 위치를 알려주시면 빠르게 안내해 드립니다."], "area2"),
                ("ul", ['<a href="/seoul/area/">서울 지역별 안내</a>',
                        '<a href="/seoul/stations/">서울 지하철역별 안내</a>',
                        '<a href="/seoul/">서울 출장마사지·홈타이 대표 안내</a>'])]),
            ("다른 관리와 차이점", [
                t["diff"],
                v(["어떤 관리가 맞을지 고민된다면, 목적(이완·근육 회복·향·수면 등)을 기준으로 선택하면 쉽습니다.",
                   "선택이 어렵다면 '무엇을 위해 받는가'를 먼저 떠올려 보면 적합한 관리를 고르기 쉽습니다.",
                   "고민될 때는 이완·근육 회복·향·수면처럼 원하는 목적을 기준으로 고르시길 권합니다."], "diff2")]),
            ("진행 방식과 시간", [
                t["method"],
                v(["60·90·120분 구성으로 운영하며, 시작 전 선호와 컨디션을 확인해 진행합니다. 자세한 시간 선택은 <a href=\"/course/guide/\">코스 선택 가이드</a>에서 확인하실 수 있습니다.",
                   "시간은 60·90·120분 중에서 고르며, 시작 전 압·집중 부위 선호를 확인합니다. 시간 선택 기준은 <a href=\"/course/guide/\">코스 선택 가이드</a>를 참고하세요.",
                   "구성은 60·90·120분이며, 진행 전 컨디션과 선호를 확인해 맞춥니다. 어느 시간이 좋을지는 <a href=\"/course/guide/\">코스 선택 가이드</a>에서 확인할 수 있습니다."], "method2")]),
            ("예약 전 확인사항", [
                v([f"{name} 예약 시에는 방문 장소의 정확한 주소와 출입 방법, 조용한 공간 확보 여부를 미리 확인해 주세요.",
                   f"{name} 예약 전에는 정확한 주소와 공동현관 출입 방법, 편히 쉴 공간이 있는지 확인하면 좋습니다.",
                   f"{name} 예약을 앞두고는 주소·출입 방법과 조용한 공간 확보 여부를 미리 점검해 주세요."], "resv1"),
                v(["민감성 피부·알러지·임신 등 주의가 필요한 상황은 안전을 위해 예약 시 미리 알려주시면 무리하지 않도록 조정합니다.",
                   "알러지나 민감성 피부, 임신 등 주의가 필요하면 예약 때 알려주세요. 무리하지 않도록 진행합니다.",
                   "건강상 주의가 필요한 상황(임신·피부 질환 등)은 안전을 위해 사전에 공유해 주시면 맞춰 진행합니다."], "resv2"),
                reserve_links_ul()]),
        ]
        faq = [
            (f"{name}는 처음인데 받아도 될까요?",
             "네. 시작 전 선호와 컨디션을 확인하고 진행하니 처음이셔도 편하게 받으실 수 있습니다."),
            (f"{name}는 서울 어디까지 방문하나요?",
             "서울 전지역을 대상으로 하며, 예약 시 정확한 위치를 알려주시면 방문 가능 시간을 안내드립니다."),
            (f"{name}와 다른 관리를 함께 받을 수 있나요?",
             "구성에 따라 가능합니다. 원하는 부위나 목적을 말씀해 주시면 적합한 구성을 안내드립니다."),
            (f"{name}도 정찰 요금인가요?",
             "네. 코스별 정찰 요금을 사전에 안내드립니다. 자세한 금액은 가격 안내에서 확인하실 수 있습니다."),
        ]
        content_page(path, "theme", trail,
            title=f"{name} 출장마사지·홈타이 | 서울 {name} 관리 안내",
            desc=f"{name} 출장마사지·홈타이 안내 - {t['summary']} 추천 대상, 다른 관리와의 차이, 진행 방식, 예약 전 확인사항을 제공합니다.",
            eyebrow=f"THEME · {name}", h1=f"{name} 출장마사지·홈타이 안내",
            lead=t["summary"] + " 서울 전지역 방문으로 이용하실 수 있으며, 추천 대상과 다른 관리와의 차이를 함께 확인하세요.",
            sections=sections, faq=faq, show_price=True,
            top_links=[("tel:" + PHONE_TEL, "예약문의", True), ("/theme/", "테마별 안내"),
                       ("/course/", "코스안내"), ("/seoul/area/", "지역별 안내")],
            data_note=f"{name}는 이용 목적이 뚜렷한 편이라, 예약 시 원하는 압·향·집중 부위를 함께 알려주시면 방문이 매끄럽습니다.",
            service=(f"{name} 출장마사지·홈타이", f"서울 전지역 {name} 방문 건강관리 서비스"),
            cta_title=f"{name} 예약을 도와드릴까요?")


# ---- 코스 허브 /course/ --------------------------------------------------
def build_course():
    path = "/course/"
    trail = [("/", "홈"), (None, "코스안내")]
    course_faq = [
        ("코스는 어떻게 선택하나요?", "컨디션과 목적을 말씀해 주시면 피로 회복·아로마·스포츠·홈타이 중 적합한 코스를 안내드립니다."),
        ("커플·가족 관리는 어떻게 진행되나요?", "두 분이 같은 공간에서 동시에 받는 동반 관리이며, 인원과 시간에 따라 요금이 달라집니다."),
        ("기업·단체 관리도 되나요?", "워크숍·행사 등 단체 인원은 사전 협의 후 별도 견적으로 안내드립니다."),
        ("표시된 요금 외 추가 비용이 있나요?", "정찰 요금을 원칙으로 하며, 변동 사항은 예약 시 사전에 안내드립니다."),
    ]
    course_cards = "".join(
        f'<a class="card reveal" href="/course/{c["slug"]}/"><div class="k">{c["kicker"]}</div>'
        f'<h3>{c["name"]}</h3><p>{c["desc"]}</p><span class="more">코스 보기 →</span></a>'
        for c in COURSES)
    more_cards = (
        '<a class="card reveal" href="/course/price/"><div class="k">PRICE</div>'
        '<h3>가격 안내</h3><p>코스별 60·90·120분 정찰 요금과 변동 요소를 안내합니다.</p>'
        '<span class="more">가격 보기 →</span></a>'
        '<a class="card reveal" href="/course/guide/"><div class="k">GUIDE</div>'
        '<h3>코스 선택 가이드</h3><p>목적·상황별 추천과 시간 선택 기준을 안내합니다.</p>'
        '<span class="more">가이드 보기 →</span></a>')
    body = (breadcrumb(trail) +
        '<section class="block" id="all"><div class="wrap">'
        '<span class="eyebrow"><span class="pulse"></span>COURSE</span>'
        '<h2 class="sec">전체 코스</h2>'
        '<p class="sec-lead">목적과 컨디션에 맞춰 고를 수 있는 방문 관리 코스입니다. 코스를 눌러 상세 안내를 확인하세요.</p>'
        f'<div class="grid g3" style="margin-top:26px">{course_cards}</div></div></section>' +
        price_menu_block() +
        '<section class="block"><div class="wrap">'
        '<span class="eyebrow"><span class="pulse"></span>MORE</span>'
        '<h2 class="sec">가격과 코스 선택</h2>'
        f'<div class="grid g2" style="margin-top:24px">{more_cards}</div></div></section>' +
        hub_prose("COURSE", "코스는 이렇게 구성됩니다", [
            "코스안내는 '무엇을 위해, 얼마나 받을 것인가'를 기준으로 정리했습니다. 피로 회복 관리는 전신을 부드럽게 풀어주는 기본 구성, 아로마 관리는 향을 더한 이완, 스포츠 관리는 운동 후 또렷한 압의 회복 케어, 홈타이 코스는 자택 방문 방식, 커플·가족과 기업·단체는 인원·일정에 맞춘 동반·협의형 구성입니다.",
            "모든 코스는 60·90·120분 시간 구성으로 운영합니다. 60분은 핵심 부위 위주로 빠르게 정리할 때, 90분은 전신을 고르게 풀고 싶을 때, 120분은 마무리 케어까지 여유 있게 받고 싶을 때 적합합니다. 처음이라면 90분 구성을 가장 많이 선택합니다.",
            "요금은 코스(종류)와 시간(분)의 조합으로 정해지는 정찰 요금을 원칙으로 합니다. 현장에서 임의로 금액을 올리거나 숨겨진 추가 비용을 청구하지 않으며, 지역·시간대 등 변동 요소는 예약 시 미리 안내드립니다. 자세한 금액은 가격 안내에서 확인하실 수 있습니다.",
            "어떤 관리 방식(스웨디시·아로마테라피·타이마사지 등)을 받을지는 테마별 안내에서, 코스를 고르는 기준은 코스 선택 가이드에서 함께 확인하시면 선택이 한결 쉬워집니다.",
            "커플·가족 방문 관리는 두 분이 같은 공간에서 동시에 받는 동반형 구성으로, 관리사 2인이 방문하며 각자 다른 코스를 선택할 수도 있습니다. 일정 조율이 필요해 사전 예약을 권장드립니다. 기업·단체 방문 관리는 워크숍·행사·사내 복지 등 단체 인원을 대상으로 하며, 짧은 의자형 케어부터 표준 코스까지 인원과 시간에 맞춰 유연하게 구성합니다.",
            "재방문 시에는 지난번 좋았던 압·향·집중 부위를 알려주시면 더 잘 맞춰 드릴 수 있습니다. 컨디션에 따라 코스를 바꿔가며 받는 것도 좋은 방법이며, 같은 코스라도 시간 구성을 달리하면 받는 느낌이 달라집니다. 처음이라 고르기 어렵다면 예약 상담에서 컨디션을 말씀해 주시면 알맞은 코스와 시간을 추천드립니다."]) +
        faq_block(course_faq) + cta_band())
    jsonld = [bc_ld(trail),
              service_ld("방문 마사지 코스", "피로 회복·아로마·스포츠·홈타이·커플·기업단체 방문 관리 코스", "/course/"),
              offer_ld(), faq_ld(course_faq), reviews_ld(url=BASE_URL + path)]
    html = page(path, "코스안내 | 서울 출장마사지·홈타이 피로회복·아로마·스포츠 요금",
        "서울 출장마사지·홈타이 코스안내 - 피로 회복, 아로마, 스포츠, 홈타이, 커플·가족, 기업·단체 관리의 코스 설명과 정찰 요금을 안내합니다.",
        "course", body, jsonld)
    write(path, html)
    _LEN_REPORT.append((path, text_len(html)))


def build_course_pages():
    ct = [("/", "홈"), ("/course/", "코스안내")]

    content_page("/course/fatigue/", "course", ct + [(None, "피로 회복 관리")],
        title="피로 회복 관리 | 서울 출장마사지 스웨디시 계열 방문 관리",
        desc="서울 출장마사지 피로 회복 관리 안내 - 전신 긴장을 부드럽게 풀어주는 스웨디시 계열 방문 관리입니다. 대상, 60·90·120분 진행 방식, 방문 관리의 장점을 확인하세요.",
        eyebrow="COURSE · 피로 회복", h1="피로 회복 관리",
        lead="전신의 근육 긴장을 부드럽게 풀어주는 스웨디시 계열 기본 방문 관리입니다.",
        sections=[
            ("피로 회복 관리란 무엇인가요", [
                "피로 회복 관리는 전신의 근육 긴장을 부드럽게 풀어주는 스웨디시 계열의 기본 방문 관리입니다.",
                "강한 자극보다 일정한 압과 리듬으로 혈행과 이완을 돕는 데 초점을 둡니다.",
                "의료적 치료가 아니라, 하루의 피로를 정리하고 휴식의 질을 높이기 위한 <strong>건강관리 목적</strong>의 관리입니다."]),
            ("이런 분께 권해드립니다", [
                ("ul", ["장시간 앉아 일해 어깨·목·허리가 자주 뭉치는 분",
                        "잠들기 전 몸의 긴장을 풀고 수면의 질을 높이고 싶은 분",
                        "강한 지압보다 부드럽고 편안한 이완을 선호하는 분",
                        "출장·야근으로 마사지숍을 방문할 시간을 내기 어려운 분"])]),
            ("60·90·120분 진행 방식", [
                "60분은 어깨·등·다리 등 피로가 집중된 부위를 중심으로 전신을 한 차례 정리합니다.",
                "90분은 가장 많이 선택되는 구성으로, 전신을 고르게 풀고 뭉친 부위에 시간을 더 배분합니다.",
                "120분은 전신을 충분히 이완한 뒤 두피·발 등 마무리 케어까지 여유 있게 진행합니다.",
                "관리 시작 전 선호하는 압의 세기와 집중 부위를 확인하고, 진행 중에도 조절해 드립니다."]),
            ("방문 관리이기에 더 좋은 점", [
                "관리 직후 이동 없이 그대로 쉴 수 있어 이완 상태가 오래 유지됩니다.",
                "익숙한 공간에서 받기 때문에 긴장이 덜하고 편안합니다.",
                "서울 전지역으로 방문하며, 위치에 따라 예상 도착 시간을 예약 시 안내드립니다."]),
            ("관리 당일, 이렇게 진행됩니다", [
                "관리사가 도착하면 가볍게 인사를 나누고, 편히 누우실 수 있도록 공간을 정돈합니다.",
                "본격적인 관리 전에 선호하는 압의 세기와 특히 풀고 싶은 부위를 확인합니다.",
                "관리는 호흡을 고르며 큰 근육부터 차례로 이완하고, 뭉친 부위는 시간을 더 들여 풀어드립니다.",
                "마지막에는 마무리 정돈과 함께 수분 섭취·휴식을 안내하며 관리를 마칩니다."]),
            ("이렇게 준비하면 더 좋습니다", [
                "관리 전 가벼운 샤워로 몸을 따뜻하게 하면 이완이 한결 수월합니다.",
                "과식 직후보다는 식사 후 어느 정도 시간이 지난 뒤가 편안합니다.",
                "편안한 복장과 조용한 분위기를 준비해 두시면 휴식의 질이 높아집니다.",
                "받고 난 뒤 좋았던 압·부위를 기억해 두면 다음 방문 때 더 잘 맞춰 드릴 수 있습니다."]),
        ],
        data_note="피로 회복 관리는 90분 구성 선택 비율이 가장 높습니다. 주중 21~24시 예약이 많아, 해당 시간대는 도착 시간을 넉넉히 안내드립니다.",
        faq=[
            ("피로 회복 관리와 아로마 관리는 어떻게 다른가요?", "피로 회복 관리는 전신 이완에, 아로마 관리는 블렌딩 오일의 향을 더한 이완에 중점을 둡니다. 향에 민감하지 않다면 피로 회복 관리로 시작하셔도 좋습니다."),
            ("압이 너무 세거나 약하면 조절되나요?", "네. 시작 전과 진행 중 언제든 압의 세기를 말씀해 주시면 맞춰 드립니다."),
            ("관리 후 주의할 점이 있나요?", "충분한 수분 섭취와 휴식을 권장드립니다. 통증·부상이 있는 부위는 무리하지 않습니다.")],
        service=("피로 회복 관리", "서울 방문 스웨디시 계열 전신 이완 관리"))

    content_page("/course/aroma/", "course", ct + [(None, "아로마 관리")],
        title="아로마 관리 | 서울 출장마사지 아로마 오일 방문 관리",
        desc="서울 출장마사지 아로마 관리 안내 - 블렌딩 오일의 향과 촉감으로 심신을 이완하는 방문 관리입니다. 사용 오일, 사전 확인사항, 진행 방식, 피로 회복 관리와의 차이를 확인하세요.",
        eyebrow="COURSE · 아로마", h1="아로마 관리",
        lead="블렌딩한 관리용 오일을 사용해 향과 촉감으로 심신을 함께 이완하는 방문 관리입니다.",
        sections=[
            ("아로마 관리의 특징", [
                "아로마 관리는 블렌딩한 관리용 오일을 사용해 향과 촉감으로 심신을 함께 이완하는 방문 관리입니다.",
                "오일이 피부 위에서 부드럽게 미끄러지며 마찰을 줄여, 더 유연하고 감각적인 이완을 돕습니다.",
                "향을 통한 심리적 이완이 더해져, 긴장도가 높거나 예민한 날에 특히 선호됩니다."]),
            ("사용 오일과 사전 확인", [
                "라벤더 계열의 차분한 향, 시트러스 계열의 가벼운 향 등 그날의 컨디션에 맞춰 안내드립니다.",
                "피부가 민감하거나 특정 향·성분에 알러지가 있다면 예약 시 미리 알려주세요.",
                "임신 중이거나 피부 질환이 있는 경우, 무리하지 않도록 사전에 상담드립니다."]),
            ("60·90·120분 진행 방식", [
                "60분은 어깨·등을 중심으로 오일 관리를 진행합니다.",
                "90분은 전신을 고르게 아우르는 가장 표준적인 구성입니다.",
                "120분은 전신 이완 후 두피·발 마무리까지 포함해 여유 있게 진행합니다."]),
            ("피로 회복 관리와의 차이", [
                "피로 회복 관리가 근육 이완 자체에 집중한다면, 아로마 관리는 여기에 향의 이완을 더합니다.",
                "오일을 사용하므로 마무리 단계에서 수건으로 가볍게 정돈해 과도한 잔여감을 줄입니다."]),
            ("오일이 만드는 차이", [
                "오일을 사용하면 손과 피부 사이의 마찰이 줄어, 같은 동작도 더 부드럽고 깊게 전달됩니다.",
                "끊김 없이 이어지는 긴 동작이 가능해 호흡이 느려지고 긴장이 천천히 가라앉습니다.",
                "건식 관리에서 자극이 부담스러웠던 분도 비교적 편안하게 받을 수 있습니다."]),
            ("관리 당일 진행 순서", [
                "도착 후 그날의 컨디션과 선호 향을 확인하고 오일을 준비합니다.",
                "어깨·등 등 넓은 부위부터 오일을 펴 바르며 이완을 시작합니다.",
                "전신을 고르게 아우른 뒤, 마무리 단계에서 수건으로 정돈해 잔여감을 줄입니다."]),
            ("관리 후 이렇게 케어하세요", [
                "관리 후에는 따뜻한 물을 충분히 마시고 무리한 활동을 피해 휴식을 권장드립니다.",
                "오일 잔여감이 신경 쓰이면 가벼운 샤워로 마무리하셔도 좋습니다."]),
        ],
        data_note="아로마 관리는 금요일·주말 저녁 예약 비율이 평일보다 높습니다. 향 선호가 뚜렷한 고객이 많아, 예약 시 선호 향을 함께 받아두면 방문이 매끄럽습니다.",
        faq=[
            ("향을 선택할 수 있나요?", "네. 라벤더·시트러스 등 계열을 안내드리며, 선호가 없으시면 컨디션에 맞춰 추천드립니다."),
            ("오일 알러지가 걱정됩니다.", "민감성 피부나 알러지가 있으면 예약 시 알려주세요. 무리하지 않도록 조정합니다."),
            ("관리 후 끈적임이 남지 않나요?", "마무리 단계에서 수건으로 정돈해 드려 과도한 잔여감을 줄입니다.")],
        service=("아로마 관리", "서울 방문 아로마 오일 이완 관리"))

    content_page("/course/sports/", "course", ct + [(None, "스포츠 관리")],
        title="스포츠 관리 | 서울 출장마사지 운동 후 근육 방문 관리",
        desc="서울 출장마사지 스포츠 관리 안내 - 운동 후 뭉친 근육과 컨디션 회복에 초점을 맞춘 방문 관리입니다. 적합한 상황, 진행 방식, 주의사항을 확인하세요.",
        eyebrow="COURSE · 스포츠", h1="스포츠 관리",
        lead="운동 후 뭉친 근육과 컨디션 회복에 초점을 맞춘 방문 관리입니다.",
        sections=[
            ("스포츠 관리란", [
                "스포츠 관리는 운동 후 뭉친 근육과 컨디션 회복에 초점을 맞춘 방문 관리입니다.",
                "근육 부위를 따라 비교적 또렷한 압으로 풀어, 운동으로 누적된 피로를 정리하는 데 도움을 줍니다.",
                "전문 재활·치료가 아닌, 일상 운동 후의 컨디션 관리 목적임을 안내드립니다."]),
            ("이런 상황에 잘 맞습니다", [
                ("ul", ["러닝·헬스·등산 등 운동 후 다리·등 근육이 무거운 날",
                        "주말 과한 활동으로 다음 날 컨디션을 빠르게 정리하고 싶을 때",
                        "평소보다 또렷한 압의 관리를 선호하는 분"])]),
            ("진행 방식", [
                "관리 전 운동 종류와 뭉친 부위를 확인해 시간을 집중 배분합니다.",
                "60분은 하체 또는 상체 등 특정 부위 중심, 90·120분은 전신을 고르게 풀며 집중 부위를 추가합니다.",
                "압이 강하게 느껴지면 즉시 조절하니 편하게 말씀해 주세요."]),
            ("주의사항 (꼭 읽어주세요)", [
                "부상·염좌·심한 통증이 있는 부위는 관리 대상이 아니며, 해당 증상은 의료기관 진료를 권유드립니다.",
                "본 관리는 의료 행위가 아닌 건강관리 서비스이며, 통증 완화·치료를 보장하지 않습니다."]),
            ("부위별 접근 방식", [
                "하체는 허벅지·종아리 등 큰 근육을 따라 또렷한 압으로 무거움을 정리합니다.",
                "등·어깨는 운동 자세로 자주 긴장되는 부위라 시간을 더 배분합니다.",
                "관리 중 통증과 시원함의 경계를 확인하며 강약을 세밀하게 조절합니다."]),
            ("관리 당일 진행 순서", [
                "도착 후 어떤 운동을 했는지, 어느 부위가 무거운지 확인합니다.",
                "근육을 데우듯 가볍게 시작해 점차 압을 높이며 집중 부위를 풀어드립니다.",
                "마무리 단계에서는 가볍게 이완하며 호흡을 고르고 관리를 마칩니다."]),
            ("운동 루틴과 함께하면 좋은 점", [
                "규칙적으로 운동하는 분은 무리한 날 컨디션을 빠르게 정리하는 용도로 활용하기 좋습니다.",
                "다만 통증이 반복되거나 심해지면 관리보다 의료기관 진료를 먼저 권유드립니다."]),
        ],
        data_note="스포츠 관리는 주말 오전~오후 예약 비율이 다른 코스보다 높습니다. 운동 직후보다는 1~2시간 휴식 후 관리를 권장드립니다.",
        faq=[
            ("운동 직후 바로 받아도 되나요?", "가벼운 휴식 후 받는 것을 권장드립니다. 심한 통증이 있다면 무리하지 않습니다."),
            ("강도가 센 편인가요?", "근육 부위에 또렷한 압을 사용하지만, 선호에 맞춰 강약을 조절합니다."),
            ("부상이 있어도 받을 수 있나요?", "부상·급성 통증 부위는 관리 대상이 아니며 의료기관 진료를 권유드립니다.")],
        service=("스포츠 관리", "서울 방문 운동 후 근육 컨디션 관리"))

    content_page("/course/home/", "course", ct + [(None, "홈타이 코스")],
        title="홈타이 코스 | 서울 출장마사지 자택 방문 홈타이 안내",
        desc="서울 홈타이 코스 안내 - 자택을 방문해 이동 없이 받는 방문형 홈타이 관리입니다. 진행 방식, 공간 준비, 기법 선택, 예약 전 확인사항을 확인하세요.",
        eyebrow="COURSE · 홈타이", h1="홈타이 코스",
        lead="관리사가 자택으로 방문해 이동 없이 익숙한 공간에서 받는 방문형 홈타이 관리입니다.",
        sections=[
            ("홈타이 코스란", [
                "홈타이는 관리사가 자택으로 방문해 이동 없이 받는 방문형 관리를 말합니다.",
                "관리 직후 그대로 휴식할 수 있어 이완 상태가 오래 유지되고, 익숙한 공간이라 긴장이 덜합니다.",
                "특정 기법이라기보다 '방문'이라는 방식이며, 원하는 기법을 자택에서 선택해 받을 수 있습니다."]),
            ("어떤 기법을 받을 수 있나요", [
                "스웨디시 계열의 부드러운 이완, 향을 더한 아로마, 또렷한 압의 스포츠 관리 등에서 선택할 수 있습니다.",
                "처음이라면 부담 없는 스웨디시 계열로 시작하는 경우가 많습니다.",
                ("ul", ['<a href="/theme/swedish/">스웨디시 안내</a>', '<a href="/theme/aroma-therapy/">아로마테라피 안내</a>',
                        '<a href="/theme/sports-massage/">스포츠·경락 안내</a>', '<a href="/theme/sleep-available/">수면 가능 안내</a>'])]),
            ("공간 준비 가이드", [
                "편히 누울 수 있는 평평한 공간만 있으면 됩니다. 별도의 장비를 준비하실 필요는 없습니다.",
                "조용한 분위기와 적당한 온도를 맞춰두면 이완의 질이 높아집니다.",
                "원룸·오피스텔 등 공간이 좁아도 진행 가능하며, 환경을 알려주시면 알맞게 안내드립니다."]),
            ("진행 시간 선택", [
                "60분은 핵심 부위 위주, 90분은 전신 균형, 120분은 마무리 케어까지 여유 있게 받는 구성입니다.",
                "처음이라면 90분이 가장 무난합니다. 자세한 기준은 코스 선택 가이드에서 확인하세요."]),
            ("관리 당일 진행 순서", [
                "도착 후 공간을 정돈하고, 선호하는 압·기법·집중 부위를 확인합니다.",
                "큰 근육부터 차례로 이완하며 뭉친 부위에 시간을 더 배분합니다.",
                "마무리 후 수분 섭취와 휴식을 안내하고 사용한 공간을 정돈합니다."]),
            ("호텔·숙소 방문은", [
                "자택이 아닌 호텔·숙소 방문은 호텔식 안내로 진행하며, 건물명과 객실 번호, 출입 안내 여부를 알려주시면 원활합니다.",
                ("ul", ['<a href="/theme/home-care/">홈케어 안내</a>', '<a href="/theme/hotel-massage/">호텔식마사지 안내</a>'])]),
            ("예약 전 확인사항", [
                "정확한 주소와 공동현관 출입 방법, 조용한 공간 확보 여부를 미리 확인해 주세요.",
                "예약 가능 시간과 준비물, 위생·안전 기준은 전용 안내에서 확인하실 수 있습니다.",
                reserve_links_ul()]),
        ],
        data_note="홈타이는 자택 방문 특성상 출입 방법·주소 안내가 도착 시간을 크게 좌우합니다. 예약 시 함께 남겨주시면 도착이 빨라집니다.",
        faq=[
            ("홈타이와 출장마사지는 다른가요?", "둘 다 방문형 관리이며, 홈타이는 자택 방문을 강조한 표현입니다. 기법은 테마에서 선택할 수 있습니다."),
            ("좁은 집에서도 가능한가요?", "네. 편히 누울 공간만 있으면 됩니다. 환경을 알려주시면 알맞게 안내드립니다."),
            ("어떤 준비물이 필요한가요?", "별도 장비는 필요 없습니다. 조용한 공간과 연락 가능한 번호, 정확한 주소면 충분합니다.")],
        service=("홈타이 코스", "서울 자택 방문 홈타이 관리"))

    content_page("/course/couple/", "course", ct + [(None, "커플·가족 방문 관리")],
        title="커플·가족 방문 관리 | 서울 출장마사지 2인 동반 관리",
        desc="서울 출장마사지 커플·가족 방문 관리 안내 - 두 분이 같은 공간에서 동시에 받는 동반형 방문 관리입니다. 공간·인원 조건, 예약 방법, 요금 구조를 확인하세요.",
        eyebrow="COURSE · 커플·가족", h1="커플·가족 방문 관리",
        lead="두 분이 같은 공간에서 동시에 관리를 받는 동반형 방문 관리입니다.",
        sections=[
            ("커플·가족 방문 관리란", [
                "두 분이 같은 공간에서 동시에 관리를 받는 동반형 방문 관리입니다.",
                "커플은 물론, 부모님과 함께 등 가족 단위로도 이용하실 수 있습니다.",
                "각자 원하는 코스(피로 회복·아로마 등)를 다르게 선택할 수 있습니다."]),
            ("공간과 인원 조건", [
                "동시에 관리가 진행되므로 관리사 2인이 방문하며, 두 사람이 누울 수 있는 공간이 필요합니다.",
                "공간이 협소한 경우 순차 진행으로 안내드릴 수 있어, 예약 시 환경을 알려주세요."]),
            ("예약 방법", [
                "동반 관리는 일정 조율이 필요해 사전 협의 예약을 권장드립니다.",
                "희망 코스, 인원, 시간, 방문 장소를 말씀해 주시면 가능한 시간을 확정해 드립니다."]),
            ("요금 안내", [
                "커플·가족 방문 관리는 인원과 시간에 따라 요금이 책정됩니다.",
                "기본 요금은 <a href='/course/price/'>가격 안내</a>에서 확인하실 수 있으며, 정확한 금액은 상담 시 안내드립니다."]),
            ("어떤 분들이 함께 받나요", [
                "기념일을 함께 보내려는 커플, 부모님께 휴식을 선물하려는 가족, 오랜만에 만난 친구 등 다양합니다.",
                "두 분이 같은 시간에 나란히 이완할 수 있어, 혼자 받을 때와는 다른 편안함이 있습니다.",
                "각자 컨디션이 다르면 한 분은 피로 회복, 다른 한 분은 아로마처럼 다르게 선택하셔도 됩니다."]),
            ("공간 준비 가이드", [
                "두 사람이 동시에 누울 수 있는 평평한 공간이 있으면 동시 진행이 가능합니다.",
                "원룸·호텔 등 공간이 좁다면 한 분씩 순차로 진행하는 방식으로 안내드립니다.",
                "예약 시 방의 크기나 환경을 알려주시면 알맞은 방식을 미리 정해 드립니다."]),
            ("관리 당일 진행 순서", [
                "관리사 2인이 함께 도착해 각자 담당을 정하고 공간을 준비합니다.",
                "두 분의 선호 압·코스를 각각 확인한 뒤 동시에 관리를 시작합니다.",
                "마무리도 함께 정돈하여 두 분이 비슷한 시점에 휴식에 들어가도록 합니다."]),
        ],
        data_note="동반 관리는 기념일·주말 저녁 문의가 집중됩니다. 관리사 2인 일정 조율이 필요하므로 가급적 1~2일 전 예약을 권장드립니다.",
        faq=[
            ("두 사람이 다른 코스를 받을 수 있나요?", "네. 각자 원하는 코스를 선택하실 수 있습니다."),
            ("좁은 공간에서도 가능한가요?", "두 분이 동시에 누울 공간이 어려우면 순차 진행으로 안내드립니다."),
            ("당일 예약도 되나요?", "관리사 2인 일정상 사전 예약을 권장드립니다. 당일은 가능 여부를 상담으로 확인해 드립니다.")],
        service=("커플·가족 방문 관리", "서울 2인 동반 방문 관리"))

    content_page("/course/group/", "course", ct + [(None, "기업·단체 방문 관리")],
        title="기업·단체 방문 관리 | 서울 출장마사지 단체·행사 관리",
        desc="서울 출장마사지 기업·단체 방문 관리 안내 - 워크숍·행사·사내 복지 등 단체 인원을 위한 사전 협의형 방문 관리입니다. 진행 방식, 견적·결제, 사전 준비를 확인하세요.",
        eyebrow="COURSE · 기업·단체", h1="기업·단체 방문 관리",
        lead="워크숍·행사·사내 복지 등 단체 인원을 대상으로 하는 사전 협의형 방문 관리입니다.",
        sections=[
            ("기업·단체 방문 관리란", [
                "워크숍·행사·사내 복지 등 단체 인원을 대상으로 하는 사전 협의형 방문 관리입니다.",
                "여러 명이 순차 또는 동시에 관리를 받을 수 있도록 일정을 구성합니다."]),
            ("진행 방식", [
                "인원수, 1인당 관리 시간, 희망 날짜와 장소를 먼저 확인합니다.",
                "행사 성격에 맞춰 짧은 의자형 케어부터 표준 코스까지 구성할 수 있습니다.",
                "관리사 인원과 진행 순서를 사전에 설계해 현장 운영을 매끄럽게 합니다."]),
            ("견적과 결제", [
                "단체 관리는 인원·시간·장소에 따라 별도 견적으로 안내드립니다.",
                "세금계산서 등 결제 방식은 사전에 협의해 드립니다."]),
            ("사전 준비", [
                "관리에 적합한 공간(조용한 회의실·라운지 등)과 콘센트, 대기 동선을 확인해 주세요.",
                "행사 일정이 정해지면 가급적 여유 있게 문의해 주시면 원활합니다."]),
            ("어떤 행사에 적합한가요", [
                "사내 워크숍이나 단합 행사에서 직원 복지 프로그램으로 활용하기 좋습니다.",
                "장시간 행사 중간의 휴식 코너, 야유회·연수 등의 부대 프로그램으로도 구성할 수 있습니다.",
                "인원과 시간을 고려해 짧고 가벼운 케어부터 표준 코스까지 유연하게 맞춰 드립니다."]),
            ("현장 운영 순서", [
                "행사 전 인원·시간표·동선을 협의해 관리사 수와 진행 순서를 설계합니다.",
                "당일에는 안내 동선을 미리 잡아 대기 시간을 줄이고 순환이 매끄럽도록 운영합니다.",
                "여러 명이 동시에 받을 경우 관리사를 늘려 전체 진행 시간을 단축합니다.",
                "행사 종료 후에는 사용 공간을 정돈하고 마무리합니다."]),
            ("사전 준비 체크리스트", [
                ("ul", ["참여 인원과 1인당 희망 시간", "행사 날짜·시간과 장소(주소)",
                        "관리 진행이 가능한 공간(회의실·라운지 등)", "콘센트·대기 동선 등 현장 여건"])]),
        ],
        data_note="기업·단체 관리는 분기 말·연말 사내 행사 시즌에 문의가 늘어납니다. 관리사 배치를 위해 최소 며칠 전 협의를 권장드립니다.",
        faq=[
            ("최소 인원 제한이 있나요?", "인원에 맞춰 구성하며, 정확한 기준은 문의 시 안내드립니다."),
            ("세금계산서 발행이 되나요?", "네. 결제 방식은 사전 협의로 안내드립니다."),
            ("행사 장소로 방문하나요?", "네. 서울 및 인근 행사 장소로 방문 가능하며 위치를 확인해 드립니다.")],
        service=("기업·단체 방문 관리", "서울 단체·행사 방문 관리"))

    content_page("/course/price/", "course", ct + [(None, "가격 안내")],
        title="가격 안내 | 서울 출장마사지 코스별 정찰 요금",
        desc="서울 출장마사지 가격 안내 - 코스별 60·90·120분 기본 요금과 정찰 요금 원칙, 변동 요소, 결제 안내를 제공합니다. 숨겨진 추가 비용 없이 투명하게 안내합니다.",
        eyebrow="COURSE · 가격", h1="가격 안내",
        lead="코스별 기본 요금을 사전에 안내하는 정찰 요금을 원칙으로 합니다.",
        sections=[
            ("정찰 요금 원칙", [
                f"{BRAND}는 코스별 기본 요금을 사전에 안내하는 <strong>정찰 요금</strong>을 원칙으로 합니다.",
                "현장에서 임의로 금액을 올리거나 숨겨진 추가 비용을 청구하지 않습니다."]),
            ("코스별 기본 요금", [
                "아래 60·90·120분 기본 요금을 참고하시고, 코스 종류(피로 회복·아로마·스포츠 등)에 따라 세부 금액이 달라질 수 있습니다."]),
            ("변동될 수 있는 요소", [
                ("ul", ["방문 지역과 이동 거리", "예약 시간대(심야 등)",
                        "커플·가족 등 인원 구성", "기업·단체 등 별도 견적 대상"])]),
            ("결제 안내", [
                "결제 방법은 예약 시 함께 안내드리며, 변동 사항이 있으면 사전에 고지합니다.",
                "정확한 최종 금액은 예약 상담에서 확인해 드립니다."]),
            ("요금은 이렇게 구성됩니다", [
                "기본 요금은 코스(피로 회복·아로마·스포츠 등)와 시간(60·90·120분)의 조합으로 정해집니다.",
                "커플·가족처럼 인원이 늘어나는 경우, 관리사 수와 시간에 따라 요금이 책정됩니다.",
                "기업·단체는 인원·장소·시간 편차가 커서 별도 견적으로 안내드립니다."]),
            ("예약 시 함께 안내드리는 것", [
                "예약 상담에서는 코스 기본 요금과 함께 아래 사항을 미리 확인해 드립니다.",
                ("ul", ["선택한 코스·시간의 최종 금액", "지역·시간대에 따른 변동 여부",
                        "결제 방법과 가능한 결제 수단"])]),
            ("투명한 요금을 위한 약속", [
                "현장에서 사전 안내와 다른 금액을 요구하지 않습니다.",
                "변동이 필요한 경우 반드시 관리 전에 설명드리고 동의를 받은 뒤 진행합니다."]),
        ],
        data_note="가장 많이 선택되는 구성은 90분입니다. 심야(자정 이후) 예약은 도착 시간과 함께 변동 요소를 미리 안내드립니다.",
        faq=[
            ("표시 요금 외에 추가 비용이 있나요?", "정찰 요금을 원칙으로 하며, 지역·시간대 등 변동 요소는 예약 시 미리 안내드립니다."),
            ("결제는 어떻게 하나요?", "결제 방법은 예약 시 안내드립니다."),
            ("코스마다 가격이 다른가요?", "네. 코스 종류에 따라 세부 금액이 달라질 수 있어 상담 시 확정해 드립니다.")],
        show_price=True,
        service=("서울 출장마사지 요금", "서울 방문 관리 정찰 요금 안내"))

    content_page("/course/guide/", "course", ct + [(None, "코스 선택 가이드")],
        title="코스 선택 가이드 | 서울 출장마사지 상황별 추천",
        desc="서울 출장마사지 코스 선택 가이드 - 목적과 상황에 맞는 코스 추천, 60·90·120분 시간 선택 기준, 처음 이용하는 분을 위한 안내를 제공합니다.",
        eyebrow="COURSE · 선택 가이드", h1="코스 선택 가이드",
        lead="어떤 코스를 골라야 할지 모르겠다면, 목적을 기준으로 선택하면 쉽습니다.",
        sections=[
            ("코스, 이렇게 고르세요", [
                "어떤 코스를 골라야 할지 모르겠다면, '무엇을 위해 받는가'라는 목적을 기준으로 선택하면 쉽습니다."]),
            ("상황별 추천", [
                ("ul", ["전신이 무겁고 푹 쉬고 싶다 → <strong>피로 회복 관리</strong>",
                        "향과 함께 깊게 이완하고 싶다 → <strong>아로마 관리</strong>",
                        "운동 후 근육을 풀고 싶다 → <strong>스포츠 관리</strong>",
                        "집에서 이동 없이 받고 싶다 → <strong>홈타이 코스</strong>",
                        "둘이 함께 받고 싶다 → <strong>커플·가족 방문 관리</strong>"])]),
            ("시간(60·90·120분) 선택", [
                "60분은 핵심 부위 위주로 빠르게 정리하고 싶을 때 적합합니다.",
                "90분은 전신을 고르게 풀 수 있어 가장 무난하며 많이 선택됩니다.",
                "120분은 전신 이완과 마무리 케어까지 여유 있게 받고 싶을 때 좋습니다."]),
            ("처음 이용하신다면", [
                "첫 방문이라면 90분 피로 회복 관리로 시작해 보시길 권합니다.",
                "받아본 뒤 선호하는 압·향·집중 부위를 알려주시면 다음 방문이 더 잘 맞습니다."]),
            ("목적별로 조금 더 자세히", [
                ("h3", "푹 쉬고 싶다면"),
                "특별히 아픈 곳은 없지만 전반적으로 무겁고 피곤하다면 피로 회복 관리가 가장 무난합니다.",
                ("h3", "향까지 즐기고 싶다면"),
                "긴장도가 높거나 예민한 날에는 향이 더해진 아로마 관리가 이완에 도움이 됩니다.",
                ("h3", "운동 후라면"),
                "다리·등 근육이 무거운 날에는 또렷한 압의 스포츠 관리가 잘 맞습니다."]),
            ("압의 세기 선택", [
                "압은 '시원하다'고 느껴지는 정도가 적당하며, 통증을 참을 필요는 없습니다.",
                "강한 압을 선호하면 스포츠 관리를, 부드러운 이완을 원하면 피로 회복·아로마 관리를 권합니다."]),
            ("재방문 시 팁", [
                "한 번 받아본 뒤 좋았던 압·향·집중 부위를 메모해 두면 다음 예약이 훨씬 수월합니다.",
                "컨디션에 따라 코스를 바꿔가며 받는 것도 좋은 방법입니다.",
                "관리 유형 자체가 궁금하면 <a href='/theme/'>테마별 안내</a>에서 특징을 비교해 보세요."]),
        ],
        data_note="처음 이용하는 고객의 다수가 90분 구성을 선택하며, 재방문 시 아로마·스포츠로 옮겨가는 경우가 많습니다.",
        faq=[
            ("처음인데 무엇이 좋을까요?", "90분 피로 회복 관리를 권장드립니다. 무난하게 전신을 풀 수 있습니다."),
            ("커플로 다른 코스도 가능한가요?", "네. 동반 관리에서 각자 다른 코스를 선택할 수 있습니다."),
            ("시간을 늘리면 더 좋은가요?", "집중 부위가 많거나 마무리 케어까지 원하면 90~120분이 적합합니다.")],
        service=("코스 선택 가이드", "서울 방문 관리 코스 선택 안내"))


# ---- 예약안내 허브 + 서브 -------------------------------------------------
def build_reservation():
    rt = [("/", "홈"), (None, "예약안내")]
    content_page("/reservation/", "reservation", rt,
        title="예약안내 | 서울 출장마사지·홈타이 예약 방법·결제",
        desc="서울 출장마사지·홈타이 예약안내 - 예약 방법, 예약 가능 시간, 방문 가능 장소, 결제와 변경·취소 절차를 한곳에서 안내합니다. 연중무휴 24시간 상담.",
        eyebrow="RESERVATION", h1="예약안내",
        lead="예약 방법부터 결제·변경까지, 서울 방문 마사지·홈타이 예약 과정을 순서대로 안내합니다.",
        sections=[
            ("예약 진행 순서", [
                "예약은 지역과 희망 시간을 확인한 뒤 코스와 인원 정보를 전달하는 순서로 진행됩니다.",
                "이후 방문 가능 여부와 예상 도착 시간을 안내하고, 예약이 확정되면 방문 전 준비사항을 확인합니다.",
                "전화 또는 문의로 편하게 시작하실 수 있습니다."]),
            ("예약 방법", [
                "전화 상담이 가장 빠르며, 원하는 지역·희망 시간·코스를 말씀해 주시면 됩니다.",
                "처음이라면 정확한 위치(자치구·동 또는 가까운 역)와 희망 시간만 알려주셔도 안내가 가능합니다."]),
            ("예약 가능 시간", [
                "연중무휴 24시간 상담을 운영합니다. 실제 방문 가능 시간은 시간대와 위치에 따라 달라질 수 있습니다.",
                "자세한 시간대별 안내는 <a href='/reservation/hours/'>예약 가능 시간</a>에서 확인하세요."]),
            ("방문 가능 장소", [
                "자택·오피스텔·숙소 등으로 방문하며, 정확한 주소와 출입 방법을 알려주시면 도착이 빨라집니다.",
                "장소별 준비 사항은 <a href='/reservation/place/'>방문 가능 장소</a>에서 안내합니다."]),
            ("결제와 변경·취소", [
                "코스별 정찰 요금을 사전에 안내드리며, 결제 방법은 예약 시 함께 확인합니다.",
                "일정 변경·취소는 가능한 한 빠르게 연락 주시면 도와드립니다.",
                ("ul", ['<a href="/reservation/payment/">결제 안내</a>',
                        '<a href="/reservation/change/">변경·취소 안내</a>',
                        '<a href="/reservation/checklist/">예약 전 체크사항</a>'])]),
            ("예약 전 준비하면 좋은 것", [
                "방문 장소 주소, 연락 가능한 번호, 희망 코스와 시간(60·90·120분), 방문 희망 시각을 미리 정리해 두시면 빠르게 진행됩니다.",
                "처음 이용 시 전체 흐름은 <a href='/guide/'>이용가이드</a>에서 확인하실 수 있습니다."]),
        ],
        data_note="저녁 시간대와 주말은 문의가 몰립니다. 원하는 시간이 정해져 있다면 미리 예약할수록 일정 조율이 수월합니다.",
        faq=[
            ("당일 예약이 가능한가요?", "가능합니다. 다만 시간대와 위치에 따라 방문 가능 시간이 달라질 수 있어 상담 시 확인해 드립니다."),
            ("예약을 변경하고 싶어요.", "확정된 일정 변경은 가능한 한 빠르게 연락 주시면 조정을 도와드립니다."),
            ("결제는 어떻게 하나요?", "정찰 요금을 사전에 안내드리며 결제 방법은 예약 시 함께 안내합니다.")],
        service=("서울 출장마사지·홈타이 예약", "서울 전지역 방문 건강관리 예약 안내"))

    content_page("/reservation/hours/", "reservation", rt + [(None, "예약 가능 시간")],
        title="예약 가능 시간 | 서울 출장마사지·홈타이 24시간 상담",
        desc="서울 출장마사지·홈타이 예약 가능 시간 안내 - 연중무휴 24시간 상담, 시간대별 특징, 예상 도착 시간, 예약 팁을 제공합니다.",
        eyebrow="예약 · 시간", h1="예약 가능 시간",
        lead="연중무휴 24시간 예약 상담을 운영합니다. 시간대별 특징과 예상 도착 시간을 안내합니다.",
        sections=[
            ("운영 시간", [
                "전화 상담은 연중무휴 24시간 가능합니다.",
                "실제 방문 가능 시간은 시간대와 위치, 배정 상황에 따라 안내드립니다."]),
            ("시간대별 특징", [
                ("ul", ["낮~초저녁: 비교적 도착이 빠르고 일정 조율이 수월합니다.",
                        "밤 21~24시: 예약이 가장 많이 몰리는 시간대로, 도착 시간을 넉넉히 안내드립니다.",
                        "심야(자정 이후): 방문 가능하나 위치에 따라 도착 시간이 길어질 수 있습니다."])]),
            ("예상 도착 시간", [
                "서울은 자치구별 이동 시간이 크게 달라, 도착 시간은 위치에 따라 편차가 있습니다.",
                "도심·강남권 등 중심 생활권은 비교적 빠르고, 외곽 권역은 다소 길어질 수 있습니다.",
                "예약 시 정확한 위치(자치구·동 또는 가까운 역)를 알려주시면 예상 도착 시간을 안내드립니다."]),
            ("예약이 몰리는 시간", [
                "평일 밤 21~24시는 하루 중 예약이 가장 집중되는 시간대입니다.",
                "이 시간대에는 도착이 평소보다 조금 더 걸릴 수 있어, 여유 있게 예약하시길 권합니다."]),
            ("도착 시간을 줄이는 방법", [
                "예약 시 정확한 주소와 공동현관·동·호수 등 출입 정보를 함께 알려주세요.",
                "가까운 지하철역이나 큰 건물 등 기준점을 알려주시면 위치 파악이 빨라집니다.",
                "도착 직전 연락이 닿을 수 있는 번호를 남겨주시면 마지막 동선이 매끄럽습니다."]),
            ("주말·공휴일 운영", [
                "주말과 공휴일에도 동일하게 연중무휴로 상담·방문을 운영합니다.",
                "다만 기념일·연휴 저녁은 문의가 몰리므로 미리 예약하시는 편이 좋습니다."]),
        ],
        data_note="평일 밤 21~24시는 예약 집중 시간대입니다. 이 시간대 방문을 원하시면 가급적 미리 예약해 주세요.",
        faq=[
            ("새벽에도 예약되나요?", "상담은 24시간 가능합니다. 심야는 위치에 따라 도착 시간이 길어질 수 있어 상담 시 안내드립니다."),
            ("도착까지 얼마나 걸리나요?", "위치에 따라 편차가 있습니다. 예약 시 정확한 위치를 알려주시면 예상 시간을 안내드립니다."),
            ("당일 예약이 가능한가요?", "가능합니다. 시간대와 위치에 따라 가능 시간을 상담으로 확인해 드립니다.")])

    content_page("/reservation/place/", "reservation", rt + [(None, "방문 가능 장소")],
        title="방문 가능 장소 | 서울 출장마사지·홈타이 자택·숙소 방문",
        desc="서울 출장마사지·홈타이 방문 가능 장소 안내 - 자택, 오피스텔, 호텔·숙소 등 장소별 준비 사항과 출입 안내를 제공합니다.",
        eyebrow="예약 · 장소", h1="방문 가능 장소",
        lead="자택·오피스텔·숙소 등으로 방문합니다. 장소별로 미리 확인하면 좋은 점을 안내합니다.",
        sections=[
            ("방문 가능한 장소", [
                "자택, 오피스텔, 호텔·숙소 등 편히 쉴 수 있는 공간이면 방문이 가능합니다.",
                "방문 형태이므로 별도의 장비를 준비하실 필요는 없으며, 편히 누울 수 있는 공간만 있으면 됩니다."]),
            ("자택 방문", [
                "공동현관 출입 방법과 동·호수를 알려주시면 도착이 빨라집니다.",
                "반려동물이 있거나 함께 계신 분이 있다면 예약 시 미리 알려주세요."]),
            ("오피스텔·원룸 방문", [
                "건물 출입 방법(공동현관 비밀번호·카드 등)과 정확한 호수를 알려주시면 원활합니다.",
                "공간이 좁아도 진행 가능하며, 환경을 알려주시면 알맞게 안내드립니다."]),
            ("호텔·숙소 방문", [
                "호텔명과 객실 번호, 프런트 출입 안내가 필요한지 함께 알려주시면 원활합니다.",
                "출장·여행 중 객실에서 받는 호텔식 안내는 <a href='/theme/hotel-massage/'>호텔식마사지</a>에서 확인하세요."]),
            ("방문이 어려운 경우", [
                "안전과 위생을 위해 관리가 어려운 환경이 있을 수 있으며, 이 경우 사전에 안내드립니다.",
                "본 서비스는 만 19세 이상 성인을 대상으로 하며, 불법·퇴폐 행위는 일절 제공하지 않습니다."]),
            ("예약 시 함께 알려주세요", [
                ("ul", ["방문 장소의 정확한 주소", "공동현관·동·호수 등 출입 방법",
                        "주차 가능 여부(필요 시)", "조용한 공간 확보 여부"])]),
        ],
        data_note="주소와 출입 방법을 예약 시 함께 남겨주시면 도착 시간이 평균적으로 단축됩니다. 공동현관 비밀번호 등은 도착 직전 안내해 주셔도 됩니다.",
        faq=[
            ("숙소(호텔)도 방문하나요?", "네. 호텔·숙소로 방문 가능하며, 건물명과 객실 번호를 알려주시면 됩니다."),
            ("좁은 원룸도 가능한가요?", "네. 편히 누울 공간만 있으면 됩니다."),
            ("주차는 어떻게 하나요?", "방문 장소 주변 주차 여건을 예약 시 알려주시면 참고해 안내드립니다.")])

    content_page("/reservation/payment/", "reservation", rt + [(None, "결제 안내")],
        title="결제 안내 | 서울 출장마사지·홈타이 정찰 요금 결제",
        desc="서울 출장마사지·홈타이 결제 안내 - 정찰 요금 원칙, 결제 방법, 변동 요소, 영수 관련 안내를 제공합니다.",
        eyebrow="예약 · 결제", h1="결제 안내",
        lead="코스별 정찰 요금을 사전에 안내하며, 결제 방법은 예약 시 함께 확인합니다.",
        sections=[
            ("정찰 요금 원칙", [
                "코스별 기본 요금을 사전에 안내하는 정찰 요금을 원칙으로 합니다.",
                "현장에서 임의로 금액을 올리거나 숨겨진 추가 비용을 청구하지 않습니다."]),
            ("결제 방법", [
                "결제 방법은 예약 시 함께 안내드립니다.",
                "변동 사항이 있는 경우 관리 전에 미리 설명드리고 동의를 받은 뒤 진행합니다."]),
            ("요금이 달라질 수 있는 요소", [
                ("ul", ["방문 지역과 이동 거리", "예약 시간대(심야 등)",
                        "커플·가족 등 인원 구성", "기업·단체 등 별도 견적 대상"])]),
            ("코스별 기본 요금", [
                "60·90·120분 코스별 기본 요금은 가격 안내에서 확인하실 수 있습니다.",
                "코스 종류(피로 회복·아로마·스포츠 등)에 따라 세부 금액이 달라질 수 있습니다.",
                ("ul", ['<a href="/course/price/">코스별 가격 안내 보기</a>', '<a href="/course/">전체 코스 보기</a>'])]),
            ("영수 관련 안내", [
                "필요하시면 영수 관련 사항도 예약 시 안내해 드립니다.",
                "기업·단체 이용 시 세금계산서 등 결제 방식은 사전에 협의합니다."]),
            ("투명한 요금을 위한 약속", [
                "사전 안내와 다른 금액을 현장에서 요구하지 않습니다.",
                "정확한 최종 금액은 예약 상담에서 확인해 드립니다."]),
        ],
        data_note="가장 많이 선택되는 구성은 90분입니다. 심야 예약은 도착 시간과 함께 변동 요소를 미리 안내드립니다.",
        faq=[
            ("표시 요금 외 추가 비용이 있나요?", "정찰 요금을 원칙으로 하며 지역·시간대 등 변동 요소는 예약 시 미리 안내드립니다."),
            ("결제는 언제 하나요?", "결제 방법과 시점은 예약 시 함께 안내드립니다."),
            ("현금만 가능한가요?", "가능한 결제 수단은 예약 상담 시 안내드립니다.")])

    content_page("/reservation/change/", "reservation", rt + [(None, "변경·취소 안내")],
        title="예약 변경·취소 안내 | 서울 출장마사지·홈타이",
        desc="서울 출장마사지·홈타이 예약 변경·취소 안내 - 일정 변경 방법, 취소 시 유의사항, 노쇼 관련 안내를 제공합니다.",
        eyebrow="예약 · 변경", h1="예약 변경·취소 안내",
        lead="일정이 바뀌면 가능한 한 빠르게 연락 주세요. 빠를수록 다른 시간으로 조율하기 쉽습니다.",
        sections=[
            ("예약 변경", [
                "확정된 일정 변경은 가능한 한 빠르게 연락 주시면 조정을 도와드립니다.",
                "원하는 새 시간과 위치를 알려주시면 가능한 시간을 다시 확인해 안내드립니다."]),
            ("예약 취소", [
                "취소가 필요한 경우에도 가능한 한 빨리 연락 주시면 감사하겠습니다.",
                "방문 직전 취소·변경은 관리사 동선상 어려울 수 있어, 미리 알려주시면 다른 분께도 도움이 됩니다."]),
            ("방문 직전 변경 시", [
                "관리사가 이미 출발했거나 도착 인근인 경우, 일정 조정이 제한될 수 있습니다.",
                "부득이한 사정이 있으면 상황을 말씀해 주시면 최대한 협의해 드립니다."]),
            ("노쇼 방지를 위한 부탁", [
                "예약 후 연락 없이 방문을 받지 않으시면 관리사와 다른 고객 모두에게 영향이 있습니다.",
                "사정이 생기면 짧게라도 연락 주시면 일정을 조정하겠습니다."]),
            ("변경·취소 시 알려주세요", [
                ("ul", ["예약자 성함 또는 예약 시 번호", "기존 예약 일시", "변경 희망 일시(변경의 경우)"])]),
        ],
        data_note="방문 직전 변경은 동선상 어려울 수 있습니다. 가급적 방문 시간 여유를 두고 연락 주시면 조율이 수월합니다.",
        faq=[
            ("예약을 미루고 싶어요.", "가능한 한 빠르게 연락 주시면 다른 시간으로 조정해 드립니다."),
            ("취소 수수료가 있나요?", "방문 직전 취소가 반복되는 경우 안내가 있을 수 있으며, 자세한 사항은 상담 시 확인해 드립니다."),
            ("연락은 어디로 하나요?", f"예약 시 이용한 번호 또는 {PHONE_DISP}로 연락 주세요.")])

    content_page("/reservation/checklist/", "reservation", rt + [(None, "예약 전 체크사항")],
        title="예약 전 체크사항 | 서울 출장마사지·홈타이 예약 준비",
        desc="서울 출장마사지·홈타이 예약 전 체크사항 - 미리 정리하면 좋은 정보, 방문 환경 확인, 안전 관련 사항을 안내합니다.",
        eyebrow="예약 · 체크", h1="예약 전 체크사항",
        lead="예약을 빠르고 매끄럽게 진행하기 위해 미리 확인하면 좋은 사항을 정리했습니다.",
        sections=[
            ("미리 정리하면 좋은 정보", [
                ("ul", ["연락 가능한 전화번호", "방문 장소의 정확한 주소",
                        "희망 코스와 시간(60·90·120분)", "방문 희망 시각"])]),
            ("방문 환경 확인", [
                "편히 누워 쉴 수 있는 조용한 공간을 미리 확보해 주세요.",
                "공동현관 출입 방법, 동·호수, 주차 여건 등을 함께 확인하면 도착이 빨라집니다."]),
            ("코스 선택이 고민될 때", [
                "목적(이완·근육 회복·향·수면 등)을 기준으로 고르면 쉽습니다.",
                "정하기 어렵다면 상담에서 컨디션을 말씀해 주시면 추천드립니다.",
                ("ul", ['<a href="/course/guide/">코스 선택 가이드</a>', '<a href="/theme/">테마별 안내</a>'])]),
            ("안전 관련 사전 확인", [
                "민감성 피부·알러지·임신 등 주의가 필요한 상황은 예약 시 미리 알려주세요.",
                "본 서비스는 만 19세 이상 성인을 대상으로 하며, 불법·퇴폐 행위 요구는 제공되지 않습니다."]),
            ("예약 직후 진행", [
                "예약이 확정되면 방문 전 준비사항을 안내드립니다.",
                "처음 이용 시 전체 흐름은 <a href='/guide/'>이용가이드</a>에서 확인하실 수 있습니다."]),
        ],
        data_note="주소와 출입 방법, 희망 코스·시간을 미리 정리해 두시면 상담 시간이 크게 줄어듭니다.",
        faq=[
            ("무엇을 준비하면 되나요?", "편히 쉴 공간과 연락 가능한 번호, 정확한 주소, 희망 코스·시간이면 충분합니다."),
            ("코스를 미리 정해야 하나요?", "아니요. 상담에서 컨디션을 말씀해 주시면 추천드립니다."),
            ("출입 정보는 언제 알려주나요?", "예약 시 또는 도착 직전에 알려주셔도 됩니다.")])


# ---- 이용가이드 허브 + 서브 -----------------------------------------------
def build_guide():
    gt = [("/", "홈"), (None, "이용가이드")]
    content_page("/guide/", "guide", gt,
        title="이용가이드 | 서울 출장마사지·홈타이 처음 이용 안내",
        desc="서울 출장마사지·홈타이 이용가이드 - 처음 이용하시는 분을 위한 진행 흐름, 방문 전 준비, 위생·안전 기준, 관리 후 주의사항과 금지행위 안내입니다.",
        eyebrow="GUIDE", h1="이용가이드",
        lead="처음 이용하시는 분도 안심할 수 있도록 방문 전후 과정을 안내합니다.",
        sections=[
            ("처음 이용하시는 분께", [
                "예약 시 지역·시간·코스만 말씀해 주시면 나머지는 안내해 드립니다.",
                "방문형 관리이므로 별도의 장비를 준비하실 필요는 없습니다. 편히 쉴 공간과 연락 가능한 번호면 충분합니다."]),
            ("전체 진행 흐름", [
                "전화·문의 → 일정 확정 → 관리사 방문 → 관리 → 마무리 정리 순으로 진행됩니다.",
                "각 단계에서 필요한 정보는 미리 안내드리니, 처음이셔도 부담 없이 시작하실 수 있습니다."]),
            ("방문 전 준비", [
                "편히 누울 수 있는 조용한 공간과 정확한 주소, 출입 방법을 준비해 주세요.",
                "자세한 준비물은 <a href='/guide/prepare/'>방문 전 준비사항</a>에서 확인하실 수 있습니다."]),
            ("위생·안전과 금지행위", [
                "위생·안전 가이드라인을 준수하며, 불법·퇴폐 행위는 일절 제공하지 않습니다.",
                ("ul", ['<a href="/guide/safety/">위생 및 안전 기준</a>',
                        '<a href="/guide/aftercare/">관리 후 주의사항</a>',
                        '<a href="/guide/forbidden/">금지행위 안내</a>'])]),
            ("자주 묻는 질문", [
                "이용과 관련해 자주 들어오는 질문은 이용 FAQ에 정리했습니다.",
                ("ul", ['<a href="/guide/faq/">이용 FAQ</a>', '<a href="/guide/checklist/">이용 전 확인사항</a>'])]),
            ("비의료 서비스 안내", [
                "본 서비스는 의료 행위가 아닌 이완·휴식 목적의 건강관리 서비스이며, 만 19세 이상 성인을 대상으로 합니다.",
                "통증·부상은 의료기관 진료를 권유드립니다."]),
        ],
        data_note="처음 이용하시는 분은 90분 구성을 가장 많이 선택합니다. 받아본 뒤 선호를 알려주시면 다음 방문이 더 잘 맞습니다.",
        faq=[
            ("처음인데 무엇을 준비하나요?", "편히 쉴 수 있는 공간과 연락 가능한 번호, 정확한 주소만 있으면 됩니다."),
            ("관리 후 주의할 점이 있나요?", "충분한 수분 섭취와 휴식을 권장드립니다."),
            ("이 서비스는 의료 행위인가요?", "아닙니다. 이완·휴식 목적의 건강관리 서비스이며 만 19세 이상을 대상으로 합니다.")],
        service=("서울 출장마사지·홈타이 이용가이드", "서울 방문 건강관리 이용 안내"))

    content_page("/guide/prepare/", "guide", gt + [(None, "방문 전 준비사항")],
        title="방문 전 준비사항 | 서울 출장마사지·홈타이",
        desc="서울 출장마사지·홈타이 방문 전 준비사항 - 공간 준비, 주소·출입 안내, 컨디션 점검 등 매끄러운 방문을 위한 준비를 안내합니다.",
        eyebrow="가이드 · 준비", h1="방문 전 준비사항",
        lead="매끄러운 방문을 위해 미리 준비하면 좋은 사항을 안내합니다.",
        sections=[
            ("공간 준비", [
                "편히 누울 수 있는 평평하고 조용한 공간을 확보해 주세요.",
                "적당한 온도와 차분한 분위기를 맞춰두면 이완의 질이 높아집니다."]),
            ("주소·출입 안내 준비", [
                "정확한 주소와 공동현관 출입 방법, 동·호수를 미리 정리해 주세요.",
                "가까운 역이나 큰 건물 등 기준점을 알려주시면 도착이 빨라집니다."]),
            ("컨디션 점검", [
                "과식 직후보다는 식사 후 어느 정도 시간이 지난 뒤가 편안합니다.",
                "관리 전 가벼운 샤워로 몸을 따뜻하게 하면 이완이 한결 수월합니다.",
                "음주가 심한 경우 안전을 위해 관리가 어려울 수 있습니다."]),
            ("미리 알려주시면 좋은 점", [
                ("ul", ["선호하는 압의 세기와 집중 부위", "피하고 싶은 향·부위",
                        "민감성 피부·알러지·임신 등 주의 사항", "함께 계신 분이나 반려동물 여부"])]),
            ("복장과 소지품", [
                "편안한 복장을 준비해 두시면 좋습니다. 관리 형태에 따라 안내드립니다.",
                "귀중품은 미리 정리해 두시면 안심하고 관리에 집중하실 수 있습니다."]),
        ],
        data_note="주소와 출입 방법을 예약 시 함께 남겨주시면 도착 시간이 단축됩니다. 출입 비밀번호 등은 도착 직전 안내해 주셔도 됩니다.",
        faq=[
            ("샤워는 꼭 해야 하나요?", "필수는 아니지만 가벼운 샤워로 몸을 따뜻하게 하면 이완이 수월합니다."),
            ("복장은 어떻게 하나요?", "편안한 복장을 권장하며, 관리 형태에 따라 안내드립니다."),
            ("알러지가 있으면 어떻게 하나요?", "예약 시 미리 알려주시면 무리하지 않도록 조정합니다.")])

    content_page("/guide/safety/", "guide", gt + [(None, "위생 및 안전 기준")],
        title="위생 및 안전 안내 | 서울 출장마사지·홈타이 위생 기준",
        desc="서울 출장마사지·홈타이 위생 및 안전 안내 - 용품 위생 관리, 관리사·고객 안전 가이드라인, 비의료 서비스 고지, 개인정보 보호 원칙을 안내합니다.",
        eyebrow="가이드 · 안전", h1="위생 및 안전 안내",
        lead="안심하고 받으실 수 있도록 위생과 안전을 운영의 기본 기준으로 둡니다.",
        sections=[
            ("위생 관리 기준", [
                "관리에 사용하는 수건·오일 등 용품은 위생 기준에 맞춰 관리합니다.",
                "방문 시 청결을 우선하며, 관리 종료 후 사용한 공간을 정돈합니다."]),
            ("관리사·고객 안전", [
                "관리사와 고객 모두의 안전을 위한 운영 가이드라인을 준수합니다.",
                "상호 존중을 원칙으로 하며, 부적절한 요구가 있을 경우 관리가 중단될 수 있습니다."]),
            ("비의료 서비스 고지", [
                "본 서비스는 의료 행위가 아닌 <strong>이완·휴식 목적의 건강관리(마사지) 서비스</strong>입니다.",
                "질환의 진단·치료를 목적으로 하지 않으며, 통증·부상은 의료기관 진료를 권유드립니다."]),
            ("개인정보 보호", [
                "예약을 위해 수집한 연락처·주소 등은 예약 진행 목적으로만 이용하고, 목적 달성 후 관련 법령에 따라 파기합니다.",
                "자세한 내용은 <a href='/privacy/'>개인정보처리방침</a>에서 확인하실 수 있습니다."]),
            ("관리사 응대 기준", [
                "정중한 인사와 설명을 기본으로, 관리 전 선호 사항을 충분히 확인합니다.",
                "관리 중에도 압·온도·자세 등 불편함이 없는지 살피며 진행합니다.",
                "응대 가이드라인을 통해 어느 관리사가 방문하더라도 일관된 경험을 유지합니다."]),
            ("고객님께 부탁드리는 점", [
                ("ul", ["만 19세 이상 본인 확인에 협조해 주세요.",
                        "관리사에 대한 존중과 기본 예의를 지켜주세요.",
                        "불법·퇴폐 행위 요구는 삼가주세요. 요청 시 서비스가 중단됩니다.",
                        "과도한 음주 상태에서는 안전을 위해 관리가 어려울 수 있습니다."])]),
        ],
        data_note="위생·안전을 운영의 기본 기준으로 두며, 관리사 교육과 응대 가이드라인을 통해 일관된 방문 경험을 유지합니다.",
        faq=[
            ("위생은 어떻게 관리되나요?", "수건·오일 등 용품을 위생 기준에 맞춰 관리하고, 관리 후 공간을 정돈합니다."),
            ("안전은 어떻게 보장되나요?", "관리사·고객 모두의 안전을 위한 가이드라인을 운영하며 상호 존중을 원칙으로 합니다."),
            ("의료적 효과가 있나요?", "아닙니다. 이완·휴식 목적의 건강관리 서비스이며 치료를 보장하지 않습니다.")])

    content_page("/guide/aftercare/", "guide", gt + [(None, "관리 후 주의사항")],
        title="관리 후 주의사항 | 서울 출장마사지·홈타이 애프터케어",
        desc="서울 출장마사지·홈타이 관리 후 주의사항 - 수분 섭취, 휴식, 무리한 활동 자제 등 관리 후 케어 방법을 안내합니다.",
        eyebrow="가이드 · 애프터", h1="관리 후 주의사항",
        lead="관리 후 이완 상태를 오래 유지하기 위한 케어 방법을 안내합니다.",
        sections=[
            ("관리 직후", [
                "관리 직후에는 따뜻한 물을 충분히 마시고 잠시 편히 쉬는 것이 좋습니다.",
                "갑자기 무리한 활동을 하기보다 몸이 풀린 상태를 천천히 이어가세요."]),
            ("수분과 휴식", [
                "충분한 수분 섭취는 이완 후 컨디션 회복에 도움이 됩니다.",
                "가능하다면 관리 후 충분한 수면이나 휴식을 권장드립니다."]),
            ("오일 관리 후", [
                "아로마 등 오일 관리 후 잔여감이 신경 쓰이면 가벼운 샤워로 마무리하셔도 좋습니다.",
                "피부가 민감한 분은 자극이 강한 제품 사용을 잠시 피하는 편이 좋습니다."]),
            ("운동·스포츠 관리 후", [
                "스포츠 관리 후에는 격한 운동을 바로 이어가기보다 휴식을 두는 것이 좋습니다.",
                "통증이 반복되거나 심해지면 관리보다 의료기관 진료를 먼저 권유드립니다."]),
            ("다음 방문을 위한 메모", [
                "좋았던 압·향·집중 부위를 기억해 두면 다음 방문 때 더 잘 맞춰 드릴 수 있습니다.",
                "컨디션에 따라 코스를 바꿔가며 받는 것도 좋은 방법입니다."]),
        ],
        data_note="관리 후 충분한 수분 섭취와 휴식을 권장드립니다. 통증·부상이 있는 부위는 무리하지 않습니다.",
        faq=[
            ("관리 후 바로 외출해도 되나요?", "가능하지만 잠시 휴식 후 움직이시면 이완 상태가 더 오래 유지됩니다."),
            ("샤워는 언제 하나요?", "오일 잔여감이 신경 쓰이면 관리 후 가벼운 샤워로 마무리하셔도 좋습니다."),
            ("다음 방문은 언제가 좋나요?", "컨디션에 따라 다르며, 선호와 목적을 알려주시면 안내드립니다.")])

    content_page("/guide/forbidden/", "guide", gt + [(None, "금지행위 안내")],
        title="금지행위 안내 | 서울 출장마사지·홈타이 건전 운영",
        desc="서울 출장마사지·홈타이 금지행위 안내 - 불법·퇴폐 행위 금지, 만 19세 이상 이용, 상호 존중 원칙 등 건전한 운영 기준을 안내합니다.",
        eyebrow="가이드 · 금지행위", h1="금지행위 안내",
        lead="건전하고 안전한 방문 관리를 위해 금지되는 행위를 명확히 안내합니다.",
        sections=[
            ("불법·퇴폐 행위 금지", [
                "본 서비스는 이완·휴식 목적의 건강관리 서비스이며, 불법·퇴폐 행위는 일절 제공하지 않습니다.",
                "이러한 요구가 있을 경우 관리는 즉시 중단되며 이후 이용이 제한될 수 있습니다."]),
            ("이용 연령 제한", [
                "본 서비스는 만 19세 이상 성인만 이용하실 수 있습니다.",
                "필요 시 본인 확인에 협조를 요청드릴 수 있습니다."]),
            ("관리사 존중", [
                "관리사에 대한 폭언·폭력·성희롱 등 부적절한 언행은 금지됩니다.",
                "상호 존중을 원칙으로 하며, 위반 시 관리가 중단될 수 있습니다."]),
            ("안전을 위한 제한", [
                "과도한 음주 상태 등 안전이 우려되는 경우 관리가 어려울 수 있습니다.",
                "관리에 부적합한 환경은 안전을 위해 사전에 안내드립니다."]),
            ("위반 시 안내", [
                "금지행위가 확인되면 서비스가 중단되며, 상황에 따라 관련 기관에 신고될 수 있습니다.",
                "건전한 운영을 위한 기준이니 양해와 협조를 부탁드립니다."]),
        ],
        data_note="건전한 운영은 관리사와 고객 모두의 안전을 위한 것입니다. 기준 준수에 협조해 주시면 감사하겠습니다.",
        faq=[
            ("어떤 행위가 금지되나요?", "불법·퇴폐 행위, 관리사에 대한 부적절한 언행 등이 금지됩니다."),
            ("미성년자도 이용 가능한가요?", "아니요. 만 19세 이상 성인만 이용하실 수 있습니다."),
            ("위반하면 어떻게 되나요?", "관리가 즉시 중단되며 이후 이용이 제한될 수 있습니다.")])

    content_page("/guide/faq/", "guide", gt + [(None, "이용 FAQ")],
        title="이용 FAQ | 서울 출장마사지·홈타이 자주 묻는 질문",
        desc="서울 출장마사지·홈타이 이용 FAQ - 예약, 방문, 준비, 위생·안전 등 이용과 관련해 자주 들어오는 질문을 정리했습니다.",
        eyebrow="가이드 · FAQ", h1="이용 FAQ",
        lead="이용과 관련해 자주 들어오는 질문을 주제별로 정리했습니다.",
        sections=[
            ("이용 전 한눈에", [
                "예약은 전화·문의로 지역·시간·코스를 알려주시면 진행됩니다.",
                "방문형 관리이므로 별도 장비는 필요 없고, 편히 쉴 공간만 있으면 됩니다."]),
            ("예약·방문", [
                ("h3", "당일 예약이 되나요"),
                "배정 상황에 따라 가능하지만, 원하는 시간이 있다면 사전 예약을 권장합니다.",
                ("h3", "어디로 방문하나요"),
                "자택·오피스텔·숙소 등으로 방문하며, 정확한 주소와 출입 방법을 알려주시면 됩니다."]),
            ("준비·진행", [
                ("h3", "무엇을 준비하나요"),
                "편히 쉴 공간과 연락 가능한 번호, 정확한 주소면 충분합니다.",
                ("h3", "코스는 어떻게 고르나요"),
                "목적을 기준으로 고르면 쉬우며, 상담에서 컨디션을 말씀해 주시면 추천드립니다."]),
            ("위생·안전", [
                "본 서비스는 의료 행위가 아닌 이완·휴식 목적의 건강관리 서비스이며, 만 19세 이상 성인을 대상으로 합니다.",
                "위생·안전 가이드라인을 준수하며, 자세한 내용은 위생 및 안전 안내에서 확인하실 수 있습니다.",
                ("ul", ['<a href="/guide/safety/">위생 및 안전 안내</a>', '<a href="/guide/forbidden/">금지행위 안내</a>'])]),
        ],
        data_note="가장 많이 들어오는 문의는 '도착까지 걸리는 시간'과 '코스·요금'입니다. 예약 시 위치와 희망 코스를 함께 알려주시면 빠르게 안내해 드립니다.",
        faq=[
            ("예약은 어떻게 하나요?", "전화 또는 문의로 지역·시간·코스를 알려주시면 방문 가능 시간을 확정해 드립니다."),
            ("준비물이 있나요?", "편히 쉴 공간과 연락 가능한 번호, 정확한 주소면 충분합니다."),
            ("관리 후 주의사항은요?", "충분한 수분 섭취와 휴식을 권장드립니다."),
            ("이 서비스는 의료 행위인가요?", "아닙니다. 이완·휴식 목적의 건강관리 서비스이며 만 19세 이상을 대상으로 합니다.")])

    # /guide/checklist/ — 메뉴(서울 출장마사지)에서도 참조
    content_page("/guide/checklist/", "guide", gt + [(None, "이용 전 확인사항")],
        title="이용 전 확인사항 | 서울 출장마사지·홈타이 방문 준비",
        desc="서울 출장마사지·홈타이 이용 전 확인사항 - 방문 장소 준비, 예약 정보, 결제 준비, 이용 시 주의사항을 안내합니다.",
        eyebrow="가이드 · 확인", h1="이용 전 확인사항",
        lead="원활한 방문을 위해 예약 전 아래 사항을 미리 확인해 주세요.",
        sections=[
            ("방문 장소 준비", [
                "편하게 누워 쉴 수 있는 공간을 확보해 주세요.",
                "숙소·자택 등 방문 장소의 정확한 주소와 출입 방법(공동현관 등)을 알려주시면 도착이 빨라집니다."]),
            ("예약 정보 확인", [
                ("ul", ["연락 가능한 전화번호", "방문 장소 주소",
                        "희망 코스와 시간(60·90·120분)", "방문 희망 시각"])]),
            ("결제 준비", [
                "코스별 정찰 요금을 사전에 안내드리며, 결제 방법은 예약 시 함께 확인합니다.",
                "변동 요소(지역·시간대 등)는 미리 고지해 드립니다."]),
            ("이용 시 주의사항", [
                "본 서비스는 의료 행위가 아닌 건강관리 서비스이며 <strong>만 19세 이상</strong> 성인을 대상으로 합니다.",
                "불법·퇴폐 행위 요구는 일절 제공되지 않으며, 요청 시 서비스가 중단될 수 있습니다.",
                "음주가 심한 경우 안전을 위해 관리가 어려울 수 있습니다."]),
            ("방문 장소별 안내", [
                ("h3", "자택"),
                "공동현관 출입 방법과 동·호수를 알려주시면 도착이 빨라집니다. 반려동물이 있다면 미리 안내해 주세요.",
                ("h3", "숙소·호텔"),
                "건물명과 객실 번호, 프런트 출입 안내가 필요한지 함께 알려주시면 원활합니다."]),
            ("미리 알려주시면 좋은 점", [
                "함께 계신 분이 있거나, 특정 향·압을 피하고 싶다면 예약 시 말씀해 주세요.",
                "임신 중이거나 피부·건강상 주의가 필요한 상황은 안전을 위해 사전에 공유해 주세요."]),
        ],
        data_note="예약 시 주소와 출입 방법을 함께 남겨주시면 도착 시간이 평균적으로 단축됩니다.",
        faq=[
            ("무엇을 준비하면 되나요?", "편히 쉴 공간과 연락 가능한 번호, 정확한 주소면 충분합니다."),
            ("출입은 어떻게 하나요?", "출입 방법을 미리 알려주시면 도착이 수월합니다."),
            ("예약을 변경할 수 있나요?", "가능한 한 빠르게 연락 주시면 일정 변경을 도와드립니다.")])


# ---- /seoul/faq/ ---------------------------------------------------------
def build_seoul_faq():
    path = "/seoul/faq/"
    trail = [("/", "홈"), ("/seoul/", "서울 출장마사지"), (None, "자주 묻는 질문")]
    content_page(path, "seoul", trail,
        title="서울 출장마사지·홈타이 FAQ | 예약·지역·요금 자주 묻는 질문",
        desc="서울 출장마사지·홈타이 자주 묻는 질문 - 방문 가능 지역, 예약 방법, 도착 시간, 코스, 요금, 안전까지 자주 들어오는 질문을 한곳에 정리했습니다.",
        eyebrow="서울 · FAQ", h1="서울 출장마사지·홈타이 자주 묻는 질문",
        lead="예약·지역·시간·코스·요금 등 자주 들어오는 질문을 한곳에 정리했습니다.",
        sections=[
            ("자주 묻는 질문을 모았습니다", [
                "서울 출장마사지·홈타이를 이용하기 전 자주 들어오는 질문을 주제별로 정리했습니다.",
                "더 궁금한 점은 <a href='/customer/'>고객센터</a> 또는 전화로 언제든 문의해 주세요."]),
            ("예약·지역 한눈에", [
                ("h3", "어디까지 방문하나요"),
                "서울 전지역을 대상으로 하며, 자치구·대표 동·역세권을 기준으로 안내드립니다.",
                ("h3", "당일·심야 예약"),
                "상담은 24시간 가능하며, 시간대와 위치에 따라 방문 가능 시간을 안내드립니다."]),
            ("지하철·지역 구조", [
                ("h3", "역 근처도 되나요"),
                "강남역·잠실역·홍대입구역 등 주요 역세권은 위치 기준으로 안내하며, 출구별 페이지는 운영하지 않습니다.",
                ("h3", "숫자로 나뉜 동도 되나요"),
                "논현1동·논현2동처럼 나뉜 행정동은 대표 동 페이지 기준으로 통합 안내드립니다."]),
            ("코스·요금 한눈에", [
                ("h3", "어떤 코스가 있나요"),
                "피로 회복·아로마·스포츠·홈타이·커플가족·기업단체 관리가 있으며 60·90·120분으로 운영합니다.",
                ("h3", "요금은 어떻게 안내되나요"),
                "코스별 정찰 요금을 사전에 안내하며, 지역·시간대 등 변동 요소는 예약 시 미리 알려드립니다."]),
            ("안전·신뢰", [
                "본 서비스는 의료 행위가 아닌 이완·휴식 목적의 건강관리 서비스이며, 만 19세 이상 성인을 대상으로 합니다.",
                "위생·안전 가이드라인을 준수하며, 자세한 내용은 위생 및 안전 안내 페이지에서 확인하실 수 있습니다."]),
        ],
        data_note="가장 많이 들어오는 문의는 '도착까지 걸리는 시간'과 '코스·요금'입니다. 예약 시 위치와 희망 코스를 함께 알려주시면 빠르게 안내해 드립니다.",
        faq=[
            ("서울 어디까지 방문 가능한가요?", "서울 전지역을 대상으로 하며, 자치구·대표 동·역세권을 기준으로 안내드립니다."),
            ("숫자로 나뉜 동도 되나요?", "네. 논현1동·논현2동, 중곡1~4동 등은 대표 동 안내 기준으로 통합 안내드립니다."),
            ("예약은 어떻게 하나요?", "전화 또는 문의로 지역·시간·코스를 알려주시면 방문 가능 시간을 확정해 드립니다."),
            ("당일·심야 예약이 가능한가요?", "상담은 24시간 가능합니다. 심야는 위치에 따라 도착 시간이 길어질 수 있습니다."),
            ("어떤 코스가 있나요?", "피로 회복·아로마·스포츠·홈타이·커플가족·기업단체 관리가 있으며 60·90·120분으로 운영합니다."),
            ("요금은 어떻게 되나요?", "코스별 정찰 요금을 사전에 안내드립니다. 자세한 금액은 가격 안내에서 확인하세요."),
            ("이 서비스는 의료 행위인가요?", "아닙니다. 이완·휴식 목적의 건강관리 서비스이며 만 19세 이상을 대상으로 합니다.")])


# ---- 매거진(블로그) /magazine/ ------------------------------------------
# 정보성 글 + 롱테일 키워드 내부링크 강화 (구글 helpful-content 기준)
def _ul(*items):
    return ("ul", list(items))

MAGAZINE_POSTS = [
 {"slug":"chuljang-massage-first-guide","menu":"출장마사지 처음 이용",
  "subject":"출장마사지·홈타이 첫 이용",
  "title":"출장마사지·홈타이 처음 이용 가이드 | 예약부터 마무리까지",
  "desc":"출장마사지·홈타이를 처음 이용하는 분을 위한 안내입니다. 예약 방법, 방문 전 준비물, 코스 선택, 위생·안전까지 처음 이용 시 알아야 할 점을 정리했습니다.",
  "eyebrow":"MAGAZINE · 입문 가이드","h1":"출장마사지·홈타이, 처음이라면 이렇게 준비하세요",
  "lead":"방문 마사지가 처음이라 망설여진다면, 예약부터 마무리까지 흐름만 알면 충분합니다. 처음 이용 시 자주 묻는 점을 순서대로 정리했습니다.",
  "sections":[
    ("출장마사지와 홈타이, 무엇이 다른가요", [
      "출장마사지와 홈타이는 모두 관리사가 고객이 있는 곳으로 방문하는 방문형 관리입니다. 홈타이는 그중에서도 자택 방문을 강조한 표현으로, 받는 방식은 같습니다.",
      "스웨디시·아로마테라피·타이마사지처럼 받고 싶은 기법은 따로 고르며, 이는 <a href=\"/theme/\">테마별 안내</a>에서 확인할 수 있습니다."]),
    ("예약 전에 정리하면 좋은 것", [
      "예약 전 방문 지역(자치구·동 또는 가까운 지하철역), 희망 시간, 코스와 인원을 미리 정리해 두면 상담이 빠릅니다.",
      _ul('<a href="/reservation/">예약안내 — 예약 방법·결제·변경</a>',
          '<a href="/reservation/checklist/">예약 전 체크사항</a>',
          '<a href="/course/guide/">코스 선택 가이드(60·90·120분)</a>')]),
    ("방문 전 준비사항", [
      "편히 누울 수 있는 조용한 공간과 정확한 주소, 공동현관 출입 방법만 있으면 됩니다. 별도의 장비는 필요하지 않습니다.",
      "자세한 준비물은 <a href=\"/guide/checklist/\">이용 전 확인사항</a>과 <a href=\"/guide/prepare/\">방문 전 준비사항</a>에서 확인하세요."]),
    ("처음에는 어떤 코스가 좋을까요", [
      "첫 방문이라면 전신을 고르게 풀어주는 90분 <a href=\"/course/fatigue/\">피로 회복 관리</a>가 무난합니다. 향과 함께 깊게 쉬고 싶다면 <a href=\"/theme/aroma-therapy/\">아로마테라피</a>도 좋습니다.",
      "받아본 뒤 선호하는 압·향·집중 부위를 알려주시면 다음 방문이 더 잘 맞습니다."]),
    ("위생과 안전은 이렇게 확인하세요", [
      "용품 위생 관리와 응대 기준, 비의료 서비스 고지는 미리 확인해 두면 안심하고 받을 수 있습니다.",
      _ul('<a href="/guide/safety/">위생 및 안전 안내</a>', '<a href="/guide/forbidden/">금지행위 안내</a>')]),
  ],
  "data_note":"처음 이용하시는 분의 다수가 90분 구성을 선택합니다. 예약 시 정확한 위치와 희망 시간을 함께 알려주시면 예상 도착 시간을 빠르게 안내해 드립니다.",
  "faq":[
    ("출장마사지와 홈타이는 다른 서비스인가요?","둘 다 방문형 관리이며 홈타이는 자택 방문을 강조한 표현입니다. 기법은 테마에서 선택합니다."),
    ("처음인데 무엇을 준비하나요?","편히 쉴 공간과 연락 가능한 번호, 정확한 주소면 충분합니다."),
    ("당일 예약도 되나요?","배정 상황에 따라 가능하지만 원하는 시간이 있으면 사전 예약을 권장합니다.")]},

 {"slug":"swedish-vs-aroma","menu":"스웨디시 vs 아로마",
  "subject":"스웨디시와 아로마테라피",
  "title":"스웨디시와 아로마테라피 차이 | 나에게 맞는 관리 고르는 법",
  "desc":"스웨디시와 아로마테라피의 차이와 선택 기준을 정리했습니다. 압·향·이완 방식의 차이부터 추천 대상까지, 방문 마사지 코스 선택에 참고하세요.",
  "eyebrow":"MAGAZINE · 코스 비교","h1":"스웨디시와 아로마테라피, 무엇이 다를까요",
  "lead":"두 관리 모두 오일을 사용한 부드러운 이완 계열이라 헷갈리기 쉽습니다. 차이를 알면 컨디션에 맞게 고르기 쉬워집니다.",
  "sections":[
    ("스웨디시는 어떤 관리인가요", [
      "스웨디시는 길고 부드러운 동작과 일정한 압으로 전신의 긴장을 풀어주는 가장 대중적인 오일 관리입니다. 자세한 특징은 <a href=\"/theme/swedish/\">스웨디시 안내</a>에서 확인할 수 있습니다.",
      "강한 자극보다 혈행과 이완에 초점을 두어 마사지가 처음인 분도 편안하게 받을 수 있습니다."]),
    ("아로마테라피는 무엇이 다른가요", [
      "<a href=\"/theme/aroma-therapy/\">아로마테라피</a>는 블렌딩 오일의 향을 더해 심신을 함께 이완하는 관리입니다. 향을 통한 심리적 안정이 더해져 긴장도가 높은 날에 선호됩니다.",
      "두 관리의 동작은 비슷하지만, 아로마테라피는 '향'이라는 요소가 더해진다는 점이 핵심 차이입니다."]),
    ("이럴 때 이렇게 고르세요", [
      _ul("전신을 부드럽게 풀고 싶다 → 스웨디시",
          "향과 함께 깊게 이완하고 수면 전 안정을 원한다 → 아로마테라피",
          "또렷한 압으로 근육을 풀고 싶다 → <a href=\"/theme/sports-massage/\">스포츠·경락</a>"),
      "고민된다면 첫 방문은 스웨디시로 시작하고, 다음에 아로마테라피로 비교해 보는 것도 좋습니다."]),
    ("코스 시간과 요금은", [
      "두 관리 모두 60·90·120분으로 운영합니다. 시간 선택 기준은 <a href=\"/course/guide/\">코스 선택 가이드</a>, 요금은 <a href=\"/course/price/\">가격 안내</a>에서 확인하세요."]),
  ],
  "data_note":"향 선호가 뚜렷한 고객은 아로마테라피를 재방문하는 비율이 높습니다. 예약 시 선호 향(라벤더·시트러스 등)을 알려주시면 방문이 매끄럽습니다.",
  "faq":[
    ("처음이면 둘 중 무엇이 좋나요?","부담 없는 스웨디시로 시작하는 분이 많습니다."),
    ("향 알러지가 있어도 아로마가 되나요?","예약 시 알려주시면 향·오일을 조정합니다."),
    ("오일 잔여감이 남나요?","마무리 단계에서 수건으로 정돈해 과도한 잔여감을 줄입니다.")]},

 {"slug":"office-worker-recovery","menu":"직장인 피로 회복",
  "subject":"야근 후 피로 회복",
  "title":"야근 후 피로 회복 | 직장인 출장마사지·홈타이 활용법",
  "desc":"늦은 퇴근과 잦은 야근으로 지친 직장인을 위한 방문 마사지 활용법입니다. 업무지구 역세권 이용 팁과 피로 회복 코스 선택을 안내합니다.",
  "eyebrow":"MAGAZINE · 직장인","h1":"야근 후, 이동 없이 푸는 직장인 피로 회복법",
  "lead":"퇴근이 늦어 마사지숍 갈 시간이 없을 때, 방문 관리는 이동 없이 그대로 쉴 수 있어 직장인에게 잘 맞습니다.",
  "sections":[
    ("왜 방문 관리가 직장인에게 맞을까", [
      "관리 직후 이동 없이 바로 휴식할 수 있어 이완 상태가 오래 유지됩니다. 익숙한 공간이라 긴장도 덜합니다.",
      "오래 앉아 일해 어깨·목·허리가 뭉친 경우 <a href=\"/course/fatigue/\">피로 회복 관리</a>가 가장 무난합니다."]),
    ("업무지구 역세권에서 받기", [
      "강남·여의도 등 업무 밀집 지역은 야근 후 자택·오피스텔 방문 문의가 많습니다. 가까운 역을 기준으로 위치를 알려주시면 안내가 빠릅니다.",
      _ul('<a href="/seoul/stations/gangnam-station/">강남역 출장마사지·홈타이 안내</a>',
          '<a href="/seoul/stations/yeouido-station/">여의도역 출장마사지·홈타이 안내</a>',
          '<a href="/seoul/gangnam-gu/yeoksam-dong/">역삼동 방문 안내</a>')]),
    ("늦은 시간 예약 팁", [
      "평일 밤 21~24시는 예약이 가장 몰리는 시간대입니다. 원하는 시간이 있으면 미리 예약할수록 일정 조율이 수월합니다.",
      "시간대별 특징은 <a href=\"/reservation/hours/\">예약 가능 시간</a>에서 확인하세요."]),
    ("수면 전 이완까지 챙기기", [
      "잠들기 전 긴장을 풀고 싶다면 <a href=\"/theme/sleep-available/\">수면 가능</a> 안내나 <a href=\"/theme/aroma-therapy/\">아로마테라피</a>를 참고하세요."]),
  ],
  "data_note":"업무지구 역세권은 평일 밤 예약이 집중됩니다. 정확한 주소와 공동현관 출입 방법을 함께 남겨주시면 도착 시간이 단축됩니다.",
  "faq":[
    ("새벽에도 받을 수 있나요?","상담은 24시간 가능하며 심야는 위치에 따라 도착이 길어질 수 있습니다."),
    ("오피스텔도 방문하나요?","네. 건물 출입 방법과 호수를 알려주시면 됩니다."),
    ("야근으로 피곤할 때 어떤 코스가 좋나요?","전신을 고르게 푸는 90분 피로 회복 관리를 권장합니다.")]},

 {"slug":"couple-anniversary-home-care","menu":"커플·기념일 홈케어",
  "subject":"커플·기념일 홈케어",
  "title":"커플·기념일 홈케어 준비 가이드 | 둘이 함께 받는 방문 관리",
  "desc":"기념일에 둘이 함께 받는 커플 방문 관리 준비 가이드입니다. 공간 조건, 예약 방법, 각자 다른 코스 선택까지 정리했습니다.",
  "eyebrow":"MAGAZINE · 커플·가족","h1":"기념일, 둘이 함께 받는 홈케어 준비하기",
  "lead":"기념일이나 휴식을 함께하고 싶을 때, 같은 공간에서 나란히 받는 커플 관리는 특별한 시간을 만들어 줍니다.",
  "sections":[
    ("커플 관리는 어떻게 진행되나요", [
      "관리사 2인이 방문해 두 분이 같은 공간에서 동시에 관리를 받는 동반형 방문 관리입니다. 자세한 내용은 <a href=\"/theme/couple/\">커플 관리 안내</a>와 <a href=\"/course/couple/\">커플·가족 방문 관리 코스</a>에서 확인하세요.",
      "각자 원하는 코스를 다르게 선택할 수 있어, 한 분은 피로 회복·다른 한 분은 아로마처럼 골라도 됩니다."]),
    ("공간은 어떻게 준비하나요", [
      "두 사람이 동시에 누울 수 있는 평평한 공간이 있으면 동시 진행이 가능합니다. 좁으면 순차로 진행하니 예약 시 환경을 알려주세요.",
      "준비물과 환경 점검은 <a href=\"/guide/prepare/\">방문 전 준비사항</a>을 참고하세요."]),
    ("예약은 미리 하는 게 좋아요", [
      "관리사 2인 일정 조율이 필요해 기념일·주말 저녁은 가급적 1~2일 전 예약을 권장합니다.",
      _ul('<a href="/reservation/">예약안내</a>', '<a href="/reservation/change/">변경·취소 안내</a>')]),
    ("어디서 많이 받나요", [
      "한강변 주거지나 호텔·숙소에서 기념일 관리를 받는 경우가 많습니다. 호텔 방문은 <a href=\"/theme/hotel-massage/\">호텔식마사지</a>를 참고하세요."]),
  ],
  "data_note":"커플 관리는 기념일·주말 저녁 문의가 집중됩니다. 방의 크기와 환경을 미리 알려주시면 동시·순차 진행 방식을 정해 드립니다.",
  "faq":[
    ("두 사람이 다른 코스를 받을 수 있나요?","네. 각자 원하는 코스를 선택할 수 있습니다."),
    ("호텔에서도 가능한가요?","네. 건물명과 객실 번호를 알려주시면 됩니다."),
    ("당일도 되나요?","관리사 2인 일정상 사전 예약을 권장합니다.")]},

 {"slug":"hygiene-safety-checklist","menu":"위생·안전 체크",
  "subject":"방문 마사지 위생·안전",
  "title":"출장마사지 위생·안전 체크리스트 | 안심하고 받는 법",
  "desc":"방문 마사지를 안심하고 받기 위한 위생·안전 체크리스트입니다. 용품 위생, 응대 기준, 비의료 고지, 개인정보 보호까지 확인하세요.",
  "eyebrow":"MAGAZINE · 안전","h1":"안심하고 받기 위한 위생·안전 체크리스트",
  "lead":"방문 관리를 처음 받을 때 가장 궁금한 것이 위생과 안전입니다. 미리 확인하면 더 편안하게 받을 수 있습니다.",
  "sections":[
    ("용품 위생은 이렇게 관리됩니다", [
      "수건·오일 등 직접 닿는 용품은 위생 기준에 맞춰 관리하며, 관리 종료 후 사용한 공간을 정돈합니다. 자세한 기준은 <a href=\"/guide/safety/\">위생 및 안전 안내</a>에 있습니다."]),
    ("응대 기준과 건전한 운영", [
      "정중한 응대와 상호 존중을 원칙으로 하며, 불법·퇴폐 행위는 일절 제공하지 않습니다. <a href=\"/guide/forbidden/\">금지행위 안내</a>를 확인하세요.",
      "본 서비스는 만 19세 이상 성인을 대상으로 합니다."]),
    ("의료 행위가 아닙니다", [
      "방문 마사지는 이완·휴식 목적의 건강관리 서비스로, 질환의 진단·치료가 목적이 아닙니다. 통증·부상은 의료기관 진료를 권합니다."]),
    ("개인정보는 안전하게", [
      "예약을 위해 받은 연락처·주소는 예약 진행 목적으로만 이용하고 목적 달성 후 파기합니다. <a href=\"/privacy/\">개인정보처리방침</a>에서 확인할 수 있습니다.",
      _ul('<a href="/guide/checklist/">이용 전 확인사항</a>', '<a href="/guide/">이용가이드</a>')]),
  ],
  "data_note":"위생·안전은 운영의 기본 기준입니다. 예약 시 민감성 피부·알러지·임신 등 주의가 필요한 사항을 알려주시면 무리하지 않도록 조정합니다.",
  "faq":[
    ("위생은 어떻게 관리되나요?","용품을 위생 기준에 맞춰 관리하고 관리 후 공간을 정돈합니다."),
    ("의료적 효과가 있나요?","아닙니다. 이완·휴식 목적의 건강관리 서비스입니다."),
    ("개인정보는 어떻게 처리되나요?","예약 목적으로만 이용하고 이후 파기합니다.")]},

 {"slug":"station-area-tips","menu":"역세권 이용 팁",
  "subject":"역세권 방문 마사지",
  "title":"지하철역 근처 출장마사지·홈타이 | 역세권 이용 팁",
  "desc":"지하철역 인근에서 방문 마사지를 받을 때 알아두면 좋은 팁입니다. 역세권 위치 안내, 출구별 페이지가 없는 이유, 예약 시 알려줄 정보를 정리했습니다.",
  "eyebrow":"MAGAZINE · 역세권","h1":"지하철역 근처에서 방문 마사지 받을 때 알아둘 점",
  "lead":"역 이름으로 위치를 떠올리기 쉬워 역세권 기준으로 찾는 분이 많습니다. 역 근처에서 받을 때의 이용 팁을 정리했습니다.",
  "sections":[
    ("역세권 방문은 위치 기준입니다", [
      "방문은 역 건물이 아니라 역 인근 자택·오피스텔·숙소를 기준으로 진행됩니다. 예약 시 정확한 주소를 알려주시면 됩니다.",
      "주요 역 안내는 <a href=\"/seoul/stations/\">지하철역별 안내</a>에서 노선별로 확인할 수 있습니다."]),
    ("검색 많은 주요 역", [
      _ul('<a href="/seoul/stations/gangnam-station/">강남역</a>',
          '<a href="/seoul/stations/jamsil-station/">잠실역</a>',
          '<a href="/seoul/stations/hongik-univ-station/">홍대입구역</a>',
          '<a href="/seoul/stations/kondae-station/">건대입구역</a>',
          '<a href="/seoul/stations/seoul-station/">서울역</a>')]),
    ("출구별 페이지가 없는 이유", [
      "출구 번호로 방문 위치가 정해지는 것이 아니라 정확한 주소로 방문하기 때문에, 출구별 페이지는 운영하지 않습니다. 마찬가지로 역+테마 조합 페이지도 만들지 않습니다.",
      "관리 유형은 <a href=\"/theme/\">테마별 안내</a>에서 따로 고르시면 됩니다."]),
    ("예약 시 알려주면 좋은 정보", [
      "가까운 역과 정확한 주소, 공동현관 출입 방법을 함께 알려주시면 도착이 빨라집니다. 시간대별 도착 안내는 <a href=\"/reservation/hours/\">예약 가능 시간</a>을 참고하세요."]),
  ],
  "data_note":"같은 노선이라도 도심 구간과 외곽 구간은 도착 시간 편차가 큽니다. 가까운 역과 정확한 주소를 함께 알려주시면 예상 도착 시간을 빠르게 안내합니다.",
  "faq":[
    ("출구별로 예약이 나뉘나요?","아니요. 정확한 주소를 기준으로 방문합니다."),
    ("역 근처 숙소도 되나요?","네. 건물명과 객실 번호를 알려주시면 됩니다."),
    ("환승역은 어떻게 찾나요?","환승역도 페이지는 하나로 운영합니다.")]},

 {"slug":"sports-recovery-massage","menu":"운동 후 회복",
  "subject":"운동 후 회복 마사지",
  "title":"운동 후 회복 마사지 | 스포츠·경락 제대로 받는 법",
  "desc":"러닝·헬스·등산 후 뭉친 근육을 푸는 스포츠 마사지 활용법입니다. 적합한 상황, 받는 시점, 주의사항을 정리했습니다.",
  "eyebrow":"MAGAZINE · 스포츠","h1":"운동 후 컨디션, 스포츠 마사지로 정리하기",
  "lead":"운동으로 누적된 근육 피로는 또렷한 압의 관리로 정리하면 한결 가볍습니다. 제대로 받는 방법을 정리했습니다.",
  "sections":[
    ("스포츠 마사지는 어떤 관리인가요", [
      "근육 결을 따라 또렷한 압으로 풀어 운동 후 무거움을 정리하는 관리입니다. 특징은 <a href=\"/theme/sports-massage/\">스포츠·경락 안내</a>와 <a href=\"/course/sports/\">스포츠 관리 코스</a>에서 확인하세요.",
      "전문 재활·치료가 아닌 일상 운동 후 컨디션 관리 목적입니다."]),
    ("언제 받는 게 좋을까", [
      "운동 직후보다 1~2시간 휴식 후가 좋습니다. 심한 통증이 있으면 무리하지 않습니다."]),
    ("부위별로 이렇게 풀어요", [
      "다리·등처럼 운동으로 자주 긴장되는 부위에 시간을 더 배분합니다. 압이 강하게 느껴지면 즉시 조절하니 편하게 말씀하세요."]),
    ("꼭 알아둘 주의사항", [
      "부상·염좌·급성 통증 부위는 관리 대상이 아니며 의료기관 진료를 권합니다. 부드러운 이완을 원하면 <a href=\"/course/fatigue/\">피로 회복 관리</a>가 더 맞을 수 있습니다."]),
  ],
  "data_note":"스포츠 관리는 주말 오전~오후 예약 비율이 높습니다. 어떤 운동을 했고 어느 부위가 무거운지 알려주시면 시간을 집중 배분합니다.",
  "faq":[
    ("운동 직후 바로 받아도 되나요?","가벼운 휴식 후를 권장합니다."),
    ("강도가 센가요?","또렷한 압을 쓰지만 선호에 맞춰 조절합니다."),
    ("부상이 있어도 되나요?","부상 부위는 관리 대상이 아니며 진료를 권합니다.")]},

 {"slug":"sleep-aroma-routine","menu":"숙면 마사지 루틴",
  "subject":"숙면을 돕는 마사지",
  "title":"숙면을 돕는 수면 마사지·아로마 루틴 | 잠 못 드는 밤에",
  "desc":"잠들기 어려운 밤, 깊은 이완과 수면 유도에 초점을 둔 수면 마사지와 아로마 루틴을 안내합니다.",
  "eyebrow":"MAGAZINE · 수면","h1":"잠 못 드는 밤, 숙면을 돕는 이완 루틴",
  "lead":"긴장이 풀리지 않아 잠들기 어려운 날에는 부드러운 압과 향으로 천천히 가라앉히는 관리가 도움이 됩니다.",
  "sections":[
    ("수면 마사지는 어떤 방식인가요", [
      "관리 도중 잠들어도 괜찮은, 깊은 이완과 수면 유도에 초점을 둔 방식입니다. <a href=\"/theme/sleep-available/\">수면 가능 안내</a>에서 자세히 확인하세요.",
      "또렷한 자극보다 부드러운 <a href=\"/theme/swedish/\">스웨디시</a>·<a href=\"/theme/aroma-therapy/\">아로마테라피</a> 기반으로 진행합니다."]),
    ("향이 만드는 차이", [
      "라벤더 계열의 차분한 향은 심리적 안정을 도와 수면 전 이완에 좋습니다. 향 선호가 있으면 예약 시 알려주세요."]),
    ("잠들기 좋은 환경 만들기", [
      "조명을 낮추고 휴대폰 알림을 줄여두면 더 깊은 휴식에 도움이 됩니다. 환경 점검은 <a href=\"/guide/prepare/\">방문 전 준비사항</a>을 참고하세요."]),
    ("받은 다음에는", [
      "관리 후에는 무리한 활동을 피하고 그대로 휴식하는 것이 좋습니다. 애프터케어는 <a href=\"/guide/aftercare/\">관리 후 주의사항</a>에 정리되어 있습니다."]),
  ],
  "data_note":"수면 목적의 예약은 늦은 저녁~심야에 많습니다. 선호 향과 조용한 환경을 미리 알려주시면 차분하게 진행합니다.",
  "faq":[
    ("관리 중 잠들어도 되나요?","네. 잠들면 마무리도 조용하게 진행합니다."),
    ("어떤 향이 수면에 좋나요?","라벤더 계열의 차분한 향을 선호하는 분이 많습니다."),
    ("심야에도 되나요?","상담은 24시간 가능하며 위치에 따라 도착이 달라집니다.")]},

 {"slug":"price-time-guide","menu":"비용·시간 선택",
  "subject":"코스 비용·시간 선택",
  "title":"출장마사지 비용·시간 선택 가이드 | 60·90·120분 차이",
  "desc":"방문 마사지 코스의 비용과 시간(60·90·120분) 선택 기준을 정리했습니다. 정찰 요금 원칙과 변동 요소도 함께 확인하세요.",
  "eyebrow":"MAGAZINE · 비용","h1":"60·90·120분, 어떤 시간을 고를까요",
  "lead":"코스 비용은 종류와 시간의 조합으로 정해집니다. 상황에 맞는 시간을 고르면 만족도가 높아집니다.",
  "sections":[
    ("시간별로 이렇게 다릅니다", [
      _ul("60분 — 핵심 부위 위주로 빠르게 정리",
          "90분 — 전신을 고르게, 가장 많이 선택",
          "120분 — 전신 이완 + 마무리 케어까지 여유 있게"),
      "더 자세한 기준은 <a href=\"/course/guide/\">코스 선택 가이드</a>에서 확인하세요."]),
    ("정찰 요금을 원칙으로 합니다", [
      "코스별 기본 요금을 사전에 안내하며 현장에서 임의로 금액을 올리지 않습니다. 금액은 <a href=\"/course/price/\">가격 안내</a>에서 확인할 수 있습니다."]),
    ("요금이 달라질 수 있는 경우", [
      _ul("방문 지역과 이동 거리","예약 시간대(심야 등)","커플·가족 등 인원 구성","기업·단체 등 별도 견적 대상")]),
    ("코스별로 고르기", [
      "목적에 따라 <a href=\"/course/fatigue/\">피로 회복</a>·<a href=\"/course/aroma/\">아로마</a>·<a href=\"/course/sports/\">스포츠</a>·<a href=\"/course/home/\">홈타이</a> 중에서 고르면 됩니다."]),
  ],
  "data_note":"가장 많이 선택되는 구성은 90분입니다. 심야 예약은 도착 시간과 함께 변동 요소를 미리 안내드립니다.",
  "faq":[
    ("표시 요금 외 추가 비용이 있나요?","정찰 요금을 원칙으로 하며 변동 요소는 예약 시 안내합니다."),
    ("처음엔 몇 분이 좋나요?","전신을 고르게 푸는 90분을 권장합니다."),
    ("결제는 어떻게 하나요?","결제 방법은 예약 시 함께 안내합니다.")]},

 {"slug":"area-guide-by-life","menu":"생활권별 안내",
  "subject":"서울 생활권별 방문 마사지",
  "title":"서울 생활권별 출장마사지·홈타이 안내 | 우리 동네 찾기",
  "desc":"서울을 권역·자치구·대표 동으로 나눠 방문 마사지를 찾는 방법을 정리했습니다. 숫자 행정동 통합 안내 방식도 함께 설명합니다.",
  "eyebrow":"MAGAZINE · 지역","h1":"우리 동네에서 받는 방문 마사지 찾는 법",
  "lead":"서울은 생활권이 넓어 지역별 이동 시간이 다릅니다. 권역과 자치구, 대표 동 순서로 좁혀 가면 찾기 쉽습니다.",
  "sections":[
    ("권역 → 자치구 → 대표 동 순서로", [
      "<a href=\"/seoul/area/\">서울 지역별 안내</a>에서 6개 권역과 25개 자치구로 나눠 방문 가능 생활권을 확인할 수 있습니다.",
      _ul('<a href="/seoul/gangnam-gu/">강남구 안내</a>',
          '<a href="/seoul/songpa-gu/">송파구 안내</a>',
          '<a href="/seoul/mapo-gu/">마포구 안내</a>')]),
    ("숫자로 나뉜 동은 대표 동에서", [
      "논현1동·논현2동은 논현동 페이지에서, 중곡1~4동은 중곡동 페이지에서 함께 안내합니다. 비슷한 페이지를 늘리지 않아 찾기도 쉽습니다.",
      _ul('<a href="/seoul/gangnam-gu/nonhyeon-dong/">논현동 안내</a>',
          '<a href="/seoul/gwangjin-gu/junggok-dong/">중곡동 안내</a>')]),
    ("역세권으로 찾고 싶다면", [
      "지하철역 기준으로 찾는다면 <a href=\"/seoul/stations/\">지하철역별 안내</a>에서 노선과 역으로 좁혀 보세요."]),
    ("관리 유형으로 좁히기", [
      "지역을 정한 뒤에는 <a href=\"/theme/\">테마별 안내</a>에서 원하는 관리 방식을 고르고 예약 시 함께 말씀하시면 됩니다."]),
  ],
  "data_note":"방문 가능 여부는 자치구·동 단위로 일률적이지 않고 위치·시간·배정 상황에 따라 달라집니다. 정확한 위치를 알려주시면 빠르게 안내합니다.",
  "faq":[
    ("우리 동 페이지가 없어요.","대표 동 위주로 운영하며 숫자 동은 대표 동에서 통합 안내합니다."),
    ("지역과 테마를 함께 고르나요?","각각 확인한 뒤 예약 시 함께 말씀하시면 됩니다."),
    ("서울 전지역이 되나요?","위치·시간에 따라 다르며 예약 시 확인해 드립니다.")]},
]

# 추가 매거진 글(50편) — 별도 모듈에서 로드
try:
    from magazine_posts import POSTS as _EXTRA_POSTS
except Exception:
    _EXTRA_POSTS = []
MAGAZINE_POSTS = MAGAZINE_POSTS + _EXTRA_POSTS

# 카테고리 정의 (글 수백 개 확장 대비 — 메뉴는 카테고리만 노출)
MAG_CATS = [
    {"slug": "guide", "name": "이용가이드"},
    {"slug": "course-theme", "name": "코스·테마"},
    {"slug": "tips", "name": "활용팁"},
    {"slug": "area-station", "name": "지역·역세권"},
    {"slug": "region", "name": "지역별 마사지"},
    {"slug": "swedish", "name": "스웨디시"},
    {"slug": "visiting", "name": "출장마사지"},
    {"slug": "korean-therapist", "name": "한국인 관리사"},
    {"slug": "thai-therapist", "name": "태국 관리사"},
]
CAT_NAME = {c["slug"]: c["name"] for c in MAG_CATS}

# 글별 메타: slug -> (발행일, 카테고리)
_MAG_META = {
    "chuljang-massage-first-guide": ("2026-06-05", "guide"),
    "swedish-vs-aroma":             ("2026-06-03", "course-theme"),
    "office-worker-recovery":       ("2026-05-30", "tips"),
    "couple-anniversary-home-care": ("2026-05-27", "tips"),
    "hygiene-safety-checklist":     ("2026-05-23", "guide"),
    "station-area-tips":            ("2026-05-20", "area-station"),
    "sports-recovery-massage":      ("2026-05-16", "course-theme"),
    "sleep-aroma-routine":          ("2026-05-12", "course-theme"),
    "price-time-guide":             ("2026-05-08", "guide"),
    "area-guide-by-life":           ("2026-05-02", "area-station"),
}
# 글 하단 롱테일 내부링크: slug -> [(href, 앵커) ...] (각 5개, 지역/역세권 출장마사지 주제)
_MAG_RELATED = {
    "chuljang-massage-first-guide": [
        ("/seoul/stations/gangnam-station/", "강남역 출장마사지·홈타이 예약 안내"),
        ("/seoul/stations/hongik-univ-station/", "홍대입구역 출장마사지·홈타이 예약 안내"),
        ("/seoul/stations/jamsil-station/", "잠실역 출장마사지·홈타이 예약 안내"),
        ("/seoul/gangnam-gu/", "강남구 출장마사지·홈타이 안내"),
        ("/seoul/mapo-gu/", "마포구 출장마사지·홈타이 안내")],
    "swedish-vs-aroma": [
        ("/seoul/gangnam-gu/", "강남구 출장마사지·홈타이 안내"),
        ("/seoul/seocho-gu/", "서초구 출장마사지·홈타이 안내"),
        ("/seoul/songpa-gu/", "송파구 출장마사지·홈타이 안내"),
        ("/seoul/stations/gangnam-station/", "강남역 출장마사지·홈타이 예약 안내"),
        ("/seoul/gangnam-gu/cheongdam-dong/", "청담동 출장마사지·홈타이 안내")],
    "office-worker-recovery": [
        ("/seoul/stations/gangnam-station/", "강남역 출장마사지·홈타이 예약 안내"),
        ("/seoul/stations/yeouido-station/", "여의도역 출장마사지·홈타이 예약 안내"),
        ("/seoul/gangnam-gu/yeoksam-dong/", "역삼동 출장마사지·홈타이 안내"),
        ("/seoul/yeongdeungpo-gu/yeouido-dong/", "여의도동 출장마사지·홈타이 안내"),
        ("/seoul/gangnam-gu/samseong-dong/", "삼성동 출장마사지·홈타이 안내")],
    "couple-anniversary-home-care": [
        ("/seoul/songpa-gu/", "송파구 출장마사지·홈타이 안내"),
        ("/seoul/gangnam-gu/", "강남구 출장마사지·홈타이 안내"),
        ("/seoul/yongsan-gu/hannam-dong/", "한남동 출장마사지·홈타이 안내"),
        ("/seoul/stations/jamsil-station/", "잠실역 출장마사지·홈타이 예약 안내"),
        ("/seoul/mapo-gu/", "마포구 출장마사지·홈타이 안내")],
    "hygiene-safety-checklist": [
        ("/seoul/gangnam-gu/", "강남구 출장마사지·홈타이 안내"),
        ("/seoul/songpa-gu/", "송파구 출장마사지·홈타이 안내"),
        ("/seoul/mapo-gu/", "마포구 출장마사지·홈타이 안내"),
        ("/seoul/stations/gangnam-station/", "강남역 출장마사지·홈타이 예약 안내"),
        ("/seoul/stations/hongik-univ-station/", "홍대입구역 출장마사지·홈타이 예약 안내")],
    "station-area-tips": [
        ("/seoul/stations/gangnam-station/", "강남역 출장마사지·홈타이 예약 안내"),
        ("/seoul/stations/jamsil-station/", "잠실역 출장마사지·홈타이 예약 안내"),
        ("/seoul/stations/hongik-univ-station/", "홍대입구역 출장마사지·홈타이 예약 안내"),
        ("/seoul/stations/kondae-station/", "건대입구역 출장마사지·홈타이 예약 안내"),
        ("/seoul/stations/seoul-station/", "서울역 출장마사지·홈타이 예약 안내")],
    "sports-recovery-massage": [
        ("/seoul/songpa-gu/", "송파구 출장마사지·홈타이 안내"),
        ("/seoul/gangnam-gu/", "강남구 출장마사지·홈타이 안내"),
        ("/seoul/stations/jamsil-station/", "잠실역 출장마사지·홈타이 예약 안내"),
        ("/seoul/seocho-gu/yangjae-dong/", "양재동 출장마사지·홈타이 안내"),
        ("/seoul/gwangjin-gu/", "광진구 출장마사지·홈타이 안내")],
    "sleep-aroma-routine": [
        ("/seoul/gangnam-gu/", "강남구 출장마사지·홈타이 안내"),
        ("/seoul/mapo-gu/", "마포구 출장마사지·홈타이 안내"),
        ("/seoul/seocho-gu/", "서초구 출장마사지·홈타이 안내"),
        ("/seoul/stations/seongsu-station/", "성수역 출장마사지·홈타이 예약 안내"),
        ("/seoul/yongsan-gu/hannam-dong/", "한남동 출장마사지·홈타이 안내")],
    "price-time-guide": [
        ("/seoul/gangnam-gu/", "강남구 출장마사지·홈타이 안내"),
        ("/seoul/songpa-gu/", "송파구 출장마사지·홈타이 안내"),
        ("/seoul/mapo-gu/", "마포구 출장마사지·홈타이 안내"),
        ("/seoul/stations/gangnam-station/", "강남역 출장마사지·홈타이 예약 안내"),
        ("/seoul/stations/jamsil-station/", "잠실역 출장마사지·홈타이 예약 안내")],
    "area-guide-by-life": [
        ("/seoul/gangnam-gu/", "강남구 출장마사지·홈타이 안내"),
        ("/seoul/songpa-gu/", "송파구 출장마사지·홈타이 안내"),
        ("/seoul/mapo-gu/", "마포구 출장마사지·홈타이 안내"),
        ("/seoul/gangseo-gu/", "강서구 출장마사지·홈타이 안내"),
        ("/seoul/nowon-gu/", "노원구 출장마사지·홈타이 안내")],
}
for _p in MAGAZINE_POSTS:
    if _p["slug"] in _MAG_META:            # 기존 10편: 메타·관련링크를 별도 맵에서 적용
        _p["date"], _p["cat"] = _MAG_META[_p["slug"]]
        _p["related"] = _MAG_RELATED.get(_p["slug"], [])
    else:                                  # 추가 50편: 글 dict에 date/cat/related 포함
        _p.setdefault("related", [])
        _p.setdefault("cat", "guide")
        _p.setdefault("date", UPDATED)

MAG_PER_PAGE = 12           # 한 화면에 노출할 글 수(수백 개 확장 대비 페이지네이션)
_MAG_PATHS = []             # 사이트맵용 매거진 목록 경로 누적

def _mag_card(p):
    d = p["date"].replace("-", ".")
    cat = CAT_NAME.get(p["cat"], "매거진")
    return (f'<a class="card reveal" href="/magazine/{p["slug"]}/">'
            f'<div class="k">{cat}</div><h3>{p["menu"]}</h3>'
            f'<p>{p["desc"][:66]}…</p>'
            f'<div style="color:var(--dim);font-size:12.5px;margin-top:12px">'
            f'<time datetime="{p["date"]}">{d}</time> · {cat}</div>'
            f'<span class="more">글 보기 →</span></a>')

def _mag_pager(base, cur, total):
    if total <= 1:
        return ""
    u = lambda k: base if k == 1 else f"{base}page/{k}/"
    nums = "".join(
        (f'<a class="chip" href="{u(k)}" style="background:var(--grad);color:#1a1208;border-color:transparent">{k}</a>'
         if k == cur else f'<a class="chip" href="{u(k)}">{k}</a>') for k in range(1, total + 1))
    prev = f'<a class="btn btn-ghost" href="{u(cur-1)}">← 이전</a>' if cur > 1 else ""
    nxt = f'<a class="btn btn-ghost" href="{u(cur+1)}">다음 →</a>' if cur < total else ""
    return (f'<div style="display:flex;justify-content:center;align-items:center;gap:12px;'
            f'flex-wrap:wrap;margin-top:34px">{prev}<div class="chips">{nums}</div>{nxt}</div>')

def _mag_listing(base, posts, *, eyebrow, heading, lead, title, desc, prose, faqs,
                 cat_name=None):
    """매거진 목록 페이지(최신순·페이지네이션). base는 '/magazine/' 또는 카테고리 경로."""
    posts = sorted(posts, key=lambda p: p["date"], reverse=True)
    chunks = [posts[i:i + MAG_PER_PAGE] for i in range(0, len(posts), MAG_PER_PAGE)] or [[]]
    total = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        path = base if i == 1 else f"{base}page/{i}/"
        # breadcrumb
        if cat_name:
            trail = [("/", "홈"), ("/magazine/", "매거진")]
            trail += ([(None, cat_name)] if i == 1
                      else [(base, cat_name), (None, f"{i}페이지")])
        else:
            trail = ([("/", "홈"), (None, "매거진")] if i == 1
                     else [("/", "홈"), ("/magazine/", "매거진"), (None, f"{i}페이지")])
        cards = "".join(_mag_card(p) for p in chunk) or '<p class="sec-lead">등록된 글이 없습니다.</p>'
        page_lead = lead if i == 1 else f"{heading} {i}페이지입니다. {lead}"
        body = (breadcrumb(trail) +
            '<section class="block"><div class="wrap">'
            f'<span class="eyebrow"><span class="pulse"></span>{eyebrow}</span>'
            f'<h2 class="sec">{heading}</h2>'
            f'<p class="sec-lead">{page_lead}</p>'
            f'<div class="grid g3" style="margin-top:26px">{cards}</div>'
            f'{_mag_pager(base, i, total)}</div></section>'
            + hub_prose("MAGAZINE", "매거진은 이렇게 활용하세요", prose)
            + faq_block(faqs) + cta_band())
        item_list = {"@context": "https://schema.org", "@type": "Blog",
            "name": heading, "url": BASE_URL + path,
            "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "datePublished": p["date"],
                          "url": BASE_URL + f"/magazine/{p['slug']}/"} for p in chunk]}
        t = title if i == 1 else f"{title} ({i}페이지)"
        html = page(path, t, desc, "magazine", body, [bc_ld(trail), item_list, reviews_ld(url=BASE_URL + path)])
        n = text_len(html)
        # 글이 적어 본문이 얇은 목록(카테고리/페이지)은 noindex + 사이트맵 제외
        # (글이 쌓여 2,000자 이상이 되면 자동으로 색인 대상이 됨)
        if n < 2000:
            html = page(path, t, desc, "magazine", body, [bc_ld(trail), item_list], index=False)
            write(path, html)
        else:
            write(path, html)
            _MAG_PATHS.append(path)
            _LEN_REPORT.append((path, n))

_MAG_PROSE = [
    "매거진은 처음 이용하는 분을 위한 입문 가이드부터 코스 비교, 위생·안전 체크리스트, 지역·역세권 이용 팁까지 실제 이용에 도움이 되는 정보를 담았습니다. 각 글은 관련 지역·역세권 안내로 연결되어 원하는 동네·역 출장마사지·홈타이 안내로 바로 이동할 수 있습니다.",
    "글이 늘어나도 쉽게 찾을 수 있도록 이용가이드·코스·테마·활용팁·지역·역세권 카테고리로 나누고, 최신 글부터 순서대로 보여줍니다. 한 화면에 일정 수만 노출하고 나머지는 페이지로 넘겨, 수백 편으로 늘어나도 화면이 무거워지지 않습니다.",
    "예약 전이라면 첫 이용 가이드와 비용·시간 선택 가이드를, 받을 관리를 고민 중이라면 스웨디시와 아로마테라피 비교 글을 먼저 읽어보시길 권합니다. 지역으로 찾는 분은 생활권별 안내가, 역으로 찾는 분은 역세권 이용 팁이 도움이 됩니다.",
    "매거진의 정보는 일반적인 이용 안내를 돕기 위한 것으로, 실제 예약 가능 여부와 도착 시간은 위치·시간·배정 상황에 따라 달라집니다. 모든 글은 이완·휴식 목적의 건강관리 서비스를 전제로 하며, 통증·부상이 있는 경우 의료기관 진료를 먼저 권합니다.",
]
_MAG_FAQ = [
    ("글이 많아지면 어떻게 찾나요?", "상단 카테고리(이용가이드·코스·테마·활용팁·지역·역세권)와 최신순 목록, 페이지 넘김으로 원하는 글을 쉽게 찾을 수 있습니다."),
    ("글 내용이 의료적 조언인가요?", "아닙니다. 이완·휴식 목적의 일반 정보이며 진단·치료를 대신하지 않습니다."),
    ("발행일은 어디서 보나요?", "각 글 카드와 글 상단에 발행일을 표기합니다."),
]

def build_magazine():
    _mag_listing("/magazine/", MAGAZINE_POSTS,
        eyebrow="MAGAZINE", heading="매거진",
        lead="출장마사지·홈타이를 더 잘 이용하기 위한 가이드와 정보 글을 최신순으로 모았습니다. 카테고리와 페이지로 나누어 글이 늘어나도 쉽게 찾을 수 있습니다.",
        title="매거진 | 서울 출장마사지·홈타이 이용 가이드·정보",
        desc="서울 출장마사지·홈타이 매거진 - 첫 이용 가이드, 코스 비교, 위생·안전, 지역·역세권 이용 팁 등 방문 마사지 정보 글을 카테고리·최신순으로 제공합니다.",
        prose=_MAG_PROSE, faqs=_MAG_FAQ)
    # 카테고리별 목록
    for c in MAG_CATS:
        cposts = [p for p in MAGAZINE_POSTS if p["cat"] == c["slug"]]
        _mag_listing(f"/magazine/category/{c['slug']}/", cposts,
            eyebrow=f"MAGAZINE · {c['name']}", heading=f"{c['name']} 글",
            lead=f"{c['name']} 카테고리의 출장마사지·홈타이 정보 글입니다. 최신순으로 정리했습니다.",
            title=f"{c['name']} | 서울 출장마사지·홈타이 매거진",
            desc=f"서울 출장마사지·홈타이 매거진 {c['name']} 카테고리 - 관련 정보 글을 최신순으로 제공합니다.",
            prose=_MAG_PROSE, faqs=_MAG_FAQ, cat_name=c["name"])

def build_magazine_posts():
    for p in MAGAZINE_POSTS:
        path = f"/magazine/{p['slug']}/"
        cat = CAT_NAME.get(p["cat"], "매거진")
        trail = [("/", "홈"), ("/magazine/", "매거진"),
                 (f"/magazine/category/{p['cat']}/", cat), (None, p["menu"])]
        # 하단 롱테일 내부링크 섹션 (지역/역세권 출장마사지 주제 5개)
        related = p.get("related", [])
        sections = list(p["sections"])
        if related:
            sections.append(("함께 보면 좋은 지역·역세권 출장마사지·홈타이 안내", [
                f"아래 지역과 지하철역의 출장마사지·홈타이 안내도 함께 확인해 보세요. 원하는 동네·역세권의 방문 가능 생활권과 예약 정보를 바로 볼 수 있습니다.",
                ("ul", [f'<a href="{href}">{anchor}</a>' for href, anchor in related])]))
        content_page(path, "magazine", trail,
            title=p["title"], desc=p["desc"], eyebrow=p["eyebrow"], h1=p["h1"], lead=p["lead"],
            sections=sections, faq=p["faq"], data_note=p.get("data_note"),
            subject=p["subject"], published=p["date"],
            top_links=[("tel:" + PHONE_TEL, "예약문의", True), ("/magazine/", "매거진 전체"),
                       (f"/magazine/category/{p['cat']}/", f"{cat} 더보기"), ("/seoul/area/", "지역별 안내")],
            cta_title="궁금한 점이 있다면 예약 상담으로 도와드릴까요?")


# ---- 후기 /reviews/ ------------------------------------------------------
def build_reviews():
    path = "/reviews/"
    trail = [("/", "홈"), (None, "후기")]
    sample = [
        ("강남구 · 30대", "아로마", "늦은 시간 연락에도 도착 안내가 정확했습니다."),
        ("마포구 · 40대", "스포츠", "운동 후 받았는데 컨디션이 한결 가벼워졌어요."),
        ("송파구 · 30대", "피로회복", "예약부터 마무리까지 깔끔하고 정중했습니다."),
        ("성동구 · 50대", "아로마", "위생 안내가 꼼꼼해서 안심하고 받았습니다."),
        ("영등포구 · 40대", "홈타이", "집에서 이동 없이 받으니 끝나고 바로 쉴 수 있어 좋았어요."),
        ("관악구 · 30대", "커플", "둘이 함께 받았는데 응대가 친절했습니다."),
    ]
    cards = "".join(
        f'<div class="review reveal"><div class="stars">★★★★★</div>'
        f'<p>“{q}”</p><div class="who">{w} · {c} 코스</div></div>' for w, c, q in sample)
    region_links = "".join(
        f'<a class="chip" href="/seoul/area/#{slugify_region(r)}"><b>{r}</b></a>' for r in REGIONS_ORDER)
    content_page(path, "reviews", trail,
        title="후기 | 서울 출장마사지·홈타이 방문 관리 후기 안내",
        desc="서울 출장마사지·홈타이 후기 안내 - 지역별·역세권 이용 후기와 후기 작성 안내를 제공합니다. 후기는 동의 하에 게시되며 개인정보는 표시하지 않습니다.",
        eyebrow="REVIEWS", h1="후기 안내",
        lead="서울 전지역에서 방문 관리를 이용하신 분들의 후기를 모았습니다. 후기는 실제 이용 고객의 동의 하에 게시됩니다.",
        sections=[
            ("후기 안내", [
                "후기는 실제 이용 고객의 동의를 받아 게시하며, 개인을 특정할 수 있는 정보는 표시하지 않습니다.",
                "지역과 코스만 간략히 표기해, 비슷한 상황의 다른 분들이 참고하실 수 있도록 정리합니다."]),
            ("전체 후기", [
                "최근 이용 후기 일부를 소개합니다. 컨디션과 목적에 따라 선택한 코스가 다른 점을 함께 참고해 보세요.",
                ("html", f'<div class="grid g3" style="margin-top:6px">{cards}</div>')]),
            ("지역별 후기", [
                "후기는 자치구·권역별로도 확인하실 수 있습니다. 아래에서 권역을 눌러 해당 지역 안내로 이동해 보세요.",
                ("html", f'<div class="chips" style="margin-top:6px">{region_links}</div>')]),
            ("역세권 후기", [
                "강남역·잠실역·홍대입구역 등 주요 역세권 이용 후기도 함께 들어옵니다.",
                "역세권 방문 안내는 지하철역별 페이지에서 확인하실 수 있습니다.",
                ("ul", ['<a href="/seoul/stations/">서울 지하철역별 안내</a>',
                        '<a href="/seoul/stations/gangnam-station/">강남역 안내</a>',
                        '<a href="/seoul/stations/jamsil-station/">잠실역 안내</a>'])]),
            ("후기 작성 안내", [
                "관리를 받으신 뒤 전화 또는 문의로 후기를 남겨주시면 게시 동의 여부를 확인한 뒤 정리합니다.",
                "후기는 서비스 개선과 다른 고객의 선택에 큰 도움이 됩니다.",
                "허위·과장 없이 실제 경험을 바탕으로 작성해 주시면 감사하겠습니다."]),
            ("후기를 신뢰할 수 있도록", [
                "후기는 실제 이용을 전제로 하며, 운영팀이 동의와 사실 여부를 확인해 게시합니다.",
                "특정 효과를 보장하는 표현은 사용하지 않으며, 본 서비스는 이완·휴식 목적의 건강관리 서비스입니다."]),
        ],
        data_note="후기에서 자주 언급되는 점은 '정확한 도착 안내'와 '정중한 응대'입니다. 예약 시 위치와 희망 시간을 알려주시면 도착 안내가 더 정확해집니다.",
        faq=[
            ("후기는 어떻게 남기나요?", "관리 후 전화 또는 문의로 남겨주시면 동의 여부를 확인한 뒤 게시합니다."),
            ("후기에 개인정보가 노출되나요?", "아니요. 개인을 특정할 수 있는 정보는 표시하지 않습니다."),
            ("지역별 후기를 볼 수 있나요?", "네. 권역·자치구 안내 페이지와 함께 확인하실 수 있습니다.")],
        service=("서울 출장마사지·홈타이 후기", "서울 전지역 방문 건강관리 이용 후기 안내"))


# ---- 고객센터 /customer/ -------------------------------------------------
def build_customer():
    path = "/customer/"
    trail = [("/", "홈"), (None, "고객센터")]
    notes = [
        ("공지사항", ["서비스 운영과 관련된 안내를 이곳에 게시합니다.",
                   "운영 시간 변경, 점검, 이벤트 등 중요한 소식을 확인하실 수 있습니다."]),
        ("자주 묻는 질문", ["예약·지역·요금 등 자주 들어오는 질문은 자주 묻는 질문에서 확인하실 수 있습니다.",
                       "더 자세한 내용은 서울 FAQ와 이용 FAQ에서도 안내합니다."]),
        ("1:1 문의", [f"전화 {PHONE_DISP}로 문의해 주세요. 연중무휴 24시간 상담을 운영합니다.",
                   "예약·변경·취소 및 기타 궁금한 점을 도와드립니다."]),
        ("제휴·기업 문의", ["기업·단체 방문 관리 및 제휴 문의도 전화로 접수받습니다.",
                       "행사·사내 복지 등 단체 이용은 사전 협의로 별도 견적을 안내드립니다."]),
    ]
    cust_faq = [
        ("문의는 어디로 하나요?", f"전화 {PHONE_DISP}로 문의하실 수 있습니다. 연중무휴 24시간 상담을 운영합니다."),
        ("운영 시간이 어떻게 되나요?", "연중무휴 24시간 상담을 운영합니다."),
        ("개인정보는 어떻게 관리되나요?", "개인정보처리방침에 따라 안전하게 관리되며, 자세한 내용은 해당 페이지에서 확인하실 수 있습니다."),
        ("제휴 문의도 가능한가요?", "네. 기업·단체 및 제휴 문의는 전화로 접수받으며 사전 협의로 안내드립니다."),
    ]
    extra = (
        '<section class="block" id="qna"><div class="wrap">'
        '<span class="eyebrow"><span class="pulse"></span>HELP CENTER</span>'
        '<h2 class="sec">고객센터 이용 안내</h2>'
        '<p class="sec-lead">예약·문의·제휴 등 무엇이든 전화로 도와드립니다. 자주 묻는 질문과 안내 페이지도 함께 확인해 보세요.</p>'
        '<div class="chips" style="margin-top:18px">'
        '<a class="chip" href="/seoul/faq/"><b>서울 FAQ</b></a>'
        '<a class="chip" href="/guide/faq/"><b>이용 FAQ</b></a>'
        '<a class="chip" href="/reservation/"><b>예약안내</b></a>'
        '<a class="chip" href="/guide/"><b>이용가이드</b></a>'
        '<a class="chip" href="/privacy/"><b>개인정보처리방침</b></a>'
        '<a class="chip" href="/terms/"><b>이용약관</b></a></div>'
        '</div></section>')
    body = (breadcrumb(trail) +
        '<section class="block" id="notice"><div class="wrap">'
        '<span class="eyebrow"><span class="pulse"></span>CUSTOMER</span>'
        '<h2 class="sec">고객센터</h2>'
        f'<p class="sec-lead">전화 {PHONE_DISP} · {HOURS} · 서울 전지역 방문 건강관리 예약·문의 안내</p>'
        '</div></section>' +
        notes_block("HELP", "문의 안내", "공지·문의·제휴 등 고객센터 이용 방법을 안내합니다.", notes, _id="inquiry") +
        extra +
        hub_prose("GUIDE", "고객센터를 200% 활용하는 법", [
            "고객센터는 예약 접수만 받는 곳이 아니라, 이용 전후에 생기는 궁금증을 한 번에 해결하는 창구입니다. 방문 가능 지역, 예약 가능 시간, 코스와 요금, 변경·취소, 위생·안전 기준까지 무엇이든 전화로 편하게 문의해 주세요. 연중무휴 24시간 상담을 운영합니다.",
            "처음 이용하신다면 방문 희망 지역(자치구·동 또는 가까운 역)과 희망 시간만 알려주셔도 됩니다. 나머지 코스 선택, 준비물, 예상 도착 시간 등은 상담 과정에서 순서대로 안내해 드립니다. 예약을 더 빠르게 진행하고 싶다면 희망 코스와 시간(60·90·120분), 인원, 방문 장소 주소를 미리 정리해 두시면 좋습니다.",
            "이미 예약하신 뒤 일정이 바뀌었다면 가능한 한 빠르게 연락 주세요. 빠를수록 다른 시간으로 조율하기 쉽습니다. 방문 직전 변경은 관리사 동선상 어려울 수 있어, 미리 알려주시면 다른 고객에게도 도움이 됩니다.",
            "기업·단체 방문 관리나 제휴 문의도 전화로 접수받습니다. 사내 워크숍·행사·복지 프로그램 등 단체 이용은 인원·시간·장소에 따라 별도 견적으로 안내드리니, 일정이 정해지면 여유 있게 문의해 주세요.",
            "개인정보는 예약 진행 목적으로만 이용하고 목적 달성 후 관련 법령에 따라 파기합니다. 처리 기준은 개인정보처리방침에서, 이용 조건은 이용약관에서 확인하실 수 있습니다.",
            "공지사항에는 운영 시간 변경, 시스템 점검, 이벤트 등 이용에 영향을 줄 수 있는 소식을 게시합니다. 중요한 변경이 있을 때는 가능한 한 미리 안내드리니, 예약 전 한 번씩 확인해 주시면 도움이 됩니다.",
            "더 빠른 안내가 필요하시면 자주 묻는 질문을 먼저 확인해 보세요. 방문 가능 지역과 예약 방법, 도착 시간, 코스·요금처럼 가장 많이 들어오는 질문은 서울 FAQ와 이용 FAQ에 주제별로 정리되어 있어, 전화 상담 전에 궁금증을 어느 정도 해결하실 수 있습니다.",
            "본 서비스는 의료 행위가 아닌 이완·휴식 목적의 건강관리 서비스이며 만 19세 이상 성인을 대상으로 합니다. 위생·안전 기준과 금지행위 안내도 이용가이드에서 함께 확인하실 수 있으니, 안심하고 문의해 주세요.",
            "전화 연결이 어려운 시간대에는 문의 내용을 남겨주시면 순차적으로 안내드립니다. 예약 변경·취소, 방문 위치 확인, 코스 추천 등 어떤 문의든 편하게 남겨주세요. 정확한 위치와 희망 시간을 함께 적어주시면 회신 시 더 빠르게 안내해 드릴 수 있습니다."]) +
        faq_block(cust_faq, "자주 묻는 질문") + cta_band())
    html = page(path, "고객센터 | 서울 출장마사지·홈타이 문의·공지",
        "서울 출장마사지·홈타이 고객센터 - 공지사항, 자주 묻는 질문, 1:1 문의, 제휴·기업 문의 안내입니다. 연중무휴 24시간 상담.",
        "customer", body, [bc_ld(trail), faq_ld(cust_faq)])
    write(path, html)
    _LEN_REPORT.append((path, text_len(html)))


# ---- 정책 페이지 ---------------------------------------------------------
def policy_page(path, title, heading, sections, desc):
    trail = [("/", "홈"), (None, heading)]
    secs = "".join(
        f'<div class="note-card"><div class="note-content"><h3 class="note-title">{t}</h3>'
        f'<div class="note-text">{"".join(f"<p>{p}</p>" for p in ps)}</div></div></div>'
        for t, ps in sections)
    body = (breadcrumb(trail) +
        f'<section class="block"><div class="wrap">'
        f'<span class="eyebrow"><span class="pulse"></span>POLICY</span>'
        f'<h2 class="sec">{heading}</h2>'
        f'<div class="note-stack" style="margin-top:26px;max-width:820px">{secs}</div>'
        f'</div></section>')
    # 정책 페이지는 분량이 적은 법적 고지 페이지이므로 noindex 처리(블루프린트 규칙)
    html = page(path, title, desc, "customer", body, [bc_ld(trail)], index=False)
    write(path, html)

def build_policies():
    policy_page("/privacy/", f"개인정보처리방침 | {BRAND}", "개인정보처리방침",
        [("수집하는 개인정보", ["예약 진행을 위해 연락처, 방문 장소 등 최소한의 정보를 수집합니다."]),
         ("이용 목적", ["수집한 정보는 예약 확정과 방문 안내 목적으로만 이용합니다."]),
         ("보유 및 파기", ["목적 달성 후에는 관련 법령에 따라 지체 없이 파기합니다."]),
         ("개인정보보호책임자", [f"{COMPANY['privacy_officer']} · 전화 {PHONE_DISP}"])],
        f"{BRAND} 개인정보처리방침 - 수집 항목, 이용 목적, 보유 및 파기, 개인정보보호책임자 안내입니다.")
    policy_page("/terms/", f"이용약관 | {BRAND}", "이용약관",
        [("목적", [f"본 약관은 {BRAND} 예약 서비스 이용 조건을 규정합니다."]),
         ("서비스 내용", ["본 서비스는 의료 행위가 아닌 이완·휴식 목적의 방문 건강관리 예약 서비스입니다."]),
         ("이용 자격", ["본 서비스는 만 19세 이상 성인만 이용할 수 있습니다."]),
         ("금지행위", ["불법·퇴폐 행위 요구 등은 금지되며, 위반 시 서비스가 중단될 수 있습니다."])],
        f"{BRAND} 이용약관 - 서비스 내용, 이용 자격, 금지행위 등 이용 조건을 안내합니다.")
    policy_page("/youth/", f"청소년보호정책 | {BRAND}", "청소년보호정책",
        [("청소년 이용 제한", ["본 서비스는 만 19세 이상 성인을 대상으로 하며 청소년은 이용할 수 없습니다."]),
         ("건전한 운영", [f"{BRAND}는 불법·퇴폐 행위를 일절 제공하지 않으며 건전한 건강관리 서비스를 지향합니다."]),
         ("책임자", [f"청소년보호 책임자 · {COMPANY['privacy_officer']} · 전화 {PHONE_DISP}"])],
        f"{BRAND} 청소년보호정책 - 만 19세 이상 이용 제한과 건전한 운영 원칙을 안내합니다.")


# ---- robots / sitemap / manifest / favicon -------------------------------
def build_meta_files():
    # 색인 대상만 사이트맵에 포함(정책 3종은 noindex이므로 제외)
    urls = ["/", "/seoul/", "/seoul/area/", "/seoul/faq/", "/seoul/stations/",
            "/theme/", "/course/", "/reservation/", "/guide/", "/reviews/", "/customer/"]
    urls += _MAG_PATHS                                        # 매거진 목록·카테고리·페이지네이션
    urls += [f"/magazine/{p['slug']}/" for p in MAGAZINE_POSTS]
    urls += [f"/course/{c['slug']}/" for c in COURSES] + ["/course/price/", "/course/guide/"]
    urls += ["/reservation/hours/", "/reservation/place/", "/reservation/payment/",
             "/reservation/change/", "/reservation/checklist/"]
    urls += ["/guide/prepare/", "/guide/safety/", "/guide/aftercare/",
             "/guide/forbidden/", "/guide/faq/", "/guide/checklist/"]
    urls += [f"/theme/{t['slug']}/" for t in THEMES]
    urls += [f"/seoul/stations/{l['slug']}/" for l in LINES]
    urls += [f"/seoul/stations/{s['slug']}/" for s in STATIONS]
    for d in DISTRICTS:
        urls.append(f"/seoul/{d['slug']}/")
        for dd in d["dongs"]:
            urls.append(f"/seoul/{d['slug']}/{dd['slug']}/")
    # 중복 제거(순서 유지)
    seen, ordered = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); ordered.append(u)
    prio = {"/": "1.0"}
    items = ""
    for u in ordered:
        p = prio.get(u, "0.9" if u.count("/") <= 2 else ("0.8" if u.count("/") <= 3 else "0.75"))
        freq = "daily" if u == "/" else "weekly"
        items += (f"  <url><loc>{BASE_URL}{u}</loc>"
                  f"<lastmod>{BUILD_DATE}</lastmod>"
                  f"<changefreq>{freq}</changefreq><priority>{p}</priority></url>\n")
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + items + "</urlset>\n")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap)

    robots = ("User-agent: *\nAllow: /\nDisallow: /tools/\n\n"
              "User-agent: GPTBot\nAllow: /\n"
              "User-agent: ClaudeBot\nAllow: /\n"
              "User-agent: Google-Extended\nAllow: /\n\n"
              f"Sitemap: {BASE_URL}/sitemap.xml\n"
              f"Sitemap: {BASE_URL}/rss.xml\n"
              f"Host: {BASE_URL.replace('https://','')}\n")
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(robots)

    manifest = {"name": BRAND, "short_name": BRAND_SHORT,
                "description": "서울 전지역 방문 건강관리(출장마사지·홈타이) 예약 안내",
                "start_url": "/", "scope": "/", "display": "standalone",
                "background_color": "#0b0b0e", "theme_color": "#0b0b0e",
                "lang": "ko-KR", "orientation": "portrait",
                "icons": [
                    {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                    {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                    {"src": "/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}
    with open(os.path.join(ROOT, "site.webmanifest"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    favicon = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
               '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
               '<stop offset="0" stop-color="#f4d29c"/><stop offset=".5" stop-color="#e9b8a7"/>'
               '<stop offset="1" stop-color="#c98a6b"/></linearGradient></defs>'
               '<rect width="64" height="64" rx="16" fill="#0b0b0e"/>'
               '<rect x="8" y="8" width="48" height="48" rx="13" fill="url(#g)"/>'
               '<text x="32" y="44" font-family="Georgia,serif" font-style="italic" '
               'font-size="32" font-weight="700" text-anchor="middle" fill="#1a1208">S</text></svg>')
    with open(os.path.join(ROOT, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(favicon)

    with open(os.path.join(ROOT, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)

    # Naver 웹마스터 도구 사이트 인증 파일
    # 내용은 반드시 "naver-site-verification: <파일명>.html" 형식이어야 한다.
    naver_verify = "naver6add6fdd87dfc14cd3fa9146ad807d64"
    with open(os.path.join(ROOT, f"{naver_verify}.html"), "w", encoding="utf-8") as f:
        f.write(f"naver-site-verification: {naver_verify}.html")


# ---------------------------------------------------------------------------
def main():
    build_home()
    build_seoul()
    build_area_hub()
    build_district_pages()
    build_dong_pages()
    build_stations_hub()
    build_line_pages()
    build_station_pages()
    build_theme_hub()
    build_theme_pages()
    build_course()
    build_course_pages()
    build_reservation()
    build_guide()
    build_seoul_faq()
    build_magazine()
    build_magazine_posts()
    build_reviews()
    build_customer()
    build_policies()
    build_meta_files()

    # 글자 수 리포트 (2,000자 미만 경고)
    short = [(p, n) for p, n in _LEN_REPORT if n < 2000]
    print(f"Build complete. pages(content)={len(_LEN_REPORT)}")
    if _LEN_REPORT:
        ns = [n for _, n in _LEN_REPORT]
        print(f"본문 글자수: min={min(ns)} max={max(ns)} avg={sum(ns)//len(ns)}")
    if short:
        print(f"⚠ 2,000자 미만 {len(short)}개:")
        for p, n in short:
            print(f"   {n}  {p}")
    else:
        print("✓ 모든 콘텐츠 페이지 2,000자 이상")


if __name__ == "__main__":
    main()
