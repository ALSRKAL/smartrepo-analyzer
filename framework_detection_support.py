from pathlib import Path
from typing import List, Set
import re

FRAMEWORK_HINTS = {
    'django': [r'import django', r'from django'],
    'flask': [r'import flask', r'from flask'],
    'fastapi': [r'import fastapi', r'from fastapi'],
    'streamlit': [r'import streamlit', r'from streamlit'],
    'react': [r'from \'react\'', r'import React', r'@types/react'],
    'vue': [r'from \'vue\'', r'import Vue'],
    'angular': [r'@angular/core', r'from \'@angular'],
    'express': [r'require\([\'\"]express[\'\"]\)', r'from \'express\''],
    'nextjs': [r'from \'next\'', r'import Next'],
    'flutter': [r'import \'package:flutter'],
    'laravel': [r'Illuminate\\', r'namespace App\\'],
    'spring': [r'import org.springframework'],
    'rails': [r'require \'rails\''],
    'symfony': [r'use Symfony'],
    'nestjs': [r'@nestjs/'],
    'svelte': [r'from \'svelte\''],
}

def detect_frameworks(files: List[Path]) -> Set[str]:
    found = set()
    for file in files:
        try:
            content = file.read_text(encoding='utf-8', errors='ignore').lower()
            for fw, patterns in FRAMEWORK_HINTS.items():
                for pat in patterns:
                    if re.search(pat, content):
                        found.add(fw)
        except Exception:
            continue
    return found 