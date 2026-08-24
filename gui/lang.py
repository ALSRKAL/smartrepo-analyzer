"""Bilingual (AR/EN) UI strings for SmartRepo Analyzer GUI.

نصوص الواجهة ثنائية اللغة (العربية/الإنجليزية).
"""

LANGS = {
    "en": {
        "welcome": "Welcome to SmartRepo Analyzer!",
        "select_project": "Project Directory",
        "output_dir": "Output Directory",
        "ai_key": "AI Key",
        "enable_complexity": "Enable Complexity Analysis",
        "start_analysis": "Start Analysis",
        "progress": "Progress",
        "logs": "Logs",
        "results": "Results",
        "readme": "README",
        "diagrams": "Diagrams",
        "summaries": "Summaries",
        "search": "Search files…",
        "filter": "Filter",
        "export": "Export",
        "dashboard": "Dashboard",
        "dark_mode": "🌙 Dark Mode",
        "light_mode": "☀ Light Mode",
        "language": "Language",
        "arabic": "Arabic",
        "english": "English",
        "error": "Error",
        "success": "Success",
        "cancel": "Cancel",
        "ok": "OK",
        "analysis_done": "Analysis completed successfully!",
        "analysis_failed": "Analysis failed — check the log for details.",
        "no_results": "No results found. Run an analysis first.",
        "select_project_first": "Please select a project directory first.",
        "health_score": "Health Score",
        "splash_features": (
            "• Professional analysis of 20+ programming languages\n"
            "• Diagrams, summaries & AI-ready reports\n"
            "• Bilingual support (Arabic/English)\n"
            "• One-click export\n"
            "• Modern UI with dark mode"
        ),
    },
    "ar": {
        "welcome": "مرحبًا بك في SmartRepo Analyzer!",
        "select_project": "مجلد المشروع",
        "output_dir": "مجلد الإخراج",
        "ai_key": "مفتاح الذكاء الاصطناعي",
        "enable_complexity": "تفعيل تحليل التعقيد",
        "start_analysis": "ابدأ التحليل",
        "progress": "التقدم",
        "logs": "السجل",
        "results": "النتائج",
        "readme": "ملف README",
        "diagrams": "المخططات",
        "summaries": "الملخصات",
        "search": "ابحث في الملفات…",
        "filter": "تصفية",
        "export": "تصدير",
        "dashboard": "لوحة الإحصائيات",
        "dark_mode": "🌙 الوضع الليلي",
        "light_mode": "☀ الوضع النهاري",
        "language": "اللغة",
        "arabic": "العربية",
        "english": "الإنجليزية",
        "error": "خطأ",
        "success": "نجاح",
        "cancel": "إلغاء",
        "ok": "موافق",
        "analysis_done": "اكتمل التحليل بنجاح!",
        "analysis_failed": "فشل التحليل — راجع السجل للتفاصيل.",
        "no_results": "لا توجد نتائج. شغّل التحليل أولًا.",
        "select_project_first": "يرجى اختيار مجلد المشروع أولًا.",
        "health_score": "درجة الصحة",
        "splash_features": (
            "• تحليل احترافي لأكثر من ٢٠ لغة برمجة\n"
            "• مخططات وملخصات وتقارير جاهزة للذكاء الاصطناعي\n"
            "• دعم ثنائي اللغة (عربي/إنجليزي)\n"
            "• تصدير النتائج بضغطة واحدة\n"
            "• واجهة عصرية مع وضع ليلي"
        ),
    },
}

current_lang = "ar"


def tr(key):
    """Translate a key using the active language."""
    return LANGS[current_lang].get(key, key)


def set_lang(lang):
    global current_lang
    if lang in LANGS:
        current_lang = lang
