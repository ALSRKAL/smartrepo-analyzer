"""SmartRepo Analyzer — desktop GUI entry point.

الواجهة الرسومية لأداة SmartRepo: اختيار المشروع، تشغيل التحليل،
عرض النتائج والتصدير، بواجهة عربية/إنجليزية ووضع ليلي.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk

try:
    from .lang import tr, set_lang
    from .theme import set_theme, get_theme
    from .components import (
        AnalysisOptions,
        Dashboard,
        FileBrowser,
        ProjectPicker,
        ResultsViewer,
        ThreadedAnalyzer,
    )
except ImportError:  # direct execution fallback
    from lang import tr, set_lang  # type: ignore
    from theme import set_theme, get_theme  # type: ignore
    from components import (  # type: ignore
        AnalysisOptions,
        Dashboard,
        FileBrowser,
        ProjectPicker,
        ResultsViewer,
        ThreadedAnalyzer,
    )

APP_TITLE = "SmartRepo Analyzer"
SPLASH_DURATION_MS = 1800

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

LOGO_PATH = Path(__file__).resolve().parent.parent / "image" / "logo.png"


class SplashScreen(tk.Toplevel):
    """Brief branded splash shown at startup."""

    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        w, h = 480, 280
        sw, sh = parent.winfo_screenwidth(), parent.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.configure(bg="#16181d")
        if HAS_PIL and LOGO_PATH.exists():
            try:
                img = Image.open(LOGO_PATH).resize((96, 96))
                self.logo = ImageTk.PhotoImage(img)
                tk.Label(self, image=self.logo, bg="#16181d").pack(pady=(24, 8))
            except Exception:
                tk.Label(self, text="⚡", font=("Arial", 40), fg="#90caf9",
                         bg="#16181d").pack(pady=(20, 4))
        else:
            tk.Label(self, text="⚡", font=("Arial", 40), fg="#90caf9",
                     bg="#16181d").pack(pady=(20, 4))
        tk.Label(self, text=APP_TITLE, font=("Arial", 22, "bold"),
                 fg="#fff", bg="#16181d").pack()
        tk.Label(self, text=tr("splash_features"), font=("Arial", 11),
                 fg="#94a3b8", bg="#16181d", justify="left").pack(pady=12)


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1150x780")
        self.minsize(900, 620)
        self.theme_mode = "light"
        self.project_path: str | None = None
        self._analyzer: ThreadedAnalyzer | None = None
        self.apply_theme()
        self.after(100, self.show_splash)

    # ------------------------------------------------------------ lifecycle
    def show_splash(self):
        splash = SplashScreen(self)
        self.withdraw()
        self.after(SPLASH_DURATION_MS, lambda: self.start_main(splash))

    def start_main(self, splash):
        splash.destroy()
        self.deiconify()
        self.init_ui()

    # ---------------------------------------------------------------- theming
    def apply_theme(self):
        set_theme(self.theme_mode)
        self.configure(bg=get_theme()["bg"])

    def switch_theme(self):
        self.theme_mode = "dark" if self.theme_mode == "light" else "light"
        self.apply_theme()
        self.init_ui(refresh=True)

    def switch_lang(self, lang):
        set_lang(lang)
        self.init_ui(refresh=True)

    # --------------------------------------------------------------------- UI
    def init_ui(self, refresh=False):
        if refresh:
            for widget in self.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    continue
                widget.destroy()
        theme = get_theme()

        topbar = tk.Frame(self, bg=theme["bg"])
        topbar.pack(fill="x", side="top")

        try:
            logo_label = self._logo(topbar, theme)
        except Exception:
            logo_label = tk.Label(topbar, text="⚡ SR", font=("Arial", 15, "bold"),
                                  fg=theme["accent"], bg=theme["bg"])
        logo_label.pack(side="left", padx=12, pady=6)

        lang_btn = ttk.Menubutton(topbar, text=f"🌐 {tr('language')}")
        menu = tk.Menu(lang_btn, tearoff=0)
        menu.add_command(label=tr("arabic"), command=lambda: self.switch_lang("ar"))
        menu.add_command(label=tr("english"), command=lambda: self.switch_lang("en"))
        lang_btn["menu"] = menu
        lang_btn.pack(side="right", padx=10, pady=6)

        ttk.Button(topbar, text=tr("dark_mode") if self.theme_mode == "light"
                   else tr("light_mode"), command=self.switch_theme)\
            .pack(side="right", padx=10, pady=6)

        main = tk.Frame(self, bg=theme["bg"])
        main.pack(fill="both", expand=True)

        picker = ProjectPicker(main, on_pick=self._on_pick_project)
        picker.pack(fill="x", padx=16, pady=(14, 4))

        options = AnalysisOptions(main)
        options.pack(fill="x", padx=16)

        buttons_row = tk.Frame(main, bg=theme["bg"])
        buttons_row.pack(fill="x", padx=16, pady=8)

        log_box = scrolledtext.ScrolledText(buttons_row.master, height=9,
                                            font=("Consolas", 10),
                                            bg=theme.get("log_bg", "#fff"),
                                            fg=theme.get("log_fg", "#222"),
                                            state="disabled")
        log_box.pack(fill="both", expand=True, padx=16, pady=4)
        self.log_box = log_box

        progress = ttk.Progressbar(main, mode="indeterminate")
        progress.pack(fill="x", padx=16, pady=(0, 4))
        self.progress = progress
        status_label = tk.Label(main, text="", anchor="w", bg=theme["bg"],
                                fg=theme["fg"], font=("Arial", 10))
        status_label.pack(fill="x", padx=18)
        self.status_label = status_label

        start_btn = ttk.Button(buttons_row, text=f"▶ {tr('start_analysis')}",
                               command=self.start_analysis)
        results_btn = ttk.Button(buttons_row, text=f"📄 {tr('results')}",
                                 command=self.show_results)
        files_btn = ttk.Button(buttons_row, text=f"🔍 {tr('search')}",
                               command=self.show_files)
        dash_btn = ttk.Button(buttons_row, text=f"📊 {tr('dashboard')}",
                              command=self.show_dashboard)
        for b in (start_btn, results_btn, files_btn, dash_btn):
            b.pack(side="left", padx=(0, 10), pady=2)

        self.options_ref = options
        self.picker_ref = picker

    def _logo(self, topbar, theme):
        if not HAS_PIL or not LOGO_PATH.exists():
            raise FileNotFoundError(LOGO_PATH)
        img = Image.open(LOGO_PATH).resize((30, 30))
        self._logo_img = ImageTk.PhotoImage(img)
        return tk.Label(topbar, image=self._logo_img, bg=theme["bg"])

    # --------------------------------------------------------------- actions
    def _on_pick_project(self, path):
        self.project_path = path

    def _output_dir(self):
        out = self.options_ref.output_var.get().strip()
        if not out and self.project_path:
            out = os.path.join(self.project_path, "smartrepo-analysis")
        return out

    def start_analysis(self):
        if not self.project_path:
            messagebox.showerror(tr("error"), tr("select_project_first"))
            return
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.config(state="disabled")
        self.progress.start(12)
        self.status_label.config(text="⏳ …")

        def log(msg):
            self.log_box.config(state="normal")
            self.log_box.insert(tk.END, msg)
            self.log_box.see(tk.END)
            self.log_box.config(state="disabled")

        def done(success):
            self.progress.stop()
            self.status_label.config(
                text="✅ " + tr("analysis_done") if success else "❌ " + tr("analysis_failed"))

        try:
            self._analyzer = ThreadedAnalyzer(
                self.project_path,
                self._output_dir(),
                self.options_ref.complexity_var.get(),
                log_callback=log,
                done_callback=done,
                ai_key=self.options_ref.ai_key_var.get() or None,
                no_lint=self.options_ref.no_lint_var.get(),
            )
            self._analyzer.start()
            self._poll_logs()
        except RuntimeError as e:
            self.progress.stop()
            messagebox.showerror(tr("error"), str(e))

    def _poll_logs(self):
        if self._analyzer:
            self._analyzer.poll_logs()
            self.after(120, self._poll_logs)

    def show_results(self):
        out = self._output_dir()
        if not os.path.exists(out):
            messagebox.showerror(tr("error"), tr("no_results"))
            return
        win = tk.Toplevel(self)
        win.title(tr("results"))
        win.geometry("960x640")
        ResultsViewer(win, out).pack(fill="both", expand=True)

    def show_files(self):
        if not self.project_path:
            messagebox.showerror(tr("error"), tr("select_project_first"))
            return
        out = self._output_dir()
        if not os.path.exists(out):
            messagebox.showerror(tr("error"), tr("no_results"))
            return
        win = tk.Toplevel(self)
        win.title(tr("search"))
        win.geometry("900x600")
        FileBrowser(win, self.project_path, out).pack(fill="both", expand=True)

    def show_dashboard(self):
        out = self._output_dir()
        if not os.path.exists(out):
            messagebox.showerror(tr("error"), tr("no_results"))
            return
        win = tk.Toplevel(self)
        win.title(tr("dashboard"))
        win.geometry("640x480")
        Dashboard(win, out).pack(fill="both", expand=True)


def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
