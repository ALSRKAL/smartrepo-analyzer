LANGS = {
    'en': {
        'welcome': 'Welcome to SmartRepo Analyzer!',
        'select_project': 'Select Project Directory',
        'output_dir': 'Output Directory',
        'ai_key': 'AI Key',
        'enable_complexity': 'Enable Complexity Analysis',
        'start_analysis': 'Start Analysis',
        'progress': 'Progress',
        'logs': 'Logs',
        'results': 'Results',
        'readme': 'README',
        'diagrams': 'Diagrams',
        'summaries': 'Summaries',
        'search': 'Search',
        'filter': 'Filter',
        'export': 'Export',
        'dashboard': 'Dashboard',
        'dark_mode': 'Dark Mode',
        'light_mode': 'Light Mode',
        'language': 'Language',
        'arabic': 'Arabic',
        'english': 'English',
        'error': 'Error',
        'success': 'Success',
        'cancel': 'Cancel',
        'ok': 'OK',
        'splash_features': '• Professional analysis for popular programming languages\n• Diagrams and summaries\n• Bilingual support (Arabic/English)\n• Easy export\n• Modern UI with dark mode',
    },
    'ar': {
        'welcome': 'مرحبًا بك في SmartRepo Analyzer!',
        'select_project': 'اختر مجلد المشروع',
        'output_dir': 'مجلد الإخراج',
        'ai_key': 'مفتاح الذكاء الاصطناعي',
        'enable_complexity': 'تفعيل تحليل التعقيد',
        'start_analysis': 'ابدأ التحليل',
        'progress': 'التقدم',
        'logs': 'السجل',
        'results': 'النتائج',
        'readme': 'ملف README',
        'diagrams': 'المخططات',
        'summaries': 'الملخصات',
        'search': 'بحث',
        'filter': 'تصفية',
        'export': 'تصدير',
        'dashboard': 'لوحة الإحصائيات',
        'dark_mode': 'الوضع الليلي',
        'light_mode': 'الوضع النهاري',
        'language': 'اللغة',
        'arabic': 'العربية',
        'english': 'الإنجليزية',
        'error': 'خطأ',
        'success': 'نجاح',
        'cancel': 'إلغاء',
        'ok': 'موافق',
        'splash_features': '• تحليل احترافي لأشهر لغات البرمجة\n• عرض المخططات والملخصات\n• دعم ثنائي اللغة (عربي/إنجليزي)\n• تصدير النتائج بسهولة\n• واجهة عصرية ودعم الوضع الليلي',
    }
}

current_lang = 'ar'

def tr(key):
    return LANGS[current_lang].get(key, key)

def set_lang(lang):
    global current_lang
    if lang in LANGS:
        current_lang = lang 