# Changelog | سجل التغييرات

All notable changes are documented here.
جميع التغييرات المهمة موثقة في هذا الملف.

## [2.0.0] — 2026-08

### ✨ Added | مضاف
- **Health score (0–100)** with letter grade and factor breakdown
  (درجة صحة شاملة مع تقدير حرفي وتفصيل العوامل)
- Standalone **HTML report** (`report.html`) — works offline
  (تقرير HTML مستقل يعمل بدون إنترنت)
- **Parallel file analysis** via ThreadPoolExecutor + `--workers` option
  (تحليل متوازٍ للملفات)
- `--exclude` / `--include` glob filtering
  (تصفية مرنة بأنماط الاستبعاد والتضمين)
- `gui` subcommand — launch the desktop app from the CLI
  (أمر gui لتشغيل الواجهة الرسومية)
- Monorepo mode now skips vendor dirs and the root itself
  (تحسين دعم المستودعات متعددة المشاريع)
- pyproject.toml / Gemfile / build.gradle project detection
  (كشف أنواع مشاريع إضافية)
- AI summaries support openai>=1.0 SDK *and* legacy versions, capped at 50 files
  (دعم إصداري مكتبة OpenAI مع حد أقصى للتكلفة)
- Full pytest suite (**60+ tests**) + GitHub Actions CI on 3 OSes × Python 3.9–3.13
  (حزمة اختبارات شاملة وخط CI متعدد المنصات)
- Bilingual documentation: this README, CONTRIBUTING.md, CHANGELOG.md
  (توثيق ثنائي اللغة كامل)

### ⚡ Performance | أداء
- External tools (radon, bandit, pylint, flake8, eslint) run once per batch of files
  instead of one subprocess per file → **10–50× faster** on large projects
  (تشغيل الأدوات على دفعات بدل عملية لكل ملف)
- File-dependency graph rebuilt from O(n²) to O(n·m) indexed matching
  (إعادة بناء رسم التبعيات بفهرسة أسرع)
- Early directory pruning during scanning (node_modules, caches, hidden dirs)
  (تخطي مبكر للمجلدات غير الضرورية)

### 🐛 Fixed | مصلح
- `--ai-key` was parsed but never passed to the analyzer
  (`--ai-key` كان يُقرأ ولا يُمرَّر للمحلل!)
- Documentation generators resolved source paths against the output folder,
  breaking custom `-o` locations; now anchored to the real project root
  (مسارات المصادر تُحل الآن نسبةً لجذر المشروع الحقيقي)
- Hardcoded generation timestamp in ai-summary.json → real UTC time
  (تاريخ التوليد الثابت أصبح ديناميكيًا)
- GUI broken imports (`sys.path.append('..')`) → proper package-relative imports;
  runnable via `python smartrepo_analyzer.py gui` or `python -m gui`
  (إصلاح استيرادات الواجهة المعطوبة)
- FileBrowser expected summaries in a path/format never produced by the generator
  (مطابقة مسارات ملخصات الملفات في الواجهة)
- radon MI JSON parsing (returns a list, not a dict)
  (تصحيح قراءة نتائج radon)
- `create-requirements` omitted rich/networkx and wrote incomplete file
  (استكمال requirements.txt الناقص)

### 🧹 Changed | معدَّل
- Removed committed junk: `.jython_cache/`, stray `call-graph.mmd`
  (تنظيف ملفات عشوائية من المستودع)
- Modernized `.gitignore`
- Version bumped to 2.0.0

## [1.0.0] — 2025

- Initial public release: multi-language analysis, Mermaid diagrams,
  complexity option, bilingual Tkinter GUI
  (الإصدار الأول العام: تحليل متعدد اللغات، مخططات، وواجهة رسومية ثنائية اللغة)
