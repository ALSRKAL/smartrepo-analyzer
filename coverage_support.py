"""Coverage report parsing (coverage.py XML format).

تحليل تقارير التغطية بصيغة coverage.py XML، مع دعم قراءة النسبة
العامة من جذر الملف أو حسابها من بيانات الأسطر.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional


def parse_coverage_xml(xml_path: Path) -> Optional[Dict[str, float]]:
    """Parse ``coverage.xml`` -> ``{filename: percent}`` (None if missing).

    يحلل تقرير coverage.xml ويعيد نسبة تغطية كل ملف. يعيد None إذا
    لم يكن الملف موجودًا أو كان تالفًا.
    """
    if not xml_path.exists():
        return None
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return None
    root = tree.getroot()
    coverage_data: Dict[str, float] = {}

    # Fast path: overall line-rate on the root element.
    root_rate = root.attrib.get("line-rate")
    for cls in root.findall(".//class"):
        filename = cls.attrib.get("filename")
        lines_elem = cls.find("lines")
        if not filename or lines_elem is None:
            continue
        total = 0
        covered = 0
        for line in lines_elem.findall("line"):
            total += 1
            try:
                if int(line.attrib.get("hits", "0")) > 0:
                    covered += 1
            except ValueError:
                continue
        percent = (covered / total * 100) if total > 0 else 0.0
        coverage_data[filename] = round(percent, 2)

    if coverage_data and root_rate:
        try:
            coverage_data["__overall__"] = float(root_rate) * 100
        except ValueError:
            pass
    return coverage_data or None


def get_overall_coverage(coverage_data: Dict[str, float]) -> float:
    """Return the mean coverage percentage across files.

    يحسب متوسط نسبة التغطية لجميع الملفات، ويفضّل النسبة العامة
    المسجلة في التقرير إن وجدت.
    """
    if not coverage_data:
        return 0.0
    if "__overall__" in coverage_data:
        return round(coverage_data["__overall__"], 1)
    per_file = [v for k, v in coverage_data.items() if k != "__overall__"]
    if not per_file:
        return 0.0
    return round(sum(per_file) / len(per_file), 1)
