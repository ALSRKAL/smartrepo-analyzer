import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional

def parse_coverage_xml(xml_path: Path) -> Optional[Dict[str, float]]:
    """
    تحليل تقرير coverage.xml وإرجاع نسبة التغطية لكل ملف (filename -> percent)
    """
    if not xml_path.exists():
        return None
    tree = ET.parse(xml_path)
    root = tree.getroot()
    coverage_data = {}
    for cls in root.findall('.//class'):
        filename = cls.attrib.get('filename')
        lines_elem = cls.find('lines')
        if not filename or lines_elem is None:
            continue
        total = 0
        covered = 0
        for line in lines_elem.findall('line'):
            total += 1
            if line.attrib.get('hits') and int(line.attrib['hits']) > 0:
                covered += 1
        percent = (covered / total * 100) if total > 0 else 0.0
        coverage_data[filename] = percent
    return coverage_data

def get_overall_coverage(coverage_data: Dict[str, float]) -> float:
    """
    حساب متوسط التغطية لجميع الملفات
    """
    if not coverage_data:
        return 0.0
    return sum(coverage_data.values()) / len(coverage_data) 