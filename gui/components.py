import tkinter as tk
from tkinter import ttk, filedialog
from lang import tr
from theme import get_theme
import threading
import queue
import time
import sys
sys.path.append('..')
from smartrepo_analyzer import SmartRepoAnalyzer
from tkinter import scrolledtext
from PIL import Image, ImageTk
import markdown
import io
import base64
import os
from tkinter import filedialog, messagebox
import json

class ProjectPicker(ttk.Frame):
    def __init__(self, parent, on_pick):
        super().__init__(parent)
        self.on_pick = on_pick
        self.dir_var = tk.StringVar()
        self.init_ui()
    def init_ui(self):
        theme = get_theme()
        label = ttk.Label(self, text=tr('select_project'))
        label.pack(side='left', padx=5)
        entry = ttk.Entry(self, textvariable=self.dir_var, width=50)
        entry.pack(side='left', padx=5)
        btn = ttk.Button(self, text='...', command=self.pick_dir)
        btn.pack(side='left', padx=5)
    def pick_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.dir_var.set(path)
            self.on_pick(path)

class AnalysisOptions(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.output_var = tk.StringVar()
        self.ai_key_var = tk.StringVar()
        self.complexity_var = tk.BooleanVar(value=True)
        self.init_ui()
    def init_ui(self):
        theme = get_theme()
        ttk.Label(self, text=tr('output_dir')).grid(row=0, column=0, sticky='w', padx=5, pady=2)
        out_entry = ttk.Entry(self, textvariable=self.output_var, width=40)
        out_entry.grid(row=0, column=1, padx=5, pady=2)
        out_btn = ttk.Button(self, text='...', command=self.pick_output)
        out_btn.grid(row=0, column=2, padx=5, pady=2)
        ttk.Label(self, text=tr('ai_key')).grid(row=1, column=0, sticky='w', padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ai_key_var, width=40).grid(row=1, column=1, columnspan=2, padx=5, pady=2)
        ttk.Checkbutton(self, text=tr('enable_complexity'), variable=self.complexity_var).grid(row=2, column=0, columnspan=3, sticky='w', padx=5, pady=2)
    def pick_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_var.set(path) 

class ThreadedAnalyzer:
    def __init__(self, project_path, output_dir, enable_complexity, log_callback, done_callback):
        self.project_path = project_path
        self.output_dir = output_dir
        self.enable_complexity = enable_complexity
        self.log_callback = log_callback
        self.done_callback = done_callback
        self.thread = None
    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
    def run(self):
        try:
            analyzer = SmartRepoAnalyzer()
            # إعادة توجيه stdout مؤقتًا
            old_stdout = sys.stdout
            sys.stdout = self
            analyzer.run(self.project_path, self.output_dir, self.enable_complexity)
            sys.stdout = old_stdout
            self.done_callback(success=True)
        except Exception as e:
            self.log_callback(f'Error: {e}')
            self.done_callback(success=False)
    def write(self, msg):
        self.log_callback(msg)
    def flush(self):
        pass 

class ResultsViewer(ttk.Frame):
    def __init__(self, parent, output_dir):
        super().__init__(parent)
        self.output_dir = output_dir
        self.tabs = None
        self.files = []
        self.init_ui()
    def init_ui(self):
        theme = get_theme()
        self.tabs = ttk.Notebook(self)
        self.files = []
        # README
        readme_tab = scrolledtext.ScrolledText(self.tabs, wrap='word', font=("Arial", 12))
        readme_path = os.path.join(self.output_dir, 'readme-enhanced.md')
        if os.path.exists(readme_path):
            with open(readme_path, encoding='utf-8') as f:
                md = f.read()
                readme_tab.insert('1.0', md)
            self.files.append(('readme', readme_path))
        self.tabs.add(readme_tab, text=tr('readme'))
        # Mermaid/PNG
        mmd_path = os.path.join(self.output_dir, 'architecture.mmd')
        png_path = os.path.join(self.output_dir, 'architecture.png')
        if os.path.exists(png_path):
            img_tab = tk.Frame(self.tabs)
            img = Image.open(png_path)
            img = img.resize((600, 400))
            self.imgtk = ImageTk.PhotoImage(img)
            label = tk.Label(img_tab, image=self.imgtk)
            label.pack()
            self.tabs.add(img_tab, text=tr('diagrams'))
            self.files.append(('diagrams', png_path))
        elif os.path.exists(mmd_path):
            mmd_tab = scrolledtext.ScrolledText(self.tabs, wrap='word', font=("Arial", 12))
            with open(mmd_path, encoding='utf-8') as f:
                mmd = f.read()
                mmd_tab.insert('1.0', mmd)
            self.tabs.add(mmd_tab, text=tr('diagrams'))
            self.files.append(('diagrams', mmd_path))
        # AI Summary
        summary_path = os.path.join(self.output_dir, 'ai-summary.json')
        if os.path.exists(summary_path):
            summary_tab = scrolledtext.ScrolledText(self.tabs, wrap='word', font=("Arial", 12))
            with open(summary_path, encoding='utf-8') as f:
                summary_tab.insert('1.0', f.read())
            self.tabs.add(summary_tab, text=tr('summaries'))
            self.files.append(('summaries', summary_path))
        self.tabs.pack(fill='both', expand=True)
        # زر تصدير
        export_btn = ttk.Button(self, text=tr('export'), command=self.export_current)
        export_btn.pack(pady=5)
    def export_current(self):
        idx = self.tabs.index(self.tabs.select())
        if idx < len(self.files):
            _, file_path = self.files[idx]
            ext = os.path.splitext(file_path)[1]
            save_path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=[('All Files', '*.*')])
            if save_path:
                try:
                    with open(file_path, 'rb') as src, open(save_path, 'wb') as dst:
                        dst.write(src.read())
                    messagebox.showinfo(tr('success'), tr('export'))
                except Exception as e:
                    messagebox.showerror(tr('error'), str(e)) 

class FileBrowser(ttk.Frame):
    def __init__(self, parent, project_path, output_dir):
        super().__init__(parent)
        self.project_path = project_path
        self.output_dir = output_dir
        self.init_ui()
    def init_ui(self):
        theme = get_theme()
        # شريط البحث
        search_var = tk.StringVar()
        search_entry = ttk.Entry(self, textvariable=search_var, width=40)
        search_entry.pack(pady=5)
        # شجرة الملفات
        tree = ttk.Treeview(self)
        tree.pack(fill='both', expand=True)
        # ملخص الملف
        summary_box = scrolledtext.ScrolledText(self, height=8, font=("Arial", 11))
        summary_box.pack(fill='x', pady=5)
        # بناء الشجرة
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self.project_path)
                tree.insert('', 'end', rel_path, text=rel_path)
        def on_select(event):
            sel = tree.selection()
            if sel:
                rel_path = sel[0]
                summary_path = os.path.join(self.output_dir, 'file-summaries', rel_path + '.md')
                summary_box.config(state='normal')
                summary_box.delete('1.0', tk.END)
                if os.path.exists(summary_path):
                    with open(summary_path, encoding='utf-8') as f:
                        summary_box.insert('1.0', f.read())
                else:
                    summary_box.insert('1.0', tr('summaries'))
                summary_box.config(state='disabled')
        tree.bind('<<TreeviewSelect>>', on_select)
        # البحث
        def on_search(*_):
            q = search_var.get().lower()
            for iid in tree.get_children():
                tree.detach(iid)
            for root, dirs, files in os.walk(self.project_path):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), self.project_path)
                    if q in rel_path.lower():
                        if not tree.exists(rel_path):
                            tree.insert('', 'end', rel_path, text=rel_path)
                        else:
                            tree.reattach(rel_path, '', 'end')
        search_var.trace_add('write', on_search) 

class Dashboard(ttk.Frame):
    def __init__(self, parent, output_dir):
        super().__init__(parent)
        self.output_dir = output_dir
        self.init_ui()
    def init_ui(self):
        theme = get_theme()
        stats = {}
        summary_path = os.path.join(self.output_dir, 'ai-summary.json')
        if os.path.exists(summary_path):
            try:
                with open(summary_path, encoding='utf-8') as f:
                    data = json.load(f)
                    stats = data.get('metrics', {})
            except Exception:
                pass
        # عرض الإحصائيات
        title = ttk.Label(self, text=tr('dashboard'), font=("Arial", 16, "bold"))
        title.pack(pady=10)
        for k, v in stats.items():
            row = ttk.Label(self, text=f"{k}: {v}", font=("Arial", 12))
            row.pack(anchor='w', padx=20) 