# Contributing | المساهمة

<div dir="rtl">

شكرًا لاهتمامك بتحسين SmartRepo Analyzer! هذا الدليل يشرح كيف تساهم بخطوات واضحة.

</div>

Thank you for improving SmartRepo Analyzer! This guide explains how to contribute.

## 🛠️ Development Setup | تجهيز بيئة التطوير

```bash
git clone https://github.com/ALSRKAL/smartrepo-analyzer.git
cd smartrepo-analyzer

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install pytest ruff          # dev tools

pytest tests/                    # run the suite | تشغيل الاختبارات
ruff check .                     # lint | فحص التنسيق
```

## 🌿 Workflow | سير العمل

1. Fork → create a branch: `git checkout -b feature/my-feature`
   (أنشئ فرعًا جديدًا لميزتك)
2. Make changes **with tests** for any new behavior.
   (أضف اختبارات لأي سلوك جديد)
3. Ensure everything passes:
   ```bash
   pytest tests/ -v
   python smartrepo_analyzer.py analyze tests/../smartrepo_analyzer.py --no-lint -q || true
   ```
4. Commit using [conventional commits](https://www.conventionalcommits.org/):
   - `feat:` new feature — `fix:` bug fix — `docs:` documentation — `perf:` performance — `refactor:` cleanup
5. Open a Pull Request describing *what* and *why*.

## 📝 Code Guidelines | إرشادات الكود

- Python 3.9+ compatible; standard library first.
- Type hints on public functions (`typing`).
- Every external tool must degrade gracefully when missing
  (استخدم `tool_runner.tool_available` وتحقق قبل الاستخدام).
- Keep analysis modules pure where possible — easy to unit-test.
- Bilingual docstrings are welcome: English first, Arabic after.
- Never commit generated reports or secrets.

## 🧪 Adding Language Support | دعم لغة جديدة

1. Add extension to `SUPPORTED_EXTENSIONS` in `smartrepo_analyzer.py`.
2. Add an `_analyze_<lang>_file` method (regex is fine to start).
3. Wire it into `analyze_file`.
4. Add tests in `tests/test_analyzer.py`.

## 🐛 Reporting Bugs | الإبلاغ عن الأخطاء

Open an issue with:

- OS + Python version (نظام التشغيل وإصدار بايثون)
- Command you ran (الأمر المنفَّذ)
- Full traceback if available (تتبّع الخطأ كاملًا إن أمكن)
- A minimal sample project that reproduces it (نموذج صغير يعيد إنتاج المشكلة)

---

<div align="center" dir="rtl">

**كل مساهمة، مهما صغرت، تُحسب** 💙

</div>
