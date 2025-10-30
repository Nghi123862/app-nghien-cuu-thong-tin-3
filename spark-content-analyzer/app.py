import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

try:
    from detectors import analyze_url, analyze_text, analyze_file
    # Import the new Ollama-based analyzer
    from detectors.ai_detector import analyze_text_with_ai as analyze_text_with_ollama
except Exception:
    # Lazy import fallback paths
    from detectors.url_detector import analyze_url  # type: ignore
    from detectors.text_detector import analyze_text  # type: ignore
    from detectors.file_detector import analyze_file  # type: ignore
    from detectors.ai_detector import analyze_text_with_ai as analyze_text_with_ollama # type: ignore


class App(ttk.Window):
    def __init__(self) -> None:
        # Use a modern theme from ttkbootstrap
        super().__init__(themename="superhero")
        self.title("Công Cụ Giám Sát Nội Dung Vi Phạm & Tin Giả")
        self.geometry("900x700")
        self._build_ui()

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=YES)

        header = ttk.Label(main_frame, text="Công Cụ Phân Tích Nội Dung", font="-size 16 -weight bold")
        header.pack(pady=(0, 15))

        notebook = ttk.Notebook(main_frame, bootstyle="primary")
        notebook.pack(fill=BOTH, expand=YES)

        # URL Tab
        url_tab = ttk.Frame(notebook, padding=15)
        notebook.add(url_tab, text="  Kiểm tra Link  ")
        self._build_url_tab(url_tab)

        # Text Tab
        text_tab = ttk.Frame(notebook, padding=15)
        notebook.add(text_tab, text="  Kiểm tra Văn bản  ")
        self._build_text_tab(text_tab)

        # File Tab
        file_tab = ttk.Frame(notebook, padding=15)
        notebook.add(file_tab, text="  Kiểm tra Tập tin  ")
        self._build_file_tab(file_tab)

        # Big Data Tab
        big_tab = ttk.Frame(notebook, padding=15)
        notebook.add(big_tab, text="  Big Data (Spark)  ")
        self._build_bigdata_tab(big_tab)

    def _build_url_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Nhập đường dẫn (URL) để phân tích:", font="-size 12").pack(anchor=W, pady=(0, 5))
        self.url_var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=self.url_var, font="-size 11")
        entry.pack(fill=X, pady=(0, 10), ipady=4)

        # --- Analysis Method Selection for URL ---
        method_frame = ttk.Frame(parent)
        method_frame.pack(anchor=W, fill=X, pady=5)
        ttk.Label(method_frame, text="Phương pháp phân tích:", font="-size 10 -weight bold").pack(anchor=W)

        self.url_analysis_method = tk.StringVar(value="url_only")

        url_only_radio = ttk.Radiobutton(method_frame, text="Chỉ phân tích URL (Rất nhanh)", variable=self.url_analysis_method, value="url_only")
        url_only_radio.pack(anchor=W, side=LEFT, padx=10)

        ollama_radio = ttk.Radiobutton(method_frame, text="Phân tích nội dung trang với Ollama AI (Rất chậm)", variable=self.url_analysis_method, value="ollama_content")
        ollama_radio.pack(anchor=W, side=LEFT)
        # --- End of Selection ---

        ttk.Button(parent, text="Phân tích URL", command=self._on_check_url, bootstyle="success").pack(anchor=W, pady=5, ipady=4)
        self.url_result = ttk.Text(parent, height=16, font="-size 10", wrap="word", relief=FLAT)
        self.url_result.pack(fill=BOTH, expand=YES, pady=(5,0))
        self.url_result.configure(state='disabled') # Make it read-only initially

    def _build_text_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Dán hoặc nhập văn bản cần phân tích:", font="-size 12").pack(anchor=W, pady=(0, 5))
        self.text_input = ttk.Text(parent, height=12, font="-size 10", wrap="word", relief=FLAT)
        self.text_input.pack(fill=BOTH, expand=YES, pady=(0, 10))

        # --- Analysis Method Selection ---
        method_frame = ttk.Frame(parent)
        method_frame.pack(anchor=W, fill=X, pady=5)
        ttk.Label(method_frame, text="Phương pháp phân tích:", font="-size 10 -weight bold").pack(anchor=W)

        self.text_analysis_method = tk.StringVar(value="keyword")

        keyword_radio = ttk.Radiobutton(method_frame, text="Dựa trên Từ khóa (Nhanh)", variable=self.text_analysis_method, value="keyword")
        keyword_radio.pack(anchor=W, side=LEFT, padx=10)

        ollama_radio = ttk.Radiobutton(method_frame, text="Sử dụng Ollama AI (Cục bộ, Chậm)", variable=self.text_analysis_method, value="ollama")
        ollama_radio.pack(anchor=W, side=LEFT)
        # --- End of Selection ---

        ttk.Button(parent, text="Phân tích văn bản", command=self._on_check_text, bootstyle="success").pack(anchor=W, pady=5, ipady=4)
        self.text_result = ttk.Text(parent, height=12, font="-size 10", wrap="word", relief=FLAT)
        self.text_result.pack(fill=BOTH, expand=YES, pady=(5,0))
        self.text_result.configure(state='disabled')

    def _build_file_tab(self, parent: ttk.Frame) -> None:
        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=X, pady=(5, 10))
        ttk.Button(btn_row, text="Chọn tập tin...", command=self._on_pick_file, bootstyle="info").pack(side=LEFT, ipady=4)
        self.file_path_var = tk.StringVar()
        ttk.Entry(btn_row, textvariable=self.file_path_var, font="-size 11").pack(side=LEFT, fill=X, expand=YES, padx=10, ipady=4)
        ttk.Button(btn_row, text="Phân tích tập tin", command=self._on_check_file, bootstyle="success").pack(side=LEFT, ipady=4)

        self.file_result = ttk.Text(parent, height=18, font="-size 10", wrap="word", relief=FLAT)
        self.file_result.pack(fill=BOTH, expand=YES, pady=(5,0))
        self.file_result.configure(state='disabled')

    def _build_bigdata_tab(self, parent: ttk.Frame) -> None:
        # Inputs row
        row1 = ttk.Frame(parent)
        row1.pack(fill=X, pady=(0, 8))
        ttk.Label(row1, text="CSV URLs (có cột 'url'):").pack(side=LEFT)
        self.bd_urls_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.bd_urls_var).pack(side=LEFT, fill=X, expand=YES, padx=8)
        ttk.Button(row1, text="Chọn...", bootstyle="info", command=self._on_pick_bd_urls).pack(side=LEFT)

        row2 = ttk.Frame(parent)
        row2.pack(fill=X, pady=(0, 8))
        ttk.Label(row2, text="Từ khóa vi phạm (.txt):").pack(side=LEFT)
        self.bd_keywords_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.bd_keywords_var).pack(side=LEFT, fill=X, expand=YES, padx=8)
        ttk.Button(row2, text="Chọn...", bootstyle="info", command=self._on_pick_bd_keywords).pack(side=LEFT)

        row3 = ttk.Frame(parent)
        row3.pack(fill=X, pady=(0, 8))
        ttk.Label(row3, text="Thư mục xuất kết quả:").pack(side=LEFT)
        self.bd_output_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.bd_output_var).pack(side=LEFT, fill=X, expand=YES, padx=8)
        ttk.Button(row3, text="Chọn...", bootstyle="info", command=self._on_pick_bd_output).pack(side=LEFT)

        row4 = ttk.Frame(parent)
        row4.pack(fill=X, pady=(0, 8))
        ttk.Label(row4, text="Spark master (tùy chọn):").pack(side=LEFT)
        self.bd_master_var = tk.StringVar()
        ttk.Entry(row4, textvariable=self.bd_master_var).pack(side=LEFT, fill=X, expand=YES, padx=8)

        # --- Analysis Method Selection for Big Data ---
        method_frame = ttk.Frame(parent)
        method_frame.pack(anchor=W, fill=X, pady=10)
        ttk.Label(method_frame, text="Phương pháp phân tích:", font="-size 10 -weight bold").pack(anchor=W)

        self.bd_analysis_method = tk.StringVar(value="url_only")

        url_only_radio = ttk.Radiobutton(method_frame, text="Chỉ phân tích URL (Nhanh)", variable=self.bd_analysis_method, value="url_only")
        url_only_radio.pack(anchor=W, side=LEFT, padx=10)

        ollama_radio = ttk.Radiobutton(method_frame, text="Phân tích nội dung với Ollama AI (Rất chậm)", variable=self.bd_analysis_method, value="ollama_content")
        ollama_radio.pack(anchor=W, side=LEFT)
        # --- End of Selection ---

        ttk.Button(parent, text="Chạy xử lý với Spark", bootstyle="success", command=self._on_run_bigdata).pack(anchor=W, pady=6)

        self.bd_log = ttk.Text(parent, height=18, font="-size 10", wrap="word", relief=FLAT)
        self.bd_log.pack(fill=BOTH, expand=YES)
        self.bd_log.configure(state='disabled')

    def _on_pick_bd_urls(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Tất cả", "*.*")])
        if path:
            self.bd_urls_var.set(path)

    def _on_pick_bd_keywords(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt"), ("Tất cả", "*.*")])
        if path:
            self.bd_keywords_var.set(path)

    def _on_pick_bd_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.bd_output_var.set(path)

    def _append_bd_log(self, text: str) -> None:
        self.bd_log.configure(state='normal')
        self.bd_log.insert(tk.END, text + "\n")
        self.bd_log.see(tk.END)
        self.bd_log.configure(state='disabled')

    def _on_run_bigdata(self) -> None:
        import subprocess, sys, shlex, os
        script_path = os.path.join(os.path.dirname(__file__), 'bigdata', 'process_urls.py')
        urls = self.bd_urls_var.get().strip()
        keywords = self.bd_keywords_var.get().strip()
        output = self.bd_output_var.get().strip()
        master = self.bd_master_var.get().strip()
        method = self.bd_analysis_method.get()

        args = [sys.executable, script_path]
        args += ["--method", method]
        if urls:
            args += ["--urls", urls]
        if keywords:
            args += ["--keywords", keywords]
        if output:
            args += ["--output", output]
        if master:
            args += ["--master", master]

        self.bd_log.configure(state='normal')
        self.bd_log.delete("1.0", tk.END)
        self.bd_log.configure(state='disabled')
        self._append_bd_log("Bắt đầu chạy Spark job...")

        try:
            # Use text mode and line-buffered output for real-time logs
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in iter(proc.stdout.readline, ''):
                self._append_bd_log(line.rstrip())
            proc.stdout.close()
            code = proc.wait()
            if code == 0:
                self._append_bd_log("Hoàn thành.")
                messagebox.showinfo("Spark", "Xử lý Big Data hoàn tất")
            else:
                self._append_bd_log(f"Spark job kết thúc với mã {code}")
                messagebox.showerror("Spark", f"Lỗi khi chạy Spark (mã {code})")
        except Exception as e:
            messagebox.showerror("Spark", f"Không thể chạy Spark: {e}")

    def _on_check_url(self) -> None:
        import os
        import requests
        from bs4 import BeautifulSoup

        url = self.url_var.get().strip()
        method = self.url_analysis_method.get()

        if not url:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập URL")
            return

        try:
            self.config(cursor="watch")
            self.update_idletasks()

            result = None
            user_keywords = []

            keywords_path = os.path.join('data', 'user_added_keywords.txt')
            if os.path.exists(keywords_path):
                with open(keywords_path, 'r', encoding='utf-8') as f:
                    user_keywords = [line.strip() for line in f if line.strip()]

            if method == "url_only":
                result = analyze_url(url, user_keywords=user_keywords)
            elif method == "ollama_content":
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
                response = requests.get(url, timeout=15, headers=headers)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')
                text_content = ' '.join(t.strip() for t in soup.stripped_strings)

                if not text_content:
                    raise ValueError("Không thể trích xuất nội dung văn bản từ URL này.")

                result = analyze_text_with_ollama(text_content, user_keywords=user_keywords)

            if result:
                self._display_summary_plus_json(self.url_result, result)
            else:
                raise ValueError("Phương pháp phân tích không hợp lệ được chọn.")

        except Exception as e:
            self._display_error(self.url_result, e)
        finally:
            self.config(cursor="")

    def _on_check_text(self) -> None:
        import os
        text = self.text_input.get("1.0", tk.END).strip()
        method = self.text_analysis_method.get()

        if not text:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập văn bản")
            return

        try:
            result = None
            user_keywords = []

            # Load user-added keywords to pass to the analysis functions
            keywords_path = os.path.join('data', 'user_added_keywords.txt')
            if os.path.exists(keywords_path):
                with open(keywords_path, 'r', encoding='utf-8') as f:
                    user_keywords = [line.strip() for line in f if line.strip()]

            if method == "keyword":
                # The user selected the original keyword-based analysis
                result = analyze_text(text, user_keywords=user_keywords)
            elif method == "ollama":
                # The user selected the new Ollama-based analysis, now with user keywords
                # NOTE: This will block the UI. A future improvement would be to run this in a thread.
                result = analyze_text_with_ollama(text, user_keywords=user_keywords)

            if result:
                self._display_summary_plus_json(self.text_result, result)
            else:
                raise ValueError("Phương pháp phân tích không hợp lệ được chọn.")

        except Exception as e:
            self._display_error(self.text_result, e)

    def _on_pick_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Tất cả", "*.*"), ("Văn bản", "*.txt"), ("PDF", "*.pdf"), ("Word", "*.docx")])
        if path:
            self.file_path_var.set(path)

    def _on_check_file(self) -> None:
        path = self.file_path_var.get().strip()
        if not path:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng chọn tập tin")
            return
        try:
            result = analyze_file(path)
            self._display_summary_plus_json(self.file_result, result)
        except Exception as e:
            self._display_error(self.file_result, e)

    def _display_error(self, widget: ttk.Text, error: Exception) -> None:
        widget.configure(state='normal')
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, f"Lỗi không xác định:\n{error}")
        widget.configure(state='disabled')
        messagebox.showerror("Lỗi", f"Đã xảy ra lỗi trong quá trình phân tích:\n{error}")

    def _display_summary_plus_json(self, widget: ttk.Text, payload: Any) -> None:
        import json
        widget.configure(state='normal')
        widget.delete("1.0", tk.END)

        if not isinstance(payload, dict):
            widget.insert(tk.END, str(payload))
            widget.configure(state='disabled')
            return

        # Define styles for text
        widget.tag_configure("header", font="-size 12 -weight bold", foreground=self.style.colors.primary)
        widget.tag_configure("bold", font="-weight bold")
        widget.tag_configure("risk_cao", foreground=self.style.colors.danger)
        widget.tag_configure("risk_trung bình", foreground=self.style.colors.warning)
        widget.tag_configure("risk_thấp", foreground=self.style.colors.success)
        widget.tag_configure("json_key", foreground=self.style.colors.info)
        widget.tag_configure("json_string", foreground=self.style.colors.light)
        widget.tag_configure("json_number", foreground=self.style.colors.success)

        verdict = payload.get("verdict", "")
        risk = payload.get("risk_level", "Không xác định").lower()

        risk_tag = f"risk_{risk}"

        widget.insert(tk.END, "TỔNG QUAN PHÂN TÍCH\n", "header")
        widget.insert(tk.END, "Kết luận: ", "bold")
        widget.insert(tk.END, f"{verdict}\n", risk_tag)
        widget.insert(tk.END, "Độ tin cậy: ", "bold")
        widget.insert(tk.END, f"{payload.get('confidence', 'N/A')}%\n")
        widget.insert(tk.END, "Mức rủi ro: ", "bold")
        widget.insert(tk.END, f"{payload.get('risk_level', 'N/A')}\n", risk_tag)
        widget.insert(tk.END, "Lý do: ", "bold")
        widget.insert(tk.END, f"{payload.get('rationale', 'Không có')}\n\n")

        try:
            widget.insert(tk.END, "--- Dữ liệu phân tích chi tiết ---\n", "header")
            json_str = json.dumps(payload, ensure_ascii=False, indent=2)
            widget.insert(tk.END, json_str)
        except Exception as e:
            widget.insert(tk.END, f"\nLỗi hiển thị JSON: {e}")

        widget.configure(state='disabled')


if __name__ == "__main__":
    App().mainloop()