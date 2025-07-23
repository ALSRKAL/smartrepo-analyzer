from pathlib import Path
from typing import List

def find_subprojects(root: Path) -> List[Path]:
    """
    البحث عن مجلدات مشاريع فرعية (monorepo) عبر ملفات إعداد معروفة
    """
    project_files = [
        'package.json', 'requirements.txt', 'Pipfile', 'pubspec.yaml',
        'Cargo.toml', 'go.mod', 'pom.xml', 'composer.json'
    ]
    subprojects = []
    for path in root.rglob('*'):
        if path.is_file() and path.name in project_files:
            subprojects.append(path.parent)
    return subprojects 