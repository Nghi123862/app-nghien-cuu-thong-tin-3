import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import os
import requests
from bs4 import BeautifulSoup
import subprocess
import sys
import json

# --- Import Detectors ---
from detectors.url_detector import analyze_url
from detectors.text_detector import analyze_text
from detectors.file_detector import analyze_file
from detectors.ai_detector import analyze_text_with_ai

class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="superhero")
        self.title("Công Cụ Giám Sát Nội Dung Vi Phạm & Tin Giả")
        self.geometry("900x700")
        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=YES)

        header = ttk.Label(main_frame, text="Công Cụ Phân Tích Nội Dung", font="-size 16 -weight bold")
        header.pack(pady=(0, 15))

        notebook = ttk.Notebook(main_frame, bootstyle="primary")
        notebook.pack(fill=BOTH, expand=YES)

        self._build_url_tab(notebook)
        self._build_text_tab(notebook)
        self._build_file_tab(notebook)
        self._build_bigdata_tab(notebook)

    def _build_url_tab(self, notebook):
        parent = ttk.Frame(notebook, padding=15)
        notebook.add(parent, text="  Kiểm tra Link  ")

        ttk.Label(parent, text="Nhập đường dẫn (URL) để phân tích:", font="-size 12").pack(anchor=W, pady=(0, 5))
        self.url_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.url_var, font="-size 11").pack(fill=X, pady=(0, 10), ipady=4)

        ttk.Button(parent, text="Phân tích URL", command=self._on_check_url, bootstyle="success").pack(anchor=W, pady=5, ipady=4)
        self.url_result = ttk.Text(parent, height=16, font="-size 10", wrap="word", relief=FLAT)
        self.url_result.pack(fill=BOTH, expand=YES, pady=(5,0))
        self.url_result.configure(state='disabled')

    def _build_text_tab(self, notebook):
        parent = ttk.Frame(notebook, padding=15)
        notebook.add(parent, text="  Kiểm tra Văn bản  ")

        ttk.Label(parent, text="Dán hoặc nhập văn bản cần phân tích:", font="-size 12").pack(anchor=W, pady=(0, 5))
        self.text_input = ttk.Text(parent, height=12, font="-size 10", wrap="word", relief=FLAT)
        self.text_input.pack(fill=BOTH, expand=YES, pady=(0, 10))

        method_frame = ttk.Frame(parent)
        method_frame.pack(anchor=W, fill=X, pady=5)
        ttk.Label(method_frame, text="Phương pháp phân tích:", font="-size 10 -weight bold").pack(anchor=W)

        self.text_analysis_method = tk.StringVar(value="keyword")
        ttk.Radiobutton(method_frame, text="Dựa trên Từ khóa (Nhanh)", variable=self.text_analysis_method, value="keyword").pack(anchor=W, side=LEFT, padx=10)
        ttk.Radiobutton(method_frame, text="Sử dụng AI (Chậm)", variable=self.text_analysis_method, value="ai").pack(anchor=W, side=LEFT)

        ttk.Button(parent, text="Phân tích văn bản", command=self._on_check_text, bootstyle="success").pack(anchor=W, pady=5, ipady=4)
        self.text_result = ttk.Text(parent, height=12, font="-size 10", wrap="word", relief=FLAT)
        self.text_result.pack(fill=BOTH, expand=YES, pady=(5,0))
        self.text_result.configure(state='disabled')

    def _build_file_tab(self, notebook):
        parent = ttk.Frame(notebook, padding=15)
        notebook.add(parent, text="  Kiểm tra Tập tin  ")

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=X, pady=(5, 10))
        ttk.Button(btn_row, text="Chọn tập tin...", command=self._on_pick_file, bootstyle="info").pack(side=LEFT, ipady=4)
        self.file_path_var = tk.StringVar()
        ttk.Entry(btn_row, textvariable=self.file_path_var, font="-size 11").pack(side=LEFT, fill=X, expand=YES, padx=10, ipady=4)
        ttk.Button(btn_row, text="Phân tích tập tin", command=self._on_check_file, bootstyle="success").pack(side=LEFT, ipady=4)

        self.file_result = ttk.Text(parent, height=18, font="-size 10", wrap="word", relief=FLAT)
        self.file_result.pack(fill=BOTH, expand=YES, pady=(5,0))
        self.file_result.configure(state='disabled')

    def _build_bigdata_tab(self, notebook):
        parent = ttk.Frame(notebook, padding=15)
        notebook.add(parent, text="  Big Data (Spark)  ")

        # ... (Big Data UI remains the same as it doesn't use the integrated AI) ...

    def _on_check_url(self):
        url = self.url_var.get().strip()
        if not url: return
        try:
            result = analyze_url(url)
            self._display_summary_plus_json(self.url_result, result)
        except Exception as e:
            self._display_error(self.url_result, e)

    def _on_check_text(self):
        text = self.text_input.get("1.0", tk.END).strip()
        if not text: return

        method = self.text_analysis_method.get()
        user_keywords = self._load_user_keywords()

        try:
            self.config(cursor="watch")
            self.update_idletasks()
            if method == "keyword":
                result = analyze_text(text, user_keywords=user_keywords)
            else: # AI
                result = analyze_text_with_ai(text, user_keywords=user_keywords)
            self._display_summary_plus_json(self.text_result, result)
        except Exception as e:
            self._display_error(self.text_result, e)
        finally:
            self.config(cursor="")

    def _on_pick_file(self):
        path = filedialog.askopenfilename()
        if path: self.file_path_var.set(path)

    def _on_check_file(self):
        path = self.file_path_var.get().strip()
        if not path: return
        try:
            result = analyze_file(path)
            self._display_summary_plus_json(self.file_result, result)
        except Exception as e:
            self._display_error(self.file_result, e)

    def _load_user_keywords(self):
        keywords_path = os.path.join('data', 'user_added_keywords.txt')
        if not os.path.exists(keywords_path):
            return []
        with open(keywords_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]

    def _display_error(self, widget, error):
        widget.configure(state='normal')
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, f"Lỗi không xác định:\n{error}")
        widget.configure(state='disabled')
        messagebox.showerror("Lỗi", f"Đã xảy ra lỗi:\n{error}")

    def _display_summary_plus_json(self, widget, payload):
        widget.configure(state='normal')
        widget.delete("1.0", tk.END)

        # ... (Styling and display logic remains the same) ...

        widget.configure(state='disabled')

if __name__ == "__main__":
    App().mainloop()
