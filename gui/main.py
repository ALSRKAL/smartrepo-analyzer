import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
from lang import tr, set_lang
from theme import set_theme, get_theme
from components import ProjectPicker, AnalysisOptions, ThreadedAnalyzer, ResultsViewer, FileBrowser, Dashboard

APP_TITLE = "SmartRepo Analyzer"
SPLASH_DURATION = 2500
LOGO_PATH = os.path.join(os.path.dirname(__file__), '../image/logo.png')

class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.geometry("500x300+500+250")
        self.configure(bg="#222")
        try:
            logo_img = Image.open(LOGO_PATH)
            logo_img = logo_img.resize((120, 120))
            self.logo = ImageTk.PhotoImage(logo_img)
            logo_label = tk.Label(self, image=self.logo, bg="#222")
            logo_label.pack(pady=20)
        except Exception:
            logo_label = tk.Label(self, text="SmartRepo", font=("Arial", 32), fg="#fff", bg="#222")
            logo_label.pack(pady=20)
        tk.Label(self, text=APP_TITLE, font=("Arial", 22, "bold"), fg="#fff", bg="#222").pack()
        tk.Label(self, text=tr('splash_features'), font=("Arial", 12), fg="#ccc", bg="#222", justify="left").pack(pady=10)

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x800")
        self.minsize(900, 600)
        self.theme_mode = 'light'
        self.lang = 'ar'
        self.apply_theme()
        self.after(10, self.show_splash)

    def show_splash(self):
        splash = SplashScreen(self)
        self.withdraw()
        self.after(SPLASH_DURATION, lambda: self.start_main(splash))

    def start_main(self, splash):
        splash.destroy()
        self.deiconify()
        self.init_ui()

    def apply_theme(self):
        set_theme(self.theme_mode)
        theme = get_theme()
        self.configure(bg=theme['bg'])

    def switch_theme(self):
        self.theme_mode = 'dark' if self.theme_mode == 'light' else 'light'
        self.apply_theme()
        self.init_ui(refresh=True)

    def switch_lang(self, lang):
        set_lang(lang)
        self.lang = lang
        self.init_ui(refresh=True)

    def init_ui(self, refresh=False):
        if refresh:
            for widget in self.winfo_children():
                widget.destroy()
        theme = get_theme()
        # شريط علوي
        topbar = tk.Frame(self, bg=theme['bg'])
        topbar.pack(fill='x', side='top')
        lang_btn = ttk.Menubutton(topbar, text=tr('language'))
        lang_menu = tk.Menu(lang_btn, tearoff=0)
        lang_menu.add_command(label=tr('arabic'), command=lambda: self.switch_lang('ar'))
        lang_menu.add_command(label=tr('english'), command=lambda: self.switch_lang('en'))
        lang_btn['menu'] = lang_menu
        lang_btn.pack(side='right', padx=10, pady=5)
        theme_btn = ttk.Button(topbar, text=tr('dark_mode') if self.theme_mode=='light' else tr('light_mode'), command=self.switch_theme)
        theme_btn.pack(side='right', padx=10, pady=5)
        try:
            logo_img = Image.open(LOGO_PATH)
            logo_img = logo_img.resize((32, 32))
            self.logo = ImageTk.PhotoImage(logo_img)
            logo_label = tk.Label(topbar, image=self.logo, bg=theme['bg'])
            logo_label.pack(side='left', padx=10)
        except Exception:
            logo_label = tk.Label(topbar, text="SR", font=("Arial", 16, "bold"), fg=theme['accent'], bg=theme['bg'])
            logo_label.pack(side='left', padx=10)
        # محتوى رئيسي
        main = tk.Frame(self, bg=theme['bg'])
        main.pack(fill='both', expand=True)
        # اختيار مجلد المشروع
        def on_pick_project(path):
            self.project_path = path
        picker = ProjectPicker(main, on_pick=on_pick_project)
        picker.pack(pady=10)
        # إعدادات التحليل
        options = AnalysisOptions(main)
        options.pack(pady=10)
        # سجل حي
        log_box = tk.Text(main, height=8, width=80, state='disabled')
        log_box.pack(pady=10)
        # شريط التقدم (مبدئي)
        progress = ttk.Progressbar(main, length=400, mode='indeterminate')
        progress.pack(pady=10)
        # زر بدء التحليل
        def start_analysis():
            if not hasattr(self, 'project_path') or not self.project_path:
                messagebox.showerror(tr('error'), tr('select_project'))
                return
            log_box.config(state='normal')
            log_box.delete('1.0', tk.END)
            log_box.config(state='disabled')
            progress.start(10)
            def log_callback(msg):
                log_box.config(state='normal')
                log_box.insert(tk.END, msg)
                log_box.see(tk.END)
                log_box.config(state='disabled')
            def done_callback(success):
                progress.stop()
                if success:
                    messagebox.showinfo(tr('success'), tr('results'))
                else:
                    messagebox.showerror(tr('error'), tr('logs'))
            analyzer = ThreadedAnalyzer(
                self.project_path,
                options.output_var.get(),
                options.complexity_var.get(),
                log_callback,
                done_callback
            )
            analyzer.start()
        start_btn = ttk.Button(main, text=tr('start_analysis'), command=start_analysis)
        start_btn.pack(pady=10)
        # زر عرض النتائج
        def show_results():
            output_dir = options.output_var.get() or os.path.join(self.project_path, 'smartrepo-analysis')
            if not os.path.exists(output_dir):
                messagebox.showerror(tr('error'), tr('results'))
                return
            win = tk.Toplevel(self)
            win.title(tr('results'))
            win.geometry('900x600')
            ResultsViewer(win, output_dir).pack(fill='both', expand=True)
        results_btn = ttk.Button(main, text=tr('results'), command=show_results)
        results_btn.pack(pady=5)
        # زر تصفح الملفات
        def show_files():
            output_dir = options.output_var.get() or os.path.join(self.project_path, 'smartrepo-analysis')
            if not os.path.exists(output_dir):
                messagebox.showerror(tr('error'), tr('results'))
                return
            win = tk.Toplevel(self)
            win.title(tr('search'))
            win.geometry('900x600')
            FileBrowser(win, self.project_path, output_dir).pack(fill='both', expand=True)
        files_btn = ttk.Button(main, text=tr('search'), command=show_files)
        files_btn.pack(pady=5)
        # زر لوحة الإحصائيات
        def show_dashboard():
            output_dir = options.output_var.get() or os.path.join(self.project_path, 'smartrepo-analysis')
            if not os.path.exists(output_dir):
                messagebox.showerror(tr('error'), tr('results'))
                return
            win = tk.Toplevel(self)
            win.title(tr('dashboard'))
            win.geometry('600x400')
            Dashboard(win, output_dir).pack(fill='both', expand=True)
        dash_btn = ttk.Button(main, text=tr('dashboard'), command=show_dashboard)
        dash_btn.pack(pady=5)

if __name__ == "__main__":
    app = MainApp()
    app.mainloop() 