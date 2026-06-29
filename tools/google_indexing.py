#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Google Indexing API 제출기 (URL_UPDATED 알림).

⚠️ 중요 — 공식 정책:
  Google Indexing API는 공식적으로 JobPosting / BroadcastEvent(라이브) 구조화
  데이터가 있는 페이지만 지원합니다. 일반 페이지 제출은 보장되지 않으며 무시될
  수 있습니다. 일반 콘텐츠 색인은 Search Console 등록 + sitemap 제출이 정공법이고,
  즉시 통보는 IndexNow(빙·네이버)를 사용하세요. 이 스크립트는 보조용입니다.

사전 준비:
  1) Google Cloud 프로젝트에서 Indexing API 사용 설정
  2) 서비스 계정 생성 → JSON 키 발급
  3) Search Console 속성(도메인)에 그 서비스 계정 이메일을 '소유자'로 추가
  4) pip install google-auth
  5) 환경변수 GOOGLE_APPLICATION_CREDENTIALS=서비스계정.json

사용법:
  python3 tools/google_indexing.py --all          # sitemap.xml 전체
  python3 tools/google_indexing.py https://.../a/  # 특정 URL
  python3 tools/google_indexing.py --all --delete  # 색인 삭제 통보(URL_DELETED)
"""
import os, sys, json, re, glob, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://bespoke-froyo-f91c15.netlify.app"
API = "https://indexing.googleapis.com/v3/urlNotifications:publish"
SCOPE = "https://www.googleapis.com/auth/indexing"


def get_token():
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred or not os.path.exists(cred):
        sys.exit("ERROR: GOOGLE_APPLICATION_CREDENTIALS(서비스계정 JSON 경로)를 설정하세요.")
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests as gtr
    except ImportError:
        sys.exit("ERROR: pip install google-auth 가 필요합니다.")
    creds = service_account.Credentials.from_service_account_file(cred, scopes=[SCOPE])
    creds.refresh(gtr.Request())
    return creds.token


def urls_from_sitemap():
    sm = os.path.join(ROOT, "sitemap.xml")
    return re.findall(r"<loc>([^<]+)</loc>", open(sm, encoding="utf-8").read())


def publish(url, token, typ):
    body = json.dumps({"url": url, "type": typ}).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:200]


def main(argv):
    typ = "URL_DELETED" if "--delete" in argv else "URL_UPDATED"
    args = [a for a in argv if a not in ("--delete",)]
    if "--all" in args:
        urls = urls_from_sitemap()
    else:
        urls = [a for a in args if a.startswith("http")]
    if not urls:
        print(__doc__)
        return 1
    token = get_token()
    ok = 0
    for u in sorted(set(urls)):
        st, msg = publish(u, token, typ)
        print(f"  [{st}] {u} {msg}")
        ok += (st == 200)
    print(f"완료: {ok}/{len(set(urls))} 정상")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
