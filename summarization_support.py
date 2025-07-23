from pathlib import Path
from typing import List

def summarize_file(file_path: Path, max_lines: int = 20) -> str:
    """
    تلخيص ملف نصي: أول وأسطر أخيرة + أسماء الدوال والكلاسات (للمعاينة السريعة)
    """
    lines = file_path.read_text(encoding='utf-8', errors='ignore').splitlines()
    summary = []
    if len(lines) <= max_lines:
        return '\n'.join(lines)
    # أول 5 أسطر
    summary.extend(lines[:5])
    summary.append('...')
    # أسماء الدوال والكلاسات
    import re
    for i, line in enumerate(lines):
        if re.match(r'\s*def |\s*class ', line):
            summary.append(f"[{i+1}] {line.strip()}")
    summary.append('...')
    # آخر 5 أسطر
    summary.extend(lines[-5:])
    return '\n'.join(summary) 