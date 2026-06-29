# -*- coding: utf-8 -*-
"""색인 가속용 SEO 산출물 생성:
  1) rss.xml          — 매거진 글 피드(최신순). 구글은 RSS도 사이트맵으로 인정.
  2) sitemap.xml      — 각 <url>에 <lastmod> 추가(신선도 신호).
원본은 magazine/index.html 의 JSON-LD(blogPost)에서 글 목록을 읽는다.
"""
import os, re, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://bespoke-froyo-f91c15.netlify.app"
SITE_NAME = "Seoul 마사지"
SITE_DESC = "서울 출장마사지·홈타이 이용 가이드·정보 매거진"
TODAY = datetime.date(2026, 6, 8)

def rfc822(d):
    # 한국시간(+0900) 자정 기준
    return d.strftime("%a, %d %b %Y 00:00:00 +0900")

# ── 매거진 글 목록(blogPost JSON-LD) 파싱 ─────────────────────
idx = open(os.path.join(ROOT, "magazine/index.html"), encoding="utf-8").read()
posts = []  # (url, title, date)
for m in re.finditer(r'\{"@type":"BlogPosting","headline":"(.*?)","datePublished":"(\d{4}-\d{2}-\d{2})","url":"([^"]+)"\}', idx):
    title, date, url = m.group(1), m.group(2), m.group(3)
    posts.append((url, title, date))
# 최신순
posts.sort(key=lambda x: x[2], reverse=True)
print(f"매거진 글 {len(posts)}편 수집")

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))

# 글별 meta description 읽기(있으면 RSS description으로)
def desc_of(url):
    rel = url.replace(BASE + "/", "").strip("/")
    p = os.path.join(ROOT, rel, "index.html")
    if os.path.exists(p):
        h = open(p, encoding="utf-8").read(4000)
        mm = re.search(r'<meta name="description" content="([^"]*)"', h)
        if mm:
            return mm.group(1)
    return SITE_DESC

# ── rss.xml 작성 ─────────────────────────────────────────────
items = []
for url, title, date in posts:
    d = datetime.date.fromisoformat(date)
    items.append(
        "<item>"
        f"<title>{esc(title)}</title>"
        f"<link>{url}</link>"
        f"<guid isPermaLink=\"true\">{url}</guid>"
        f"<pubDate>{rfc822(d)}</pubDate>"
        f"<description>{esc(desc_of(url))}</description>"
        "</item>"
    )
last_build = rfc822(posts[0] and datetime.date.fromisoformat(posts[0][2]) or TODAY)
rss = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
    '<channel>\n'
    f'<title>{esc(SITE_NAME)} 매거진</title>\n'
    f'<link>{BASE}/magazine/</link>\n'
    f'<description>{esc(SITE_DESC)}</description>\n'
    '<language>ko-KR</language>\n'
    f'<lastBuildDate>{last_build}</lastBuildDate>\n'
    f'<atom:link href="{BASE}/rss.xml" rel="self" type="application/rss+xml"/>\n'
    + "\n".join(items) + "\n"
    '</channel>\n</rss>\n'
)
open(os.path.join(ROOT, "rss.xml"), "w", encoding="utf-8").write(rss)
print(f"rss.xml 생성: {len(items)} items")

# ── sitemap.xml 에 lastmod 주입 ──────────────────────────────
date_by_url = {u: d for (u, _t, d) in posts}
sm_path = os.path.join(ROOT, "sitemap.xml")
sm = open(sm_path, encoding="utf-8").read()

def add_lastmod(m):
    block = m.group(0)
    if "<lastmod>" in block:
        return block  # 이미 있으면 유지
    loc = re.search(r"<loc>([^<]+)</loc>", block).group(1)
    d = date_by_url.get(loc, TODAY.isoformat())
    # <loc> 바로 뒤에 lastmod 삽입
    return block.replace("</loc>", f"</loc><lastmod>{d}</lastmod>", 1)

sm2 = re.sub(r"<url>.*?</url>", add_lastmod, sm, flags=re.S)
open(sm_path, "w", encoding="utf-8").write(sm2)
print("sitemap.xml lastmod 주입 완료:", sm2.count("<lastmod>"), "건")
