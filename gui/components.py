"""Reusable GUI components for SmartRepo Analyzer.

مكونات الواجهة الرسومية: اختيار المشروع، الخيارات، التحليل المترابط،
عارض النتائج، متصفح الملفات ولوحة الإحصائيات.
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import tkinter as tk
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Package-relative imports with a fallback so the module also works when
# executed directly (python gui/components.py) or from a frozen bundle.
try:
    from .lang import tr
    from .theme import get_theme
except ImportError:  # pragma: no cover
    from lang import tr  # type: ignore
    from theme import get_theme  # type: ignore

# Make the repository root importable regardless of CWD.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from smartrepo_analyzer import SmartRepoAnalyzer
except ImportError as e:  # pragma: no cover - only when run outside repo
    SmartRepoAnalyzer = None
    _IMPORT_ERROR = e


class ProjectPicker(ttk.Frame):
    """Directory chooser row (entry + browse button)."""

    def __init__(self, parent, on_pick):
        super().__init__(parent)
        self.on_pick = on_pick
        self.dir_var = tk.StringVar()
        self.init_ui()

    def init_ui(self):
        ttk.Label(self, text=tr("select_project")).pack(side="left", padx=5)
        entry = ttk.Entry(self, textvariable=self.dir_var, width=52)
        entry.pack(side="left", padx=5)
        entry.bind("<Return>", lambda _e: self.on_pick(self.dir_var.get()))
        ttk.Button(self, text="📁…", command=self.pick_dir).pack(side="left", padx=5)

    def pick_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.dir_var.set(path)
            self.on_pick(path)


class AnalysisOptions(ttk.Frame):
    """Output directory, AI key and analysis toggles."""

    def __init__(self, parent):
        super().__init__(parent)
        self.output_var = tk.StringVar()
        self.ai_key_var = tk.StringVar(value=os.environ.get("SMARTREPO_AI_KEY", ""))
        self.complexity_var = tk.BooleanVar(value=False)
        self.no_lint_var = tk.BooleanVar(value=False)
        self.init_ui()

    def init_ui(self):
        ttk.Label(self, text=tr("output_dir")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(self, textvariable=self.output_var, width=42).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(self, text="📁…", command=self.pick_output).grid(row=0, column=2, padx=5, pady=2)
        ttk.Label(self, text=tr("ai_key")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        key_entry = ttk.Entry(self, textvariable=self.ai_key_var, width=42, show="•")
        key_entry.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Checkbutton(self, text=tr("enable_complexity"), variable=self.complexity_var)\
            .grid(row=2, column=0, sticky="w", padx=5, pady=2)

    def pick_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_var.set(path)


class ThreadedAnalyzer:
    """Runs the analyzer off the UI thread; streams stdout to a queue."""

    def __init__(self, project_path, output_dir, enable_complexity,
                 log_callback, done_callback, ai_key=None, no_lint=False):
        if SmartRepoAnalyzer is None:
            raise RuntimeError(f"Cannot import analyzer engine: {_IMPORT_ERROR}")
        self.project_path = project_path
        self.output_dir = output_dir or None
        self.enable_complexity = enable_complexity
        self.ai_key = ai_key or None
        self.no_lint = no_lint
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self._log_callback = log_callback
        self._done_callback = done_callback
        self.thread: threading.Thread | None = None

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def poll_logs(self):
        """Drain queued messages into the UI (call from the main thread)."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._log_callback(msg)
        except queue.Empty:
            pass

    def run(self):
        sink = _QueueWriter(self.log_queue)
        ok = False
        try:
            app = SmartRepoAnalyzer()
            with redirect_stdout(sink), redirect_stderr(sink):
                result = app.run(
                    self.project_path,
                    output_dir=self.output_dir,
                    enable_complexity=self.enable_complexity,
                    ai_api_key=self.ai_key,
                    run_linters=not self.no_lint,
                    quiet=True,
                )
            ok = result is not None or True  # monorepo mode returns None on success
        except Exception as e:
            self.log_queue.put(f"\n❌ {e}\n")
        finally:
            self._done_callback(ok)


class _QueueWriter:
    """File-like object that forwards writes into a queue."""

    def __init__(self, q: "queue.Queue"):
        self.q = q

    def write(self, msg):
        if msg and msg.strip():
            self.q.put(msg.rstrip() + "\n")

    def flush(self):
        pass


class ResultsViewer(ttk.Frame):
    """Tabbed viewer for README / diagrams / AI summary artifacts."""

    def __init__(self, parent, output_dir):
        super().__init__(parent)
        self.output_dir = output_dir
        self.tabs: ttk.Notebook | None = None
        self.files: list = []
        self.init_ui()

    def init_ui(self):
        self.tabs = ttk.Notebook(self)
        self.files = []
        readme_tab = scrolledtext.ScrolledText(self.tabs, wrap="word", font=("Arial", 12))
        readme_path = os.path.join(self.output_dir, "readme-enhanced.md")
        if os.path.exists(readme_path):
            with open(readme_path, encoding="utf-8") as f:
                readme_tab.insert("1.0", f.read())
            self.files.append(("readme", readme_path))
        else:
            readme_tab.insert("1.0", tr("no_results"))
        self.tabs.add(readme_tab, text=f"📄 {tr('readme')}")

        png_path = os.path.join(self.output_dir, "architecture.png")
        mmd_path = os.path.join(self.output_dir, "architecture.mmd")
        if os.path.exists(png_path):
            img_tab = tk.Frame(self.tabs)
            try:
                from PIL import Image, ImageTk
                img = Image.open(png_path)
                img.thumbnail((860, 520))
                self._imgtk = ImageTk.PhotoImage(img)
                tk.Label(img_tab, image=self._imgtk).pack(expand=True)
            except Exception:
                tk.Label(img_tab, text="(image preview unavailable)").pack()
            self.tabs.add(img_tab, text=f"📊 {tr('diagrams')}")
        elif os.path.exists(mmd_path):
            mmd_tab = scrolledtext.ScrolledText(self.tabs, wrap="word", font=("Consolas", 11))
            with open(mmd_path, encoding="utf-8") as f:
                mmd_tab.insert("1.0", f.read())
            self.tabs.add(mmd_tab, text=f"📊 {tr('diagrams')}")
            self.files.append(("diagrams", mmd_path))

        for name, label in (
            ("ai-summary.json", tr("summaries")),
            ("report.html", "HTML"),
            ("recommendations.txt", "💡"),
        ):
            p = os.path.join(self.output_dir, name)
            if os.path.exists(p):
                tab = scrolledtext.ScrolledText(self.tabs, wrap="word", font=("Consolas", 11))
                with open(p, encoding="utf-8") as fh:
                    tab.insert("1.0", fh.read())
                self.tabs.add(tab, text=label)
                self.files.append((name, p))

        self.tabs.pack(fill="both", expand=True)
        ttk.Button(self, text=f"⬇ {tr('export')}", command=self.export_current).pack(pady=4)

    def export_current(self):
        sel = self.tabs.select()
        idx = self.tabs.index(sel) if sel else 0
        if idx >= len(self.files):
            return
        _, file_path = self.files[idx]
        ext = os.path.splitext(file_path)[1]
        save_path = filedialog.asksaveasfilename(defaultextension=ext,
                                                 filetypes=[("All Files", "*.*")])
        if save_path:
            try:
                with open(file_path, "rb") as src, open(save_path, "wb") as dst:
                    dst.write(src.read())
                messagebox.showinfo(tr("success"), tr("export"))
            except OSError as e:
                messagebox.showerror(tr("error"), str(e))


class FileBrowser(ttk.Frame):
    """Searchable project file tree with per-file summaries."""

    def __init__(self, parent, project_path, output_dir):
        super().__init__(parent)
        self.project_path = project_path
        self.output_dir = output_dir
        self.init_ui()

    def init_ui(self):
        search_var = tk.StringVar()
        entry = ttk.Entry(self, textvariable=search_var, width=44)
        entry.pack(pady=6)
        entry.insert(0, "")
        entry.configure(justify="left")

        tree = ttk.Treeview(self, height=14)
        tree.pack(fill="both", expand=True, padx=6)

        summary_box = scrolledtext.ScrolledText(self, height=9, font=("Arial", 11),
                                                state="disabled")
        summary_box.pack(fill="x", pady=6, padx=6)

        all_files = []
        skip = {"node_modules", "__pycache__", ".git", "venv", ".venv",
                "smartrepo-analysis", "dist", "build"}
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
            for fname in files:
                rel = os.path.relpath(os.path.join(root, fname), self.project_path)
                all_files.append(rel.replace(os.sep, "/"))

        for rel in sorted(all_files)[:4000]:
            tree.insert("", "end", rel, text=rel)

        def show_summary(rel):
            safe = rel.replace("/", "__")
            candidates = [
                os.path.join(self.output_dir, "summaries", f"summary_{safe}.txt"),
                os.path.join(self.output_dir, "summaries", f"summary_{os.path.basename(rel)}.txt"),
            ]
            summary_box.config(state="normal")
            summary_box.delete("1.0", tk.END)
            found = next((c for c in candidates if os.path.exists(c)), None)
            if found:
                with open(found, encoding="utf-8") as f:
                    summary_box.insert("1.0", f.read())
            else:
                full = os.path.join(self.project_path, rel)
                if os.path.exists(full) and os.path.getsize(full) < 100_000:
                    try:
                        with open(full, encoding="utf-8", errors="replace") as f:
                            head = "".join(f.readlines()[:40])
                        summary_box.insert("1.0", head)
                    except OSError:
                        pass
            summary_box.config(state="disabled")

        def on_select(_event):
            sel = tree.selection()
            if sel:
                show_summary(sel[0])
        tree.bind("<<TreeviewSelect>>", on_select)

        def on_search(*_):
            q = search_var.get().lower()
            tree.delete(*tree.get_children())
            for rel in all_files:
                if not q or q in rel.lower():
                    tree.insert("", "end", rel, text=rel)
        search_var.trace_add("write", on_search)


class Dashboard(ttk.Frame):
    """Key metrics panel rendered from ai-summary.json."""

    def __init__(self, parent, output_dir):
        super().__init__(parent)
        self.output_dir = output_dir
        self.init_ui()

    def init_ui(self):
        stats, health = {}, {}
        path = os.path.join(self.output_dir, "ai-summary.json")
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                stats = data.get("metrics", {})
                health = data.get("health", {})
            except (OSError, json.JSONDecodeError):
                pass

        title = ttk.Label(self, text=f"📊 {tr('dashboard')}", font=("Arial", 16, "bold"))
        title.pack(pady=(12, 6))

        if health.get("score") is not None:
            color = {"A": "#16a34a", "B": "#65a30d", "C": "#d97706"}.get(
                str(health.get("grade", "?"))[0], "#dc2626")
            tk.Label(self, text=f"{health['score']}/100 ({health.get('grade', '')})",
                     font=("Arial", 26, "bold"), fg=color).pack(pady=4)
            tk.Label(self, text=tr("health_score"), font=("Arial", 10)).pack()

        grid = ttk.Frame(self)
        grid.pack(pady=10)
        icons = {"total_files": "📄", "total_lines": "📝", "total_functions": "ƒ",
                 "total_classes": "🧱", "average_complexity": "🌀"}
        for i, (k, v) in enumerate(stats.items()):
            if not isinstance(v, (int, float, str)):
                continue
            r, c = divmod(i, 3)
            card = tk.Frame(grid, bd=1, relief="solid", padx=12, pady=8)
            card.grid(row=r, column=c, padx=8, pady=6, sticky="nsew")
            icon = icons.get(k, "•")
            label = k.replace("_", " ").title()
            val = f"{v:,}" if isinstance(v, int) else v
            tk.Label(card, text=f"{icon} {label}", font=("Arial", 9)).pack()
            tk.Label(card, text=str(val), font=("Arial", 13, "bold")).pack()
