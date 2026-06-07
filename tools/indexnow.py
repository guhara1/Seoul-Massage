#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IndexNow 제출기 — 빙·네이버·얀덱스 등에 변경 URL을 즉시 통보.

IndexNow는 단일 엔드포인트(api.indexnow.org)로 제출하면 참여 검색엔진
(Bing, Naver, Yandex, Seznam 등)에 자동 전파됩니다. (구글은 미참여)

사용법:
  python3 tools/indexnow.py --all                # sitemap.xml의 모든 URL 제출
  python3 tools/indexnow.py --changed            # 직전 커밋 대비 바뀐 페이지만 제출
  python3 tools/indexnow.py https://.../a/ ...    # 특정 URL 직접 제출
  python3 tools/indexnow.py --all --dry-run       # 전송 없이 목록만 출력

키 파일(<KEY>.txt)은 빌드 시 사이트 루트에 생성되어 배포 도메인에서
https://<도메인>/<KEY>.txt 로 노출되어야 합니다.
"""
import os, sys, json, glob, re, subprocess, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "seoul-massage-at6.pages.dev"               # 배포 도메인 (호스트만)
BASE = "https://" + HOST
ENDPOINT = "https://api.indexnow.org/indexnow"   # 단일 제출 → 참여 엔진에 전파


def discover_key():
    """루트의 <KEY>.txt (내용==파일명 stem)에서 IndexNow 키를 찾는다."""
    for p in glob.glob(os.path.join(ROOT, "*.txt")):
        stem = os.path.splitext(os.path.basename(p))[0]
        if re.fullmatch(r"[0-9a-fA-F]{8,128}", stem):
            try:
                if open(p, encoding="utf-8").read().strip() == stem:
                    return stem
            except OSError:
                pass
    sys.exit("ERROR: IndexNow 키 파일(<KEY>.txt)을 찾을 수 없습니다. 먼저 `python3 tools/build.py` 실행.")


def path_to_url(rel):
    """index.html 경로 → 사이트 URL."""
    rel = rel.replace(os.sep, "/")
    if rel == "index.html":
        return BASE + "/"
    if rel.endswith("/index.html"):
        return BASE + "/" + rel[:-len("index.html")]
    return None


def urls_from_sitemap():
    sm = os.path.join(ROOT, "sitemap.xml")
    if not os.path.exists(sm):
        sys.exit("ERROR: sitemap.xml 이 없습니다. 먼저 빌드하세요.")
    return re.findall(r"<loc>([^<]+)</loc>", open(sm, encoding="utf-8").read())


def urls_changed():
    """직전 커밋 대비 변경된 index.html → URL."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD~1", "HEAD"],
            cwd=ROOT, text=True)
    except subprocess.CalledProcessError:
        out = ""
    urls = []
    for f in out.splitlines():
        if f.endswith("index.html"):
            u = path_to_url(f)
            if u:
                urls.append(u)
    return urls


def submit(urls, key, dry=False):
    urls = sorted(set(u for u in urls if u and u.startswith(BASE)))
    if not urls:
        print("제출할 URL이 없습니다.")
        return 0
    print(f"IndexNow 제출 대상 {len(urls)}건:")
    for u in urls:
        print("  ", u)
    if dry:
        print("(--dry-run: 전송하지 않음)")
        return 0
    payload = json.dumps({
        "host": HOST, "key": key,
        "keyLocation": f"{BASE}/{key}.txt",
        "urlList": urls,
    }).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=payload,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"응답: HTTP {r.status} (200/202 = 정상 접수)")
            return 0
    except urllib.error.HTTPError as e:
        print(f"응답: HTTP {e.code} — {e.read().decode('utf-8', 'ignore')[:300]}")
        # 200/202 외에도 IndexNow는 일부 4xx를 키 검증 지연으로 반환할 수 있음
        return 0 if e.code in (200, 202) else 1
    except Exception as e:
        print(f"전송 실패: {e}")
        return 1


def main(argv):
    dry = "--dry-run" in argv
    args = [a for a in argv if a != "--dry-run"]
    key = discover_key()
    if "--all" in args:
        urls = urls_from_sitemap()
    elif "--changed" in args:
        urls = urls_changed() or urls_from_sitemap()  # 변경 없으면 전체로 폴백
    else:
        urls = [a for a in args if a.startswith("http")]
        if not urls:
            print(__doc__)
            return 1
    return submit(urls, key, dry)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
