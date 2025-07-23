<img width="932" height="1006" alt="image" src="https://github.com/user-attachments/assets/02352890-9599-404f-970a-23b7ccfe28d9" />



# SmartRepo Analyzer - Setup and Usage Guide

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the SmartRepo Analyzer
git clone https://github.com/ALSRKAL/smartrepo-analyzer.git
cd smartrepo-analyzer

# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
python smartrepo_analyzer.py create-requirements
pip install -r requirements.txt

# Optional: Install Mermaid CLI for diagram generation
npm install -g @mermaid-js/mermaid-cli
```

### 2. Basic Usage

```bash
# Analyze a project in current directory
python smartrepo_analyzer.py analyze .

# Analyze a specific project
python smartrepo_analyzer.py analyze ./my-project

# Specify custom output directory
python smartrepo_analyzer.py analyze ./my-project --output ./analysis-results

# Verbose output
python smartrepo_analyzer.py analyze ./my-project --verbose
```

## 📋 Command Reference

### `analyze` - Main Analysis Command

```bash
python smartrepo_analyzer.py analyze <project_path> [OPTIONS]
```

**Arguments:**
- `project_path`: Path to the project directory to analyze

**Options:**
- `--output`, `-o`: Custom output directory for generated files
- `--verbose`, `-v`: Enable verbose logging
- `--help`, `-h`: Show help for this command

### `create-requirements` - Setup Helper

```bash
python smartrepo_analyzer.py create-requirements
```

Creates a `requirements.txt` file with all necessary dependencies.

## 📊 Example Analysis Sessions

### Analyzing a Node.js Project

```bash
$ python smartrepo_analyzer.py analyze ./my-express-app

🚀 SmartRepo Analyzer v1.0.0
📁 Analyzing project: /path/to/my-express-app
🔍 Starting project analysis...
✓ Project type: Node.js
✓ Framework: Express.js
✓ Analyzed 24 files
📝 Generating documentation...
✅ Documentation generation complete!

📊 ANALYSIS COMPLETE
============================================================
Project: my-express-app
Type: Node.js
Languages: JavaScript, TypeScript
Files analyzed: 24
Total lines: 3,847
Functions: 156
Classes: 12
Average complexity: 3.2

📁 Generated files:
  ✓ readme-enhanced.md (8,234 bytes)
  ✓ architecture.mmd (1,456 bytes)
  ✓ ai-summary.json (12,789 bytes)
  ✓ prompt-ready.md (4,567 bytes)

🎉 All files saved to: /path/to/my-express-app/smartrepo-analysis
```

### Analyzing a Python Django Project

```bash
$ python smartrepo_analyzer.py analyze ./django-blog --output ./blog-analysis

🚀 SmartRepo Analyzer v1.0.0
📁 Analyzing project: /path/to/django-blog
🔍 Starting project analysis...
✓ Project type: Python
✓ Framework: Django
✓ Analyzed 42 files
✓ Architecture PNG generated
📝 Generating documentation...
✅ Documentation generation complete!

📊 ANALYSIS COMPLETE
============================================================
Project: django-blog
Type: Python
Languages: Python
Files analyzed: 42
Total lines: 5,234
Functions: 89
Classes: 23
Average complexity: 2.8

📁 Generated files:
  ✓ readme-enhanced.md (9,876 bytes)
  ✓ architecture.mmd (2,134 bytes)
  ✓ architecture.png (45,678 bytes)
  ✓ ai-summary.json (18,456 bytes)
  ✓ prompt-ready.md (6,789 bytes)

🎉 All files saved to: ./blog-analysis
```

### Analyzing a Flutter Project

```bash
$ python smartrepo_analyzer.py analyze ./flutter_todo_app

🚀 SmartRepo Analyzer v1.0.0
📁 Analyzing project: /path/to/flutter_todo_app
🔍 Starting project analysis...
✓ Project type: Flutter
✓ Framework: Flutter
✓ Analyzed 18 files
📝 Generating documentation...
✅ Documentation generation complete!

📊 ANALYSIS COMPLETE
============================================================
Project: flutter_todo_app
Type: Flutter
Languages: Dart
Files analyzed: 18
Total lines: 2,156
Functions: 67
Classes: 15
Average complexity: 2.1

📁 Generated files:
  ✓ readme-enhanced.md (6,543 bytes)
  ✓ architecture.mmd (1,234 bytes)
  ✓ ai-summary.json (8,765 bytes)
  ✓ prompt-ready.md (3,456 bytes)

🎉 All files saved to: /path/to/flutter_todo_app/smartrepo-analysis
```

## 📁 Generated Output Files

After analysis, SmartRepo creates these files in the output directory:

### 1. `readme-enhanced.md`
- **Purpose**: Complete, professionally formatted README
- **Contents**: Project overview, architecture, dependencies, installation steps, usage examples
- **Features**: Auto-generated badges, metrics, and documentation

### 2. `architecture.mmd` & `architecture.png`
- **Purpose**: Visual project architecture
- **Format**: Mermaid diagram (.mmd) and PNG image (.png)
- **Shows**: Component relationships, file organization, data flow

### 3. `ai-summary.json`
- **Purpose**: Machine-readable project analysis
- **Format**: Structured JSON with complete metadata
- **Use cases**: AI processing, automated documentation, project indexing

### 4. `prompt-ready.md`
- **Purpose**: AI-optimized documentation chunks
- **Contents**: Context-rich summaries for LLM consumption
- **Features**: Keyword tagging, natural language descriptions

## 🔧 Advanced Configuration

### Custom File Filtering

Edit the `_should_analyze_file` method to customize which files are analyzed:

```python
def _should_analyze_file(self, file_path: Path) -> bool:
    # Add custom ignore patterns
    custom_ignore = ['*.generated.ts', 'temp/', 'cache/']
    
    if any(pattern in str(file_path) for pattern in custom_ignore):
        return False
        
    return file_path.suffix in self.supported_extensions
```

### Adding New Language Support

Add new languages to the `supported_extensions` dictionary:

```python
self.supported_extensions = {
    # Existing languages...
    '.scala': 'Scala',
    '.clj': 'Clojure',
    '.hs': 'Haskell',
    '.elm': 'Elm'
}
```

### Custom Analysis Rules

Extend the analyzer with project-specific rules:

```python
def _analyze_custom_framework(self, path: Path) -> Dict[str, Any]:
    """Custom analysis for specific frameworks"""
    # Implementation for custom framework detection
    pass
```

## 🐛 Troubleshooting

### Common Issues

**1. "Missing dependencies" error**
```bash
# Solution: Install required packages
python smartrepo_analyzer.py create-requirements
pip install -r requirements.txt
```

**2. "Permission denied" when writing files**
```bash
# Solution: Check directory permissions or use --output flag
python smartrepo_analyzer.py analyze ./project --output ~/analysis
```

**3. "Mermaid CLI not found" warning**
```bash
# Solution: Install Mermaid CLI (optional)
npm install -g @mermaid-js/mermaid-cli
```

**4. Large projects timing out**
```bash
# Solution: The analyzer automatically skips large binary files
# For very large codebases, consider filtering directories
```

### Debug Mode

For detailed debugging, modify the main function to include traceback:

```python
except Exception as e:
    print(f"❌ Error during analysis: {e}")
    if args.verbose:
        import traceback
        traceback.print_exc()
```

## 🔄 Integration Examples

### CI/CD Pipeline Integration

```yaml
# GitHub Actions example
- name: Analyze Codebase
  run: |
    pip install -r requirements.txt
    python smartrepo_analyzer.py analyze . --output ./docs/analysis
    
- name: Upload Analysis
  uses: actions/upload-artifact@v3
  with:
    name: code-analysis
    path: ./docs/analysis/
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
python smartrepo_analyzer.py analyze . --output ./analysis
git add ./analysis/readme-enhanced.md
```

### VS Code Integration

Add to `.vscode/tasks.json`:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Analyze Project",
            "type": "shell",
            "command": "python",
            "args": ["smartrepo_analyzer.py", "analyze", ".", "--output", "./analysis"],
            "group": "build"
        }
    ]
}
```

## 📈 Performance Tips

1. **Large Projects**: Use specific output directories to avoid conflicts
2. **Network Dependencies**: Run analysis offline after initial dependency installation
3. **Memory Usage**: For very large codebases (>100k files), consider breaking into modules
4. **Speed**: Use SSD storage for faster file I/O operations

## 🤝 Contributing

1. **Adding Language Support**: Implement parser in `_analyze_<language>_file` methods
2. **Custom Analyzers**: Extend the `CodeAnalyzer` class with new detection methods
3. **Output Formats**: Add new generators in `DocumentationGenerator` class
4. **Visualization**: Enhance diagram generation with additional chart types

## 📄 License

SmartRepo Analyzer is released under the MIT License. See LICENSE file for details.

---

**Ready to analyze your first project?**

```bash
python smartrepo_analyzer.py analyze . --output ./my-analysis
```

---

**This project is ready for publishing on GitHub at [ALSRKAL](https://github.com/ALSRKAL).** 

## ⚡️ أوضاع التحليل (سريع أم شامل؟)

يمكنك اختيار وضع التحليل المناسب حسب حاجتك:

### 1. التحليل السريع (موصى به للمشاريع الكبيرة)

- أسرع بكثير، يتجاوز تحليل التعقيد (radon)
- مناسب إذا كنت تريد نظرة عامة سريعة

```bash
python smartrepo_analyzer.py analyze . --output ./smartrepo-analysis
```

### 2. التحليل الشامل مع التعقيد

- أبطأ، لكنه يعطيك تفاصيل تعقيد الشيفرة (code complexity)
- يظهر شريط تقدم ووقت متبقي أثناء تحليل التعقيد

```bash
python smartrepo_analyzer.py analyze . --output ./smartrepo-analysis --complexity
```

> **ملاحظة:**
> - إذا فعّلت خيار `--complexity` سيظهر شريط تقدم خاص لتحليل التعقيد.
> - إذا لم تفعّله، سيتجاوز التحليل هذه الخطوة لتسريع العملية.

## 🛠️ متطلبات الأدوات الخارجية

للحصول على أفضل النتائج، تأكد من تثبيت الأدوات التالية:

- **radon** (لتحليل التعقيد):
  ```bash
  pip install radon
  ```
- **bandit** (لتحليل الأمان):
  ```bash
  pip install bandit
  ```

إذا لم تكن مثبتة، سيظهر لك خطأ يوضح الأداة الناقصة. 
