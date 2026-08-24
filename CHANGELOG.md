# Changelog | سجل التغييرات

All notable changes are documented here.
جميع التغييرات المهمة موثقة في هذا الملف.

## [12.0.1] — 2026-08

### ✨ Added | مضاف — Deep Language Intelligence | ذكاء عميق للغات
- **Per-function cyclomatic complexity for ALL languages**, not just Python.
  A string/comment-aware brace scanner measures `if/for/while/case/catch`,
  Rust `match` arms, and short-circuit operators (`&&`, `||`, `??`) inside the
  exact function they belong to. Ruby gets a dedicated `def…end` scanner;
  Python stays on ground-truth AST.
  (تعقيد سيكلومي لكل دالة في **كل اللغات** عبر ماسح أقواس واعٍ للنصوص
  والتعليقات، مع ماسح مخصص لروبي وAST دقيق لبايثون)
- **Function signatures**: name, line number, argument count, kind
  (function/method/endpoint), visibility (exported/private) per language:
  Go capitals, Rust `pub`, Java/C#/PHP modifiers, JS/TS `export`, Swift `open`.
  (توقيعات كاملة: الاسم، السطر، عدد المعاملات، النوع، والظهور العام/الخاص)
- **HTTP API map**: REST endpoints auto-extracted from Flask/FastAPI route
  decorators, Express routers, Spring `@GetMapping`-family, and Gin routers —
  listed in HTML report, ai-summary.json and prompt-ready.md.
  (خريطة نقاط النهاية REST مستخرجة تلقائيًا من أشهر الأطر)
- **Documentation coverage**: % of public functions carrying docstrings /
  JSDoc / rustdoc — feeds the health score (+4 when ≥60%, −5 below 20%).
  (نسبة التغطية التوثيقية تؤثر الآن على درجة الصحة)
- **TODO/FIXME/HACK tracking** project-wide, surfaced in metrics & insights.
  (تتبع التعليقات المعلقة على مستوى المشروع)
- **Complexity hotspots**: top refactor candidates by complexity + arity,
  shown in console, HTML, ai-summary.json and prompt-ready.md.
  (أخطر الدوال تعقيدًا كمرشحين أوليين لإعادة الهيكلة)
- **Public API surface** extraction in ai-summary.json (`code_intelligence`
  section with endpoints, hotspots, top classes, exported symbols).
  (قسم استخبارات الكود الكامل داخل ملخص JSON)
- Deep analyzers for Go, Rust, Java, Kotlin, C#, PHP, Ruby, Dart, Swift,
  Scala, C/C++ headers; modern JS/TS syntax (arrow fns incl. single-param,
  async methods, object methods, TS interfaces/types/enums, JSX).
  (محللات عميقة لأكثر من ١٠ لغات إضافية وصياغات JS/TS الحديثة)

### 🐛 Fixed | مصلح
- Brace scanner no longer counts decision keywords or braces inside strings
  and comments (string-state machine per line).
  (الماسح يتجاهل الأقواس والكلمات المفتاحية داخل السلاسل النصية والتعليقات)
- Rust constructors named `new` are no longer filtered as keywords; premature
  function-close bug fixed by tracking enclosing brace depth.
  (إصلاح إسقاط دوال `new` وإغلاق الدوال قبل اكتمالها)
- `_python_scan` crashed silently on list-vs-set API mismatch, dropping all
  file intelligence for Python files.
  (إصلاح انهيار صامت كان يُسقط تحليل بايثون بالكامل)

### 🧪 Tests | اختبارات
- Suite grown to **78 tests**, incl. a new `test_deep_analysis.py` covering
  Go/Rust/Java/Kotlin/JS-TS/PHP/Ruby/Dart parsing, endpoints, visibility,
  documentation signals and string-safety edge cases.
  (نمو حزمة الاختبارات إلى ٧٨ اختبارًا مع تغطية اللغات الجديدة)

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
