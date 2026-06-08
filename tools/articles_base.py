# -*- coding: utf-8 -*-
"""매거진 글 생성 공통 프레임워크: 카테고리 정의 + 글 등록 헬퍼."""

CATS = {
    "region":           {"name": "지역별 마사지",  "path": "/magazine/category/region/"},
    "swedish":          {"name": "스웨디시",       "path": "/magazine/category/swedish/"},
    "visiting":         {"name": "출장마사지",      "path": "/magazine/category/visiting/"},
    "korean-therapist": {"name": "한국인 관리사",   "path": "/magazine/category/korean-therapist/"},
    "thai-therapist":   {"name": "태국 관리사",     "path": "/magazine/category/thai-therapist/"},
}

ARTICLES = []

def A(**k):
    ARTICLES.append(k)
