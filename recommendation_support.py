from typing import Dict, List

def generate_recommendations(metrics: Dict, coverage: float = None, lint_issues: int = None) -> List[str]:
    recs = []
    if metrics.get('average_complexity', 0) > 10:
        recs.append("الكود معقد جدًا في بعض الملفات، يُنصح بتقسيمها أو إعادة هيكلتها.")
    if metrics.get('total_lines', 0) > 10000:
        recs.append("المشروع كبير جدًا، فكر في تقسيمه إلى وحدات أو حزم أصغر.")
    if coverage is not None and coverage < 60:
        recs.append("تغطية الاختبارات أقل من 60%، يُنصح بزيادة الاختبارات.")
    if lint_issues is not None and lint_issues > 20:
        recs.append("هناك العديد من مشاكل linting، يُنصح بتحسين جودة الكود.")
    if metrics.get('total_functions', 0) / (metrics.get('total_files', 1)) > 10:
        recs.append("هناك كثافة دوال عالية في بعض الملفات، فكر في توزيع الوظائف.")
    if not recs:
        recs.append("الكود منظم وجيد، استمر في العمل الجيد!")
    return recs 