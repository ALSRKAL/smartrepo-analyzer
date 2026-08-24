"""Framework detection by scanning source files for import signatures.

اكتشاف أطر العمل المستخدمة في المشروع عبر فحص عبارات الاستيراد،
مع قراءة كل ملف مرة واحدة فقط وتجميع الأنماط المحمّلة مسبقًا.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set

# Compiled regex patterns per framework (checked against lowercased content).
FRAMEWORK_HINTS: Dict[str, List[re.Pattern]] = {
    "django": [re.compile(p) for p in (r"import django", r"from django")],
    "flask": [re.compile(p) for p in (r"import flask", r"from flask")],
    "fastapi": [re.compile(p) for p in (r"import fastapi", r"from fastapi")],
    "streamlit": [re.compile(p) for p in (r"import streamlit", r"from streamlit")],
    "pydantic": [re.compile(r"from pydantic|import pydantic")],
    "sqlalchemy": [re.compile(r"from sqlalchemy|import sqlalchemy")],
    "pytest": [re.compile(r"import pytest|from pytest")],
    "react": [re.compile(p) for p in (r"from ['\"]react['\"]", r"import react", r"@types/react")],
    "vue": [re.compile(p) for p in (r"from ['\"]vue['\"]", r"import vue")],
    "angular": [re.compile(p) for p in (r"@angular/core", r"from ['\"]@angular")],
    "express": [re.compile(p) for p in (r"require\(['\"]express['\"]\)", r"from ['\"]express['\"]")],
    "nextjs": [re.compile(p) for p in (r"from ['\"]next/", r"from ['\"]next['\"]", r"import next")],
    "nuxt": [re.compile(r"from ['\"]@nuxt|@nuxtjs")],
    "svelte": [re.compile(r"from ['\"]svelte")],
    "flutter": [re.compile(r"import ['\"]package:flutter")],
    "laravel": [re.compile(p) for p in (r"illuminate\\", r"namespace app\\")],
    "spring": [re.compile(r"import org\.springframework")],
    "rails": [re.compile(r"require ['\"]rails['\"]")],
    "symfony": [re.compile(r"use symfony")],
    "nestjs": [re.compile(r"@nestjs/")],
    "gin": [re.compile(r"github\.com/gin-gonic/gin")],
    "actix": [re.compile(r"use actix_web")],
}


def detect_frameworks(files: List[Path]) -> Set[str]:
    """Return the set of framework identifiers found across ``files``.

    يفحص كل ملف مرة واحدة ويجمع أنماط جميع الأطر لتقليل عمليات
    القراءة المتكررة، مما يحسّن السرعة على المشاريع الكبيرة.
    """
    found: Set[str] = set()
    for file in files:
        try:
            content = file.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            continue
        for fw, patterns in FRAMEWORK_HINTS.items():
            if fw in found:
                continue
            if any(pat.search(content) for pat in patterns):
                found.add(fw)
    return found
