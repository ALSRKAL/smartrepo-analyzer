"""Deep multi-language code analysis engine.

محرك التحليل العميق متعدد اللغات: يستخرج لكل ملف الدوال والكلاسات
بتوقيعاتها وأرقام أسطرها، ويحسب التعقيد السيكلومي **لكل دالة** في كل
اللغات (وليس بايثون فقط)، مع اكتشاف نقاط النهاية (REST endpoints)،
التعليقات المعلقة (TODO/FIXME)، ونسبة التوصيل التوثيقي.

Design notes
------------
* Python uses the ``ast`` module — ground truth.
* Brace languages (JS/TS, Go, Rust, Java, Kotlin, C#, C/C++, PHP, Swift,
  Scala, Dart) share one lightweight scanner that tracks braces while
  skipping string/comment states, so keywords inside strings never fool it.
* Ruby is handled with a dedicated ``def … end`` scanner.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class FunctionInfo:
    """A function/method with its measured properties."""

    name: str
    line: int = 0
    args: int = 0
    complexity: int = 1
    kind: str = "function"          # function | method | constructor | endpoint
    exported: bool = False
    documented: bool = False


@dataclass
class ClassInfo:
    """A class/struct/interface/trait declaration."""

    name: str
    line: int = 0
    bases: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    kind: str = "class"             # class | struct | interface | trait | impl


@dataclass
class ParsedSource:
    """Uniform result for every language."""

    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    complexity: int = 1
    docstring: str = ""
    functions_detail: List[FunctionInfo] = field(default_factory=list)
    classes_detail: List[ClassInfo] = field(default_factory=list)
    todos: int = 0
    endpoints: List[str] = field(default_factory=list)

    def finalize(self) -> "ParsedSource":
        self.functions = [f.name for f in self.functions_detail]
        self.classes = [c.name for c in self.classes_detail]
        self.complexity = max(
            sum(f.complexity for f in self.functions_detail), 1
        ) if self.functions_detail else 1
        return self


TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _count_todos(text: str) -> int:
    return len(TODO_RE.findall(text))


def _doc_above(lines: List[str], idx: int, patterns: tuple) -> bool:
    """True when the line above ``idx`` looks like documentation."""
    j = idx - 1
    while j >= 0 and not lines[j].strip():
        j -= 1
    if j < 0:
        return False
    stripped = lines[j].lstrip()
    return any(stripped.startswith(p) for p in patterns)


def _strip_inline_comment(line: str, comment_token: str) -> str:
    pos = line.find(comment_token)
    return line if pos == -1 else line[:pos]


# ---------------------------------------------------------------------------
# Generic brace-language engine
# ---------------------------------------------------------------------------

# Decision points shared by all language scanners.
# - simple keywords get \b on BOTH sides
# - Rust `match x { a => .. }` handled without a trailing \b (=> is not a word char)
# - short-circuit operators (&&, ||, ??) count as decisions, like lizard/radon do
# - bare '?' is deliberately excluded (nullable types in C#/TS/Kotlin would skew counts)
DECISION_KEYWORDS = re.compile(
    r"\b(?:if|else\s+if|elif|for|foreach|while|do|case|catch|switch)\b"
    r"|match\b[^=\n]*=>"
    r"|\?\?"
    r"|(?:&&|\|\|)"
)

FUNC_PATTERNS_BY_LANG: Dict[str, "re.Pattern"] = {
    # Go: func name( / func (recv) Name(
    ".go": re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(([^)]*)\)"),
    # Rust: fn name(
    ".rs": re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+([A-Za-z_]\w*)\s*[<(]\s*(?:<[^>]*>\s*)?\(?([^)]*)"),
    # Java / Kotlin / C#: modifiers Type name(args) {
    ".java": re.compile(r"^\s*(?:@\w+\s+)*(?:public|private|protected|static|final|abstract|override|synchronized|default|native|\s)*\s*[\w<>\[\],?.\s]+\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*(?:throws [\w,\s]+)?\{"),
    ".kt": re.compile(r"^\s*(?:@\w+:?\s*)*(?:public|private|protected|internal|open|override|abstract|final|suspend|inline|operator|\s)*\s*fun\s+(?:[A-Za-z_][\w.]*\.)?([A-Za-z_]\w*)\s*(?:<[^>]*>)?\s*\(([^)]*)\)"),
    ".cs": re.compile(r"^\s*(?:@\w+\s+)*(?:public|private|protected|internal|static|virtual|override|abstract|async|sealed|partial|\s)*\s*[\w<>\[\],?.\s]+\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*(?:where\s+[\w:\s,<]+)?\{"),
    # PHP: function name( / methods with visibility
    ".php": re.compile(r"^\s*(?:abstract\s+|final\s+|public\s+|private\s+|protected\s+|static\s+)*function\s+&?([A-Za-z_]\w*)\s*\(([^)]*)\)"),
    # C/C++: type name(args) {  — conservative, requires opening brace on same line
    ".c": re.compile(r"^\s*(?:static\s+|inline\s+|const\s+|unsigned\s+|signed\s+|struct\s+|enum\s+)*[\w\*]+\s+\**([A-Za-z_]\w*)\s*\(([^;)]*(?:\([^)]*\))?[^;)]*)\)\s*\{"),
    # Swift: func name(
    ".swift": re.compile(r"^\s*(?:@\w+\s+)*(?:public|private|fileprivate|internal|open|static|class|override|mutating|discarding|\s)*\s*func\s+([A-Za-z_]\w*)\s*(?:<[^>]*>)?\s*\(([^)]*)\)"),
    # Scala: def name(
    ".scala": re.compile(r"^\s*(?:override\s+|final\s+|private\s+|protected\s+)*def\s+([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*\(([^)]*)\)"),
    # Dart: ReturnType methodName(args) {  (methods are lowerCamelCase)
    ".dart": re.compile(r"^\s*(?:@\w+\s*)*(?:const\s+)?(?:Future<[^>]+>|Stream<[^>]+>|void|int|double|String|bool|num|Widget|var|final|[A-Z][\w<>?, ]*)\s+_?([a-z_]\w*)(?:<[^>]*>)?\s*\(([^)]*)\)"),
}

CLASS_PATTERNS_BY_LANG: Dict[str, List[tuple]] = {
    ".go": [(re.compile(r"^\s*type\s+([A-Z]\w*)\s+struct\b"), "struct"),
            (re.compile(r"^\s*type\s+(\w+)\s+interface\b"), "interface")],
    ".rs": [(re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?struct\s+(\w+)"), "struct"),
            (re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?enum\s+(\w+)"), "enum"),
            (re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?trait\s+(\w+)"), "trait")],
    ".java": [(re.compile(r"^\s*(?:@\w+\s+)*(?:public|private|protected|abstract|final|static|sealed|\s)*\s*(?:class|record)\s+(\w+)(?:<[^>]*>)?(?:\s+extends\s+([\w.<>]+))?(?:\s+implements\s+([\w.,<>\s]+))?"), "class"),
              (re.compile(r"^\s*(?:public|private|\s)*\s*interface\s+(\w+)"), "interface"),
              (re.compile(r"^\s*(?:public|\s)*\s*enum\s+(\w+)"), "enum")],
    ".kt": [(re.compile(r"^\s*(?:@\w+:?\s*)*(?:public|private|internal|open|abstract|sealed|data|enum|\s)*\s*class\s+(\w+)(?:<[^>]*>)?(?:\s*\([^)]*\))?(?:\s*:\s*([\w.,<>\s()]+))?"), "class"),
            (re.compile(r"^\s*interface\s+(\w+)"), "interface"),
            (re.compile(r"^\s*object\s+(\w+)"), "object")],
    ".cs": [(re.compile(r"^\s*(?:@\w+\s+)*(?:public|private|protected|internal|static|abstract|sealed|partial|\s)*\s*(?:class|record)\s+(\w+)(?:<[^>]*>)?(?:\s*:\s*([\w.,<>\s{}]+))?"), "class"),
            (re.compile(r"^\s*(?:public|internal|\s)*\s*interface\s+(\w+)"), "interface")],
    ".php": [(re.compile(r"^\s*(?:abstract\s+|final\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?"), "class"),
             (re.compile(r"^\s*interface\s+(\w+)"), "interface"),
             (re.compile(r"^\s*trait\s+(\w+)"), "trait")],
    ".c": [(re.compile(r"^\s*(?:typedef\s+)?struct\s+(\w+)"), "struct"),
           (re.compile(r"^\s*typedef\s+struct[^{]*\{?\s*\}?(\w+);"), "struct"),
           (re.compile(r"^\s*enum\s+(\w+)"), "enum")],
    ".swift": [(re.compile(r"^\s*(?:@\w+\s+)*(?:public|private|internal|open|final|\s)*(?:class|actor)\s+(\w+)(?:<[^>]*>)?(?:\s*:\s*([\w,&\s<>]+))?"), "class"),
               (re.compile(r"^\s*(?:public|internal|open|\s)*(?:struct)\s+(\w+)"), "struct"),
               (re.compile(r"^\s*(?:public|internal|open|\s)*(?:protocol)\s+(\w+)"), "protocol")],
    ".scala": [(re.compile(r"^\s*(?:abstract\s+|sealed\s+|case\s+)*class\s+(\w+)"), "class"),
               (re.compile(r"^\s*(?:sealed\s+)?trait\s+(\w+)"), "trait"),
               (re.compile(r"^\s*object\s+(\w+)"), "object")],
}

IMPORT_PATTERNS_BY_LANG: Dict[str, List[re.Pattern]] = {
    ".rs": [re.compile(r"^\s*use\s+([\w:{} ,:*]+);")],
    ".java": [re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+);")],
    ".kt": [re.compile(r"^\s*import\s+([\w.*]+)")],
    ".cs": [re.compile(r"^\s*using\s+(?:static\s+)?([\w.]+)\s*;")],
    ".php": [re.compile(r"^\s*use\s+([\w\\\\]+)(?:\s+as\s+\w+)?\s*;")],
    ".c": [re.compile(r'^\s*#\s*include\s*[<"]([^">]+)[">]')],
    ".swift": [re.compile(r"^\s*import\s+(\w+)")],
    ".scala": [re.compile(r"^\s*import\s+([\w.{}, ]+)")],
}

DOC_COMMENT_PREFIXES = ("///", "/**", "*", "#", "--", '"""', "'''")

ENDPOINT_PATTERNS: List[tuple] = [
    # Flask / FastAPI / Sanic decorators: @app.get("/x"), @router.post('/x')
    (re.compile(r"@[\w.]+\.(get|post|put|delete|patch|head|options)\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
     lambda m: f"{m.group(1).upper()} {m.group(2)}"),
    # Express-style: app.get("/x"), router.post(...)
    (re.compile(r"\b(app|router|api)\.(get|post|put|delete|patch|all)\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
     lambda m: f"{m.group(2).upper()} {m.group(3)}"),
    # Spring annotations
    (re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping\s*\(\s*(?:value\s*=\s*)?[\"']([^\"']+)[\"']", re.I),
     lambda m: f"{m.group(1).upper()} {m.group(2)}"),
    # Gin / Echo Go routers
    (re.compile(r"\.\s*(GET|POST|PUT|DELETE|PATCH)\s*\(\s*\"([^\"]+)\""),
     lambda m: f"{m.group(1)} {m.group(2)}"),
]


def _extract_endpoints(text: str) -> List[str]:
    found: List[str] = []
    for pattern, fmt in ENDPOINT_PATTERNS:
        for m in pattern.finditer(text):
            ep = fmt(m)
            if ep not in found:
                found.append(ep)
    return found[:40]


def _brace_scan(lines: List[str], lang_ext: str) -> ParsedSource:
    """Shared analyzer for brace languages.

    Tracks brace depth while ignoring string/char/comment regions so that
    decision keywords or braces inside strings are not miscounted.
    """
    result = ParsedSource()
    func_re = FUNC_PATTERNS_BY_LANG.get(lang_ext)
    class_specs = CLASS_PATTERNS_BY_LANG.get(lang_ext, [])
    import_res = IMPORT_PATTERNS_BY_LANG.get(lang_ext, [])

    depth = 0
    in_block_comment = False
    in_import_block = False          # Go's import ( ... )
    current_fn: Optional[tuple] = None   # (start_depth, FunctionInfo, body_lines)
    fn_stack: List[tuple] = []

    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        depth_before_line = depth   # enclosing depth before this line's braces

        # --- comment/string-aware character walk -------------------------
        code_chars = []
        i, n = 0, len(line)
        in_string = False
        quote = ""
        while i < n:
            ch = line[i]
            if in_block_comment:
                if line.startswith("*/", i):
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
                continue
            if in_string:
                if ch == "\\":
                    i += 2
                    continue
                if ch == quote:
                    in_string = False
                i += 1
                continue
            if line.startswith("//", i):
                break
            if line.startswith("/*", i):
                in_block_comment = True
                i += 2
                continue
            if ch in "\"'`":
                in_string = True
                quote = ch
                i += 1
                continue
            code_chars.append(ch)
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            i += 1

        code_line = "".join(code_chars)

        if lang_ext == ".go":
            if re.match(r"^\s*import\s*\(", line):
                in_import_block = True
            elif in_import_block and ")" in line:
                in_import_block = False
            elif in_import_block:
                m = re.search(r'"([^"]+)"', line)
                if m:
                    result.imports.append(m.group(1).split("/")[-1])

        # --- function detection ------------------------------------------
        if func_re is not None:
            m = func_re.match(line)
            if m and m.group(1) not in CONTROL_ONLY_NAMES:
                name = m.group(1)
                args_str = (m.group(2) or "").strip()
                nargs = _count_args(args_str, lang_ext)
                documented = _doc_above(lines, lineno - 1, DOC_COMMENT_PREFIXES)
                exported = _is_exported(name, lang_ext, line)
                info = FunctionInfo(
                    name=name, line=lineno, args=nargs,
                    kind="method" if depth_before_line > 0 else "function",
                    exported=exported, documented=documented,
                )
                # start_depth = enclosing depth (before the fn's own `{`)
                fn_stack.append((depth_before_line, info))
                result.functions_detail.append(info)

        # --- class detection ---------------------------------------------
        for cre, kind in class_specs:
            cm = cre.match(line)
            if cm:
                bases = []
                if cm.lastindex and cm.lastindex >= 2 and cm.group(2):
                    bases = [b.strip().split("<")[0] for b in re.split(r"[,&]", cm.group(2)) if b.strip()]
                result.classes_detail.append(ClassInfo(
                    name=cm.group(1), line=lineno, bases=bases[:5], kind=kind))
                break

        # --- imports ------------------------------------------------------
        for ire in import_res:
            im = ire.match(line)
            if im:
                mod = im.group(1).strip()
                if mod:
                    if lang_ext in (".java", ".kt", ".cs", ".scala"):
                        # keep package + top type: java.util.List -> java.util
                        segs = mod.split(".")
                        result.imports.append(".".join(segs[:2]) if len(segs) > 1 else segs[0])
                    else:
                        result.imports.append(mod.split(".")[0].split("::")[0])
                break

        # --- decision counting inside innermost open function -------------
        if fn_stack and code_line:
            decisions = len(DECISION_KEYWORDS.findall(code_line))
            if decisions:
                fn_stack[-1][1].complexity += decisions

        # close finished functions
        while fn_stack and depth <= fn_stack[-1][0]:
            fn_stack.pop()
        if lang_ext == ".go" and depth == 0:
            fn_stack.clear()

        # TODO/FIXME markers (raw line; strings rarely contain these)
        result.todos += len(TODO_RE.findall(line))

    # functions still open at EOF (unbalanced) simply keep their counts
    result.endpoints = _extract_endpoints("\n".join(lines))
    return result.finalize()


def _count_args(args_str: str, lang_ext: str) -> int:
    if not args_str:
        return 0
    parts = [p for p in re.split(r",", args_str) if p.strip()]
    return len(parts)


KEYWORD_NAMES = {
    "if", "else", "for", "foreach", "while", "switch", "case", "catch",
    "return", "new", "do", "try", "finally", "using", "lock", "with",
}
CONTROL_ONLY_NAMES = {"if", "else", "for", "foreach", "while", "do",
                      "switch", "case", "catch", "return", "try"}


def _is_exported(name: str, lang_ext: str, line: str) -> bool:
    if lang_ext == ".go":
        return name[:1].isupper()
    if lang_ext == ".rs":
        return line.lstrip().startswith("pub")
    if lang_ext in (".java", ".cs", ".php"):
        if re.match(r"\s*(public|protected)", line):
            return True
        if re.match(r"\s*private|internal|fileprivate", line):
            return False
        # top-level plain functions (PHP/C) default to exported
        return True
    if lang_ext == ".swift":
        return bool(re.search(r"\b(public|open)\b", line))
    if lang_ext == ".kt":
        return not re.search(r"\b(private|internal|protected)\b", line)
    return "export" in line


# ---------------------------------------------------------------------------
# Ruby scanner (indentation-free, end-based)
# ---------------------------------------------------------------------------

RUBY_DEF_RE = re.compile(r"^\s*def\s+(?:self\.)?([A-Za-z_]\w*[?!]?)(?:\s*\(([^)]*)\))?")
RUBY_CLASS_RE = re.compile(r"^\s*(?:class|module)\s+([A-Z]\w*)(?:\s*<\s*([\w:]+))?")


def _ruby_scan(lines: List[str]) -> ParsedSource:
    result = ParsedSource()
    def_depth: List[int] = []     # block-level at which each open `def` started
    level = 0
    openers = re.compile(r"\b(def|class|module|if|unless|while|until|case|do|begin)\b|\{\s*$")
    enders = re.compile(r"(?:^|\s)end(?:\s|$|[.;])")

    for lineno, raw in enumerate(lines, start=1):
        line = _strip_inline_comment(raw, "#").rstrip()

        dm = RUBY_DEF_RE.match(raw)
        if dm:
            result.functions_detail.append(FunctionInfo(
                name=dm.group(1), line=lineno,
                args=len([a for a in (dm.group(2) or "").split(",") if a.strip()]),
                kind="method",
                exported=not dm.group(1).startswith("_"),
                documented=_doc_above(lines, lineno - 1, DOC_COMMENT_PREFIXES),
            ))
            def_depth.append(level)

        cm = RUBY_CLASS_RE.match(raw)
        if cm:
            base = [cm.group(2)] if cm.group(2) else []
            result.classes_detail.append(ClassInfo(cm.group(1), lineno, bases=base))

        # attribute decisions to the most recently opened function
        if result.functions_detail:
            decisions = len(DECISION_KEYWORDS.findall(line))
            if decisions:
                result.functions_detail[-1].complexity += decisions

        if "require_relative" in raw:
            m = re.search(r"require_relative\s+['\"]([^'\"]+)", raw)
            if m:
                result.imports.append(m.group(1).split("/")[-1])
        elif "require" in raw:
            m = re.search(r"require\s+['\"]?([\w/-]+)", raw)
            if m and m.group(1) != "relative":
                result.imports.append(m.group(1).split("/")[-1])

        opens = len(openers.findall(line)) + (1 if dm else 0)
        ends = len(enders.findall(raw))
        level += opens - ends
        while def_depth and level <= def_depth[-1]:
            def_depth.pop()

    result.endpoints = _extract_endpoints("\n".join(lines))
    result.todos = len(TODO_RE.findall("\n".join(lines)))
    return result.finalize()


# ---------------------------------------------------------------------------
# JavaScript / TypeScript (regex tuned for modern syntax)
# ---------------------------------------------------------------------------

_JS_FUNC_RES = [
    # export default async function Name(...) / function* name(...)
    re.compile(r"^\s*(export\s+)?(default\s+)?(async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(([^)]*)\)"),
    # const x = (a, b) => ...  / const x = async a => ...
    re.compile(r"^\s*(export\s+)?(?:default\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::\s*[\w<>\[\]|]+)?\s*=\s*(async\s+)?\(([^)]*)\)\s*(?::\s*[\w<>|]+)?\s*=>"),
    # const x = a => ... (single param, no parens)
    re.compile(r"^\s*(export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?([A-Za-z_$][\w$]*)\s*=>"),
    # object/class method:   name(args) {
    re.compile(r"^\s+(?:static\s+|async\s+|get\s+|set\s+|\*|(?:public|private|protected|readonly)\s+)*([A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\s*\(([^)]*)\)\s*(?::\s*[\w<>|.\[\]]+)?\s*\{"),
]

_JS_CLASS_RE = re.compile(
    r"^\s*(export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)"
    r"(?:\s+extends\s+([\w$.]+))?(?:\s+implements\s+([\w,\s.]+))?"
)

_TS_TYPE_RES = [
    re.compile(r"^\s*(export\s+)?interface\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"^\s*(export\s+)?type\s+([A-Za-z_$][\w$]*)\s*="),
    re.compile(r"^\s*(export\s+)?enum\s+([A-Za-z_$][\w$]*)"),
]


def _js_scan(lines: List[str], text: str) -> ParsedSource:
    result = ParsedSource()
    control = {"if", "for", "while", "switch", "catch", "return"}

    for lineno, raw in enumerate(lines, start=1):
        line = _strip_inline_comment(raw, "//")

        # ---- imports (package name only; local paths ignored) ----
        for im in re.finditer(
            r"(?:^\s*import[\s\S]*?from\s+|^\s*import\s+|\brequire\s*\(\s*)['\"]([^'\"]+)['\"]",
            line,
        ):
            src = im.group(1)
            if not src.startswith((".", "/")):
                pkg = src.lstrip("@").split("/")[0]
                result.imports.append(pkg)

        # ---- TS types/interfaces/enums ----
        for tre in _TS_TYPE_RES:
            tm = tre.match(line)
            if tm:
                result.classes_detail.append(ClassInfo(tm.group(2), lineno, kind="type"))
                break

        # ---- classes ----
        cm = _JS_CLASS_RE.match(line)
        if cm:
            bases = [b for b in (cm.group(2),) if b]
            result.classes_detail.append(ClassInfo(cm.group(2), lineno, bases=bases))
            continue

        # ---- functions ----
        for fi, fre in enumerate(_JS_FUNC_RES):
            fm = fre.search(line)
            if not fm:
                continue
            if fi == 0:
                name, args, exp = fm.group(4), fm.group(5), bool(fm.group(1))
                kind_extra = ""
            elif fi == 1:
                name, args, exp = fm.group(2), fm.group(3), bool(fm.group(1))
                kind_extra = ""
            elif fi == 2:
                name, args, exp = fm.group(2), "", bool(fm.group(1))
                kind_extra = ""
            else:
                name, args = fm.group(1), fm.group(2)
                if name in control or name[0].isdigit():
                    continue
                exp = "export" in line
                kind_extra = ""
            if name in control or name in ("typeof", "await", "new"):
                continue
            nargs = len([a for a in (args or "").split(",") if a.strip()])
            kind = "endpoint" if re.search(r"\((?:req|res|request|response)\b", args or "") else "function"
            result.functions_detail.append(FunctionInfo(
                name=name, line=lineno, args=nargs,
                kind=kind,
                exported=exp,
                documented=_doc_above(lines, lineno - 1, ("/**", "*")),
            ))
            break

        # per-line decision attribution to the most recent function
        # keywords + short-circuit operators (||, &&, ??) — matching radon/lizard
        clean = _strip_inline_comment(line, "//")
        if result.functions_detail:
            hits = re.findall(r"\b(?:if|for|while|case|catch)\b|\?\?|&&|\|\|", clean)
            if hits:
                result.functions_detail[-1].complexity += len(hits)

    result.imports = sorted(set(result.imports))
    result.endpoints = _extract_endpoints(text)
    result.todos = len(TODO_RE.findall(text))
    return result.finalize()


# ---------------------------------------------------------------------------
# Dart & PHP quick scanners reuse brace engine where possible
# ---------------------------------------------------------------------------

_DART_FUNC_RE = re.compile(r"^\s*(?:@\w+\s+)*(?:Future<[^>]+>|Stream<[^>]+>|void|int|double|String|bool|num|var|final|Widget|[A-Z][\w<>?]*)\s+_?([a-z_]\w*)\s*(?:<[^>]*>)?\s*\(([^)]*)\)")
_DART_CLASS_RE = re.compile(r"^\s*(?:abstract\s+)?(?:sealed\s+)?(?:base\s+)?class\s+(\w+)(?:<[^>]*>)?(?:\s+(?:extends|implements|with)\s+([\w,<>\s]+))?")


def _dart_scan(lines: List[str], text: str) -> ParsedSource:
    result = _brace_scan(lines, ".dart")  # Dart-specific function pattern
    # refine with Dart-specific class/import patterns
    result.classes_detail = []
    for lineno, raw in enumerate(lines, start=1):
        cm = _DART_CLASS_RE.match(raw)
        if cm:
            bases = [b.strip() for b in re.split(r"[,]", cm.group(2) or "") if b.strip()]
            result.classes_detail.append(ClassInfo(cm.group(1), lineno, bases=bases[:4]))
        im = re.match(r"^\s*import\s+['\"](?:package:([^/'\"]+)/|([^:'\"]+))", raw)
        if im:
            pkg = im.group(1) or im.group(2) or ""
            if pkg and "/" not in pkg and "." in pkg or pkg.startswith("dart:"):
                result.imports.append(pkg.split(":")[-1].split(".")[0])
    seen = set()
    result.imports = [i for i in result.imports if not (i in seen or seen.add(i))]
    result.endpoints = _extract_endpoints(text)
    result.todos = len(TODO_RE.findall(text))
    return result.finalize()


# ---------------------------------------------------------------------------
# Python (AST — richest extraction)
# ---------------------------------------------------------------------------

PY_ENDPOINT_DECORATORS = re.compile(r"\.(get|post|put|patch|delete|route)\s*\(", re.I)


def _python_scan(content: str) -> ParsedSource:
    result = ParsedSource()
    import_set: set = set()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return result.finalize()

    lines = content.splitlines()
    module_doc = ast.get_docstring(tree) or ""

    # Decision nodes counted exactly like radon (verified by cross-testing):
    #   If/For/While/AsyncFor/ExceptHandler/Assert/IfExp → +1
    #   comprehension → +1 plus +1 per filter clause
    #   BoolOp → +(values-1); NOT descended into when inside an `assert`
    #   match → +1 per non-wildcard case
    decision_nodes = (
        ast.If, ast.For, ast.While, ast.AsyncFor,
        ast.ExceptHandler, ast.Assert, ast.IfExp,
    )

    def _is_wildcard_case(case_node) -> bool:
        pat = getattr(case_node, "pattern", None)
        return (
            pat is not None
            and pat.__class__.__name__ == "MatchAs"
            and getattr(pat, "pattern", "sentinel") is None
            and getattr(pat, "name", None) in (None, "_")
        )

    def local_complexity(fn_node) -> int:
        score = 1
        stack = list(ast.iter_child_nodes(fn_node))
        while stack:
            node = stack.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            if isinstance(node, decision_nodes):
                score += 1
                if isinstance(node, ast.Assert):
                    continue  # radon ignores boolean ops inside assertions
            elif isinstance(node, ast.comprehension):
                # the generator itself + every filter clause counts (radon parity)
                score += 1 + len(node.ifs)
            elif isinstance(node, ast.BoolOp):
                score += max(len(node.values) - 1, 0)
            elif node.__class__.__name__ == "Match":
                score += sum(
                    1 for cs in getattr(node, "cases", []) if not _is_wildcard_case(cs)
                )
            stack.extend(ast.iter_child_nodes(node))
        return score

    def arg_count(fn_node) -> int:
        a = fn_node.args
        total = len(a.args) + len(a.posonlyargs) + len(a.kwonlyargs)
        if a.vararg:
            total += 1
        if a.kwarg:
            total += 1
        return total

    def endpoint_from_decorators(fn_node) -> Optional[str]:
        for dec in getattr(fn_node, "decorator_list", []):
            seg = ast.unparse(dec) if hasattr(ast, "unparse") else ""
            m = PY_ENDPOINT_DECORATORS.search(seg)
            path_m = re.search(r"[\"']([^\"']+)[\"']", seg)
            if m:
                verb = {"route": "ANY"}.get(m.group(1).lower(), m.group(1).upper())
                return f"{verb} {path_m.group(1) if path_m else ''}".rstrip()
        return None

    def visit(node, in_class=False):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = "async " if isinstance(child, ast.AsyncFunctionDef) else ""
                ep = endpoint_from_decorators(child)
                result.functions_detail.append(FunctionInfo(
                    name=prefix + child.name,
                    line=child.lineno,
                    args=arg_count(child),
                    complexity=local_complexity(child),
                    kind="endpoint" if ep else ("method" if in_class else "function"),
                    exported=not child.name.startswith("_"),
                    documented=bool(ast.get_docstring(child)),
                ))
                if ep:
                    result.endpoints.append(ep)
                visit(child, in_class=in_class)
            elif isinstance(child, ast.ClassDef):
                bases = [b.id for b in child.bases if isinstance(b, ast.Name)]
                result.classes_detail.append(ClassInfo(
                    name=child.name, line=child.lineno, bases=bases,
                    methods=[m.name for m in child.body
                             if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))],
                ))
                visit(child, in_class=True)
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                if isinstance(child, ast.Import):
                    for alias in child.names:
                        import_set.add(alias.name)
                        import_set.add(alias.name.split(".")[0])
                else:
                    if child.module:
                        import_set.add(child.module)
                        import_set.add(child.module.split(".")[0])
            else:
                visit(child, in_class=in_class)

    visit(tree)
    result.imports = sorted(import_set)
    # prefer the module docstring; otherwise surface the first symbol's
    # so every file summary carries meaningful context
    if not module_doc:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                doc = ast.get_docstring(node)
                if doc:
                    module_doc = doc
                    break
    result.docstring = module_doc[:300]
    result.todos = _count_todos(content)
    return result.finalize()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

BRACE_LANGS = {".go", ".rs", ".java", ".kt", ".cs", ".c", ".cpp", ".cc",
               ".h", ".hpp", ".php", ".swift", ".scala"}
DART_EXTS = {".dart"}
RUBY_EXTS = {".rb"}
JS_EXTS = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}


def parse_source(ext: str, language: str, content: str) -> ParsedSource:
    """Dispatch to the right deep parser based on file extension."""
    lines = content.splitlines()

    if ext == ".py":
        parsed = _python_scan(content)
    elif ext in JS_EXTS:
        parsed = _js_scan(lines, content)
    elif ext in RUBY_EXTS:
        parsed = _ruby_scan(lines)
    elif ext in DART_EXTS:
        parsed = _dart_scan(lines, content)
    elif ext in BRACE_LANGS:
        key = ext if ext in FUNC_PATTERNS_BY_LANG else (
            ".c" if ext in (".h", ".hpp", ".cc", ".cpp") else ".java")
        parsed = _brace_scan(lines, key)
    else:
        parsed = ParsedSource(todos=_count_todos(content)).finalize()

    return parsed
