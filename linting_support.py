import subprocess
from pathlib import Path
from typing import List, Dict

def run_pylint_on_files(files: List[Path]) -> List[Dict]:
    """
    تشغيل pylint على قائمة من الملفات وإرجاع النتائج (كل نتيجة عبارة عن dict)
    """
    results = []
    for file in files:
        proc = subprocess.run([
            'pylint', str(file), '--output-format=json', '--score=n'
        ], capture_output=True, text=True)
        if proc.returncode == 0 or proc.returncode == 32:  # 32: usage error, 0: no error
            try:
                import json
                lint_results = json.loads(proc.stdout)
                for item in lint_results:
                    item['file'] = str(file)
                results.extend(lint_results)
            except Exception:
                continue
        else:
            results.append({'file': str(file), 'error': proc.stderr})
    return results 