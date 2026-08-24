<div align="center">

# ⚡ SmartRepo Analyzer

**AI-Powered Code Analysis & Documentation Tool**
**أداة ذكية لتحليل الأكواد وتوليد التوثيق**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-78%20passing-brightgreen)](https://github.com/ALSRKAL/smartrepo-analyzer/actions)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)](https://github.com/ALSRKAL/smartrepo-analyzer/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-12.0.1-purple)](#-changelog--سجل-التغييرات)

Analyze any codebase → get **health scores**, **architecture diagrams**, **security reports**, and **AI-ready documentation** in seconds.
حلّل أي مشروع برمجي واحصل على **درجات صحة**، **مخططات معمارية**، **تقارير أمنية**، و**توثيق جاهز للذكاء الاصطناعي** خلال ثوانٍ.

[🇬🇧 English](#english) · [🇸🇦 العربية](#العربية)

</div>

---

# English

## 📖 Table of Contents

- [Why SmartRepo?](#-why-smartrepo)
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Command Reference](#-command-reference)
- [Generated Outputs](#-generated-outputs)
- [Health Score](#-health-score)
- [Performance](#-performance)
- [CI/CD Integration](#-cicd-integration)
- [GUI Application](#-gui-application)
- [Troubleshooting](#-troubleshooting)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)

## 🎯 Why SmartRepo?

Most analyzers give you numbers. **SmartRepo gives you answers**: what the project does,
where the risks are, how healthy the code is, and documentation that both humans *and*
LLMs can consume immediately.

## ✨ Features

| | Feature / الميزة |
|---|---|
| 🔬 | **Deep per-function analysis for every language** — not just Python: function signatures, argument counts, line numbers and **per-function cyclomatic complexity** for Go, Rust, Java, Kotlin, C#, PHP, Ruby, Dart, Swift, Scala, JS/TS, C/C++ |
| 🛣️ | **HTTP API map** — auto-detects REST endpoints from Flask/FastAPI/Express/Spring/Gin decorators & routers |
| 📚 | **Documentation coverage** — % of public symbols carrying docstrings/JSDoc/rustdoc |
| 📝 | **TODO/FIXME/HACK tracking** across the whole codebase |
| 🔥 | **Complexity hotspots** — the exact functions you should refactor first |
| 🧩 | **Public API surface extraction** — exported symbols per language (Go capitals, Rust `pub`, JS `export`, Java `public`…) |
| 🔍 | **20+ languages**: Python, JavaScript/TypeScript, React, Go, Rust, Java, Kotlin, Dart, PHP, Ruby, C/C++, C#, Swift, Scala… |
| 🏥 | **Health score (0–100)** combining complexity, tests, linting, security, coverage and documentation |
| 🛡️ | **Security scanning** via bandit (batched — very fast) |
| 🌀 | **Cyclomatic complexity** via radon + maintainability index |
| 🕸️ | **Dependency graphs** between files + call-graph cycle detection |
| 🤖 | **AI summaries** through OpenAI API (`--ai-key`, optional) |
| 📊 | **Mermaid diagrams**: architecture, UML classes, file dependencies, call graphs |
| 🌐 | **Fully bilingual** UI & reports (Arabic / English) |
| ⚡ | **Parallel analysis** (ThreadPoolExecutor) + batched external tools |
| 🖥️ | Modern desktop GUI with dark mode and splash screen |
| 📄 | Standalone **HTML report** — no server, no internet needed |
| 🧩 | **Monorepo support** — analyzes every subproject automatically |
| 🚫 | Flexible `--exclude` / `--include` glob filtering |

## 📦 Installation

```bash
git clone https://github.com/ALSRKAL/smartrepo-analyzer.git
cd smartrepo-analyzer

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

**Optional extras** (auto-detected if installed):

```bash
pip install radon bandit pylint flake8   # deep quality & security analysis
npm install -g @mermaid-js/mermaid-cli    # PNG diagram rendering
```

> Requires Python 3.9+. Works on Windows, Linux and macOS.

## 🚀 Quick Start

```bash
# Analyze current directory
python smartrepo_analyzer.py analyze .

# Analyze another project into a custom folder
python smartrepo_analyzer.py analyze ~/my-app -o ./analysis

# Full power: complexity + security + everything
python smartrepo_analyzer.py analyze . --complexity --exclude "*.min.js"
```

Example session:

```
  ✓ Type: Python | Framework: FastAPI
  ✓ Analyzed 214 files (38,412 lines)
  ✓ Analysis finished in 6.2s
  ✓ Generated 14 artifacts
╭────────────────────────┬──────────────────╮
│ Files / Lines          │ 214 / 38,412     │
│ Avg Complexity         │ 4.7              │
│ Health Score           │ 87/100 (A)       │
╰────────────────────────┴──────────────────╯
```

## 📋 Command Reference

```
smartrepo_analyzer.py analyze <path> [options]
smartrepo_analyzer.py gui
smartrepo_analyzer.py create-requirements
smartrepo_analyzer.py version
smartrepo_analyzer.py help
```

### `analyze` options

| Flag | Description |
|---|---|
| `-o, --output DIR` | Custom output directory *(default: `<project>/smartrepo-analysis`)* |
| `--complexity` | Enable radon complexity/maintainability pass |
| `--no-lint` | Skip pylint/flake8/eslint passes |
| `--ai-key KEY` | OpenAI key for AI summaries (or env `SMARTREPO_AI_KEY`) |
| `--exclude PAT…` | Glob patterns to ignore (e.g. `"*.min.js" "docs/*"`) |
| `--include PAT…` | Only analyze files matching patterns |
| `--workers N` | Parallel workers *(default: CPU count)* |
| `-v / -q` | Verbose diagnostics / quiet mode |

## 📁 Generated Outputs

Everything lands in one folder:

| File | What it contains |
|---|---|
| 📄 `readme-enhanced.md` | Complete project README with stats, badges & setup guide |
| 🌐 `report.html` | Self-contained visual report (open in any browser) |
| 🧠 `ai-summary.json` | Machine-readable summary — perfect context for LLMs |
| 💬 `prompt-ready.md` | Pre-chunked documentation ready to paste into ChatGPT/Claude |
| 🗺️ `architecture.mmd` | Mermaid architecture diagram (+ `.png` if mermaid-cli installed) |
| 🧬 `uml-class-diagram.mmd` | Class relationships & inheritance |
| 🕸️ `file-dependency-graph.mmd` | Which files import which |
| 🔁 `call-graph-cycles.txt` | Circular call chains (code smells) |
| 🛡️ `security_report.json` | Bandit findings by severity |
| 🌀 `complexity_report.json` | Per-function cyclomatic complexity |
| 🔍 `flake8-linting.json` / `eslint-linting.json` | Style issues |
| 💡 `recommendations.txt` | Prioritized improvement suggestions |
| 👥 `contributors.txt` | Git contributor statistics |
| 📝 `summaries/` | Quick previews of large files |
| ✅ `usage-examples.txt` | Examples mined from docstrings & tests |

## 🏥 Health Score

A single number (0–100) summarizing project health:

| Factor | Weight |
|---|---|
| Average complexity | up to −25 |
| Test ratio | up to −18 / bonus +3 |
| Lint density | up to −15 |
| Security findings | up to −25 |
| Coverage (coverage.xml) | ±12 |
| Maintainability index | −8 |

Grades: `A+ ≥ 90` · `A ≥ 80` · `B ≥ 70` · `C ≥ 55` · `D ≥ 40` · `F < 40`

## ⚡ Performance

SmartRepo v2 is engineered for large codebases:

- **Parallel file parsing** across CPU cores
- **Batched external tools** — radon/bandit/pylint run once per ~64-file batch instead of once per file (**10–50× faster** on big projects)
- O(n·m) dependency-graph indexing instead of O(n²)
- Early directory pruning skips `node_modules`, `.git`, `venv`, caches…

Benchmark on a 2,000-file Python repo (8-core laptop): v1 ≈ 11 min → **v2 ≈ 45 s**.

## 🔧 CI/CD Integration

```yaml
# .github/workflows/docs.yml
name: Docs
on: [push]
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install rich pygments pyyaml toml networkx
      - run: python smartrepo_analyzer.py analyze . --no-lint -q -o ./docs-analysis
      - uses: actions/upload-artifact@v4
        with:
          name: project-analysis
          path: docs-analysis/
```

This repository ships its own full pipeline — see [.github/workflows/ci.yml](.github/workflows/ci.yml)
(tests on 3 OSes × Python 3.9–3.13, lint, and a self-analysis smoke test).

## 🖥️ GUI Application

```bash
python smartrepo_analyzer.py gui        # or: python -m gui
```

Features: project picker • live log • progress bar • results viewer with tabs •
searchable file browser • metrics dashboard • dark/light mode • Arabic/English toggle.

Requires tkinter (bundled with Python) and optionally `pillow`.

## 🐛 Troubleshooting

<details>
<summary><b>"Missing dependencies"</b></summary>

```bash
pip install rich pygments pyyaml toml
# or regenerate: python smartrepo_analyzer.py create-requirements
```
</details>

<details>
<summary><b>radon / bandit warnings</b></summary>
These tools are optional. Install them for deeper analysis: <code>pip install radon bandit</code>.
The analyzer never crashes when they're missing.
</details>

<details>
<summary><b>PNG diagrams not generated</b></summary>
Install mermaid-cli: <code>npm install -g @mermaid-js/mermaid-cli</code>. The <code>.mmd</code> files are always produced.
</details>

<details>
<summary><b>Large projects timing out</b></summary>
Use <code>--exclude node_modules/* dist/*</code>, reduce <code>--workers</code>, or analyze subprojects directly.
</details>

## 🗂️ Project Structure

```
smartrepo-analyzer/
├── smartrepo_analyzer.py      # Core engine + CLI
├── deep_analysis.py           # Deep multi-language parsers
├── tool_runner.py             # Batched subprocess helpers
├── *_support.py               # Analysis modules (12 modules)
├── gui/                       # Desktop application (Tkinter)
├── tests/                     # Pytest suite (78+ tests)
└── .github/workflows/ci.yml   # Multi-platform CI
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Quick version:

```bash
pytest tests/          # run the suite
ruff check .           # lint
```

## 📄 License

MIT — see [LICENSE](LICENSE).

---

# العربية

## 📖 جدول المحتويات

- [ما هو SmartRepo؟](#-ما-هو-smartrepo)
- [الميزات](#-الميزات-1)
- [التثبيت](#-التثبيت)
- [البدء السريع](#-البدء-السريع)
- [مرجع الأوامر](#-مرجع-الأوامر)
- [الملفات الناتجة](#-الملفات-الناتجة)
- [درجة الصحة](#-درجة-الصحة)
- [الأداء](#-الأداء)
- [دمج CI/CD](#-دمج-cicd)
- [الواجهة الرسومية](#-الواجهة-الرسومية)
- [حل المشاكل](#-حل-المشاكل)

## 💡 ما هو SmartRepo؟

معظم أدوات التحليل تعطيك أرقامًا فقط. **SmartRepo يعطيك إجابات**: ماذا يفعل المشروع،
أين المخاطر، كيف حالة الكود الصحية، وتوثيقًا جاهزًا للاستهلاك الفوري — سواء للبشر
أو لنماذج الذكاء الاصطناعي.

## ✨ الميزات

| | الميزة |
|---|---|
| 🔬 | **تحليل عميق لكل دالة في كل اللغات** — وليس بايثون فقط: توقيعات الدوال، عدد المعاملات، أرقام الأسطر، و**تعقيد سيكلومي لكل دالة** في Go وRust وJava وKotlin وC# وPHP وRuby وDart وSwift وScala وJS/TS |
| 🛣️ | **خريطة نقاط النهاية REST** — اكتشاف تلقائي من Flask/FastAPI/Express/Spring/Gin |
| 📚 | **نسبة التغطية التوثيقية** — نسبة الرموز العامة الموثقة بـ docstring أو JSDoc أو rustdoc |
| 📝 | **تتبع TODO/FIXME/HACK** عبر المشروع كاملًا |
| 🔥 | **النقاط الساخنة للتعقيد** — الدوال التي يجب إعادة هيكلتها أولًا |
| 🧩 | **استخراج الواجهة البرمجية العامة** — الرموز المصدَّرة بلغة كل مشروع (حروف كبيرة في Go، `pub` في Rust، `export` في JS…) |
| 🔍 | **أكثر من ٢٠ لغة**: Python وJavaScript/TypeScript وGo وRust وJava وDart وPHP وغيرها |
| 🏥 | **درجة صحة من ١٠٠** تجمع التعقيد والاختبارات والأمان والتغطية والتوثيق |
| 🛡️ | **فحص أمني** بأداة bandit بتشغيل دفعات سريعة |
| 🌀 | **تحليل التعقيد السيكلومي** ومؤشر قابلية الصيانة عبر radon |
| 🕸️ | **رسوم تبعيات** بين الملفات وكشف حلقات النداء الدائرية |
| 🤖 | **تلخيص بالذكاء الاصطناعي** عبر OpenAI (`--ai-key` اختياري) |
| 📊 | **مخططات Mermaid**: معمارية، UML، تبعيات، نداءات |
| 🌐 | **ثنائي اللغة بالكامل** (عربي/إنجليزي) في الواجهة والتقارير |
| ⚡ | **تحليل متوازٍ** + تشغيل الأدوات الخارجية على دفعات (أسرع ١٠–٥٠×) |
| 🖥️ | واجهة رسومية عصرية مع وضع ليلي وشاشة ترحيب |
| 📄 | **تقرير HTML مستقل** يعمل بدون إنترنت أو خادم |
| 🧩 | **دعم Monorepo** — يحلل كل مشروع فرعي تلقائيًا |
| 🚫 | تصفية مرنة بأنماط `--exclude` و`--include` |

## 📦 التثبيت

```bash
git clone https://github.com/ALSRKAL/smartrepo-analyzer.git
cd smartrepo-analyzer

python -m venv venv
source venv/bin/activate          # ويندوز: venv\Scripts\activate

pip install -r requirements.txt
```

**إضافات اختيارية** (تُكتشف تلقائيًا إن وُجدت):

```bash
pip install radon bandit pylint flake8     # تحليل أعمق للجودة والأمان
npm install -g @mermaid-js/mermaid-cli     # تحويل المخططات إلى PNG
```

> يتطلب Python 3.9 أو أحدث، ويعمل على ويندوز ولينكس وماك.

## 🚀 البدء السريع

```bash
# تحليل المجلد الحالي
python smartrepo_analyzer.py analyze .

# تحليل مشروع آخر مع مجلد إخراج مخصص
python smartrepo_analyzer.py analyze ./my-project -o ./analysis

# القوة الكاملة: التعقيد + الأمان + كل شيء
python smartrepo_analyzer.py analyze . --complexity --exclude "*.min.js"

# تشغيل الواجهة الرسومية
python smartrepo_analyzer.py gui
```

مثال على جلسة تحليل:

```
  ✓ النوع: Python | الإطار: FastAPI
  ✓ تم تحليل 214 ملفًا (38,412 سطرًا)
  ✓ اكتمل التحليل خلال 6.2 ثانية
  درجة الصحة: 87/100 (A)
```

## 📋 مرجع الأوامر

```
smartrepo_analyzer.py analyze <مسار> [خيارات]
smartrepo_analyzer.py gui                    # الواجهة الرسومية
smartrepo_analyzer.py create-requirements    # إعادة توليد requirements.txt
smartrepo_analyzer.py version                # رقم الإصدار
smartrepo_analyzer.py help                   # المساعدة
```

### خيارات أمر `analyze`

| الخيار | الوصف |
|---|---|
| `-o, --output DIR` | مجلد إخراج مخصص *(الافتراضي: `<المشروع>/smartrepo-analysis`)* |
| `--complexity` | تفعيل تحليل التعقيد وقابلية الصيانة (radon) |
| `--no-lint` | تخطي فحوصات pylint/flake8/eslint |
| `--ai-key KEY` | مفتاح OpenAI للتلخيص الذكي (أو المتغير `SMARTREPO_AI_KEY`) |
| `--exclude PAT…` | أنماط استبعاد مثل `"*.min.js" "docs/*"` |
| `--include PAT…` | قصر التحليل على ملفات مطابقة فقط |
| `--workers N` | عدد خيوط التحليل المتوازي |
| `-v / -q` | إخراج مفصل / وضع صامت |

## 📁 الملفات الناتجة

| الملف | المحتوى |
|---|---|
| 📄 `readme-enhanced.md` | ملف README كامل بالإحصائيات ودليل التشغيل |
| 🌐 `report.html` | تقرير بصري مستقل (افتحه بأي متصفح) |
| 🧠 `ai-summary.json` | ملخص آلي قابل للقراءة — سياق مثالي للنماذج اللغوية |
| 💬 `prompt-ready.md` | توثيق مقسم وجاهز للصق في ChatGPT أو Claude |
| 🗺️ `architecture.mmd` | مخطط معماري Mermaid (+ صورة PNG إن توفّرت mermaid-cli) |
| 🧬 `uml-class-diagram.mmd` | علاقات ووراثة الكلاسات |
| 🕸️ `file-dependency-graph.mmd` | أي ملف يستورد أي ملف |
| 🔁 `call-graph-cycles.txt` | سلاسل النداء الدائرية (روائح كود) |
| 🛡️ `security_report.json` | نتائج bandit حسب الخطورة |
| 🌀 `complexity_report.json` | التعقيد لكل دالة |
| 💡 `recommendations.txt` | توصيات تحسين مرتبة بالأولوية |
| 👥 `contributors.txt` | إحصاءات المساهمين من Git |
| 📝 `summaries/` | معاينات سريعة للملفات الكبيرة |
| ✅ `usage-examples.txt` | أمثلة مستخرجة من docstrings والاختبارات |

## 🏥 درجة الصحة

رقم واحد من ١٠٠ يلخص حالة المشروع:

| العامل | الوزن |
|---|---|
| متوسط التعقيد | حتى −25 |
| نسبة الاختبارات | حتى −18 / مكافأة +3 |
| كثافة مشاكل الفحص | حتى −15 |
| الثغرات الأمنية | حتى −25 |
| تغطية الاختبارات | ±12 |
| مؤشر الصيانة | −8 |

التقديرات: `A+ ≥ 90` · `A ≥ 80` · `B ≥ 70` · `C ≥ 55` · `D ≥ 40` · `F < 40`

## ⚡ الأداء

الإصدار الثاني مصمم للمستودعات الضخمة:

- **تحليل متوازٍ** يستفيد من كل أنوية المعالج
- **تشغيل الأدوات على دفعات** — radon/bandit/pylint تعمل مرة واحدة لكل ~64 ملفًا بدلًا من عملية لكل ملف (**أسرع ١٠–٥٠×**)
- فهرسة رسوم التبعيات بتعقيد O(n·m) بدلًا من O(n²)
- تخطي مبكر لمجلدات `node_modules` و`.git` و`venv` وذاكرات التخزين المؤقت

## 🔧 دمج CI/CD

أضف التحليل إلى خط الإنتاج الخاص بك:

```yaml
- name: Analyze Codebase
  run: |
    pip install -r requirements.txt
    python smartrepo_analyzer.py analyze . --no-lint -q -o ./docs-analysis
- name: Upload Analysis
  uses: actions/upload-artifact@v4
  with:
    name: project-analysis
    path: docs-analysis/
```

وهذا المستودع نفسه يتضمن خط تحقق كامل: اختبارات على ٣ أنظمة تشغيل × بايثون
3.9–3.13، وفحص تنسيقات، وتحليل ذاتي للمستودع.

## 🖥️ الواجهة الرسومية

```bash
python smartrepo_analyzer.py gui
```

تشمل: اختيار المشروع • سجل مباشر • شريط تقدم • عارض نتائج بتبويبات •
متصفح ملفات مع بحث • لوحة إحصائيات • وضع ليلي/نهاري • تبديل عربي/إنجليزي.

## 🐛 حل المشاكل

<details>
<summary><b>خطأ "Missing dependencies"</b></summary>

```bash
pip install rich pygments pyyaml toml
```
</details>

<details>
<summary><b>لم تُولَّد صور PNG للمخططات</b></summary>
ثبّت الأداة: <code>npm install -g @mermaid-js/mermaid-cli</code>. ملفات <code>.mmd</code> تتولد دائمًا على أي حال.
</details>

<details>
<summary><b>مشروع ضخم يستغرق وقتًا طويلًا</b></summary>
استخدم <code>--exclude</code> لتخطي المجلدات غير المهمة، أو حلّل المشاريع الفرعية مباشرة.
</details>

---

<div align="center">

**Made with ⚡ by [ALSRKAL](https://github.com/ALSRKAL)**

⭐ Star this repo if it saved you time!

</div>
