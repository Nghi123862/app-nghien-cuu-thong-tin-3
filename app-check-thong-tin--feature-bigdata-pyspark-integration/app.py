import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Dict, Optional
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import subprocess
import sys
import os
import threading
import queue

try:
    from detectors import analyze_url, analyze_text, analyze_file
    from detectors.ai_detector import analyze_text_with_ai
except Exception:
    # Lazy import fallback paths
    from detectors.url_detector import analyze_url  # type: ignore
    from detectors.text_detector import analyze_text  # type: ignore
    from detectors.file_detector import analyze_file  # type: ignore
    from detectors.ai_detector import analyze_text_with_ai # type: ignore
    from detectors.patterns import load_user_keywords # Import the new function


class FeedbackDialog(tk.Toplevel):
    """A dialog for submitting feedback and new keywords."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Báo cáo kết quả sai")
        self.geometry("500x300")
        self.transient(parent)
        self.grab_set()

        self.new_keywords = ""

        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=YES)

        ttk.Label(main_frame, text="Nếu bạn cho rằng kết quả này là sai, vui lòng nhập các từ khóa\n"
                                   "mà bạn tin là vi phạm (mỗi từ khóa trên một dòng).",
                  justify=LEFT).pack(anchor=W, pady=(0, 10))

        self.text_input = ttk.Text(main_frame, height=8, font="-size 10", wrap="word")
        self.text_input.pack(fill=BOTH, expand=YES, pady=(0, 10))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X)
        ttk.Button(btn_frame, text="Gửi", command=self._on_submit, bootstyle="success").pack(side=RIGHT, padx=5)
        ttk.Button(btn_frame, text="Hủy", command=self.destroy, bootstyle="secondary").pack(side=RIGHT)

    def _on_submit(self):
        self.new_keywords = self.text_input.get("1.0", tk.END).strip()
        if not self.new_keywords:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập ít nhất một từ khóa.", parent=self)
            return
        self.destroy()

    def wait_for_keywords(self) -> str:
        self.wait_window()
        return self.new_keywords


class SparkJobManager(threading.Thread):
    """
    Manages the execution of the Spark job in a separate thread to avoid freezing the UI.
    Communicates with the UI thread via a queue.
    """
    def __init__(self, config: Dict[str, str], ui_queue: queue.Queue):
        super().__init__()
        self.config = config
        self.ui_queue = ui_queue
        self.daemon = True

    def run(self) -> None:
        script_path = os.path.join(os.path.dirname(__file__), 'bigdata', 'process_urls.py')

        args = [sys.executable, script_path]
        if self.config.get("urls"):
            args += ["--urls", self.config["urls"]]
        if self.config.get("keywords"):
            args += ["--keywords", self.config["keywords"]]
        if self.config.get("output"):
            args += ["--output", self.config["output"]]
        if self.config.get("master"):
            args += ["--master", self.config["master"]]
        if self.config.get("scan_mode"):
            args += ["--scan-mode", self.config["scan_mode"]]

        try:
            self.ui_queue.put(("status", "Bắt đầu chạy Spark job..."))
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1)

            for line in iter(proc.stdout.readline, ''):
                self.ui_queue.put(("log", line.rstrip()))

            proc.stdout.close()
            code = proc.wait()

            if code == 0:
                self.ui_queue.put(("status", f"Hoàn thành! Kết quả được lưu tại:\n{self.config['output']}"))
                self.ui_queue.put(("done", "success"))
            else:
                self.ui_queue.put(("status", f"Spark job kết thúc với mã lỗi {code}."))
                self.ui_queue.put(("done", "error"))

        except FileNotFoundError:
            self.ui_queue.put(("status", "Lỗi: Không tìm thấy file script `process_urls.py`."))
            self.ui_queue.put(("done", "error"))
        except Exception as e:
            self.ui_queue.put(("status", f"Lỗi không xác định khi chạy Spark: {e}"))
            self.ui_queue.put(("done", "error"))


class SparkConfigDialog(tk.Toplevel):
    """A dialog for configuring the Spark job parameters."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Cấu hình Spark Job")
        self.geometry("600x350")
        self.transient(parent)
        self.grab_set()

        self.config: Optional[Dict[str, str]] = None

        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=YES)

        # Input files frame
        files_frame = ttk.Labelframe(main_frame, text="Đầu vào & Đầu ra", padding=10)
        files_frame.pack(fill=X, pady=(0, 10))

        # URLs
        self.urls_var = tk.StringVar()
        self._create_row(files_frame, "CSV URLs (có cột 'url'):", self.urls_var, self._pick_csv_file)

        # Keywords
        self.keywords_var = tk.StringVar()
        self._create_row(files_frame, "Từ khóa vi phạm (.txt):", self.keywords_var, self._pick_txt_file)

        # Output
        self.output_var = tk.StringVar()
        self._create_row(files_frame, "Thư mục xuất kết quả:", self.output_var, self._pick_directory)

        # Scan mode frame
        mode_frame = ttk.Labelframe(main_frame, text="Chế độ quét", padding=10)
        mode_frame.pack(fill=X, pady=(0, 10))

        self.scan_mode_var = tk.StringVar(value="url") # Default to 'url'
        ttk.Radiobutton(mode_frame, text="Quét Tên Link (Nhanh)", variable=self.scan_mode_var, value="url").pack(anchor=W, pady=2)
        ttk.Radiobutton(mode_frame, text="Quét Nội Dung Link (Chậm)", variable=self.scan_mode_var, value="content").pack(anchor=W, pady=2)

        # Advanced options frame
        adv_frame = ttk.Labelframe(main_frame, text="Tùy chọn nâng cao", padding=10)
        adv_frame.pack(fill=X)

        # Master
        self.master_var = tk.StringVar()
        self._create_row(adv_frame, "Spark master (tùy chọn):", self.master_var, None)

        # Buttons
        btn_frame = ttk.Frame(main_frame, padding=(10, 0))
        btn_frame.pack(fill=X)
        ttk.Button(btn_frame, text="Chạy", command=self._on_submit, bootstyle="success").pack(side=RIGHT, padx=5)
        ttk.Button(btn_frame, text="Hủy", command=self.destroy, bootstyle="secondary").pack(side=RIGHT)

    def _create_row(self, parent, label_text, var, command):
        row = ttk.Frame(parent)
        row.pack(fill=X, pady=4)
        ttk.Label(row, text=label_text, width=20).pack(side=LEFT)
        entry = ttk.Entry(row, textvariable=var)
        entry.pack(side=LEFT, fill=X, expand=YES, padx=5)
        if command:
            ttk.Button(row, text="Chọn...", command=lambda v=var, c=command: c(v), bootstyle="info-outline").pack(side=LEFT)

    def _pick_csv_file(self, var):
        path = filedialog.askopenfilename(parent=self, filetypes=[("CSV", "*.csv"), ("Tất cả", "*.*")])
        if path: var.set(path)

    def _pick_txt_file(self, var):
        path = filedialog.askopenfilename(parent=self, filetypes=[("Text", "*.txt"), ("Tất cả", "*.*")])
        if path: var.set(path)

    def _pick_directory(self, var):
        path = filedialog.askdirectory(parent=self)
        if path: var.set(path)

    def _on_submit(self):
        urls = self.urls_var.get().strip()
        keywords = self.keywords_var.get().strip()
        output = self.output_var.get().strip()

        if not all([urls, keywords, output]):
            messagebox.showwarning("Thiếu thông tin", "Vui lòng cung cấp đủ đường dẫn cho URLs, Keywords, và Output.", parent=self)
            return

        self.config = {
            "urls": urls,
            "keywords": keywords,
            "output": output,
            "master": self.master_var.get().strip(),
            "scan_mode": self.scan_mode_var.get()
        }
        self.destroy()

    def wait_for_config(self) -> Optional[Dict[str, str]]:
        self.wait_window()
        return self.config


class App(ttk.Window):
    def __init__(self) -> None:
        # Use a modern theme from ttkbootstrap
        super().__init__(themename="superhero")
        self.title("Công Cụ Giám Sát Nội Dung Vi Phạm & Tin Giả")
        self.geometry("900x700")

        self.spark_job: Optional[SparkJobManager] = None
        self.spark_queue = queue.Queue()

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

    def _on_report_feedback(self):
        """Handles the feedback reporting process."""
        dialog = FeedbackDialog(self)
        new_keywords = dialog.wait_for_keywords()

        if new_keywords:
            try:
                # Path to the user-added keywords file
                keywords_path = os.path.join(os.path.dirname(__file__), 'data', 'user_added_keywords.txt')

                # Append new keywords to the file
                with open(keywords_path, 'a', encoding='utf-8') as f:
                    f.write('\n' + new_keywords + '\n')

                messagebox.showinfo("Cảm ơn bạn!", "Cảm ơn bạn đã đóng góp! Các từ khóa mới sẽ được sử dụng trong những lần phân tích sau.", parent=self)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu từ khóa mới: {e}", parent=self)

    def _build_url_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Nhập đường dẫn (URL) để phân tích:", font="-size 12").pack(anchor=W, pady=(0, 5))
        self.url_var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=self.url_var, font="-size 11")
        entry.pack(fill=X, pady=(0, 10), ipady=4)

        # Scan mode frame for URL tab
        url_mode_frame = ttk.Labelframe(parent, text="Chế độ quét", padding=(10, 5))
        url_mode_frame.pack(fill=X, pady=(0, 10))

        self.url_scan_mode_var = tk.StringVar(value="url") # Default to 'url'
        ttk.Radiobutton(url_mode_frame, text="Quét Tên Link (Nhanh)", variable=self.url_scan_mode_var, value="url").pack(anchor=W)
        ttk.Radiobutton(url_mode_frame, text="Quét Nội Dung Link (Chậm)", variable=self.url_scan_mode_var, value="content").pack(anchor=W)

        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=X, pady=5)
        ttk.Button(action_frame, text="Phân tích URL", command=self._on_check_url, bootstyle="success").pack(side=LEFT, ipady=4)
        ttk.Button(action_frame, text="Báo cáo kết quả sai", command=self._on_report_feedback, bootstyle="warning-outline").pack(side=LEFT, padx=10, ipady=4)

        self.url_result = ttk.Text(parent, height=14, font="-size 10", wrap="word", relief=FLAT)
        self.url_result.pack(fill=BOTH, expand=YES, pady=(5,0))
        self.url_result.configure(state='disabled') # Make it read-only initially

    def _build_text_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Dán hoặc nhập văn bản cần phân tích:", font="-size 12").pack(anchor=W, pady=(0, 5))
        self.text_input = ttk.Text(parent, height=12, font="-size 10", wrap="word", relief=FLAT)
        self.text_input.pack(fill=BOTH, expand=YES, pady=(0, 10))

        # Scan mode frame for Text tab
        text_mode_frame = ttk.Labelframe(parent, text="Phương pháp phân tích", padding=(10, 5))
        text_mode_frame.pack(fill=X, pady=(0, 10))

        self.text_scan_mode_var = tk.StringVar(value="keyword") # Default to 'keyword'
        ttk.Radiobutton(text_mode_frame, text="Dựa trên Từ khóa (Nhanh)", variable=self.text_scan_mode_var, value="keyword").pack(anchor=W)
        ttk.Radiobutton(text_mode_frame, text="Sử dụng AI (Rất chậm)", variable=self.text_scan_mode_var, value="ai").pack(anchor=W)

        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=X, pady=5)
        ttk.Button(action_frame, text="Phân tích văn bản", command=self._on_check_text, bootstyle="success").pack(side=LEFT, ipady=4)
        ttk.Button(action_frame, text="Báo cáo kết quả sai", command=self._on_report_feedback, bootstyle="warning-outline").pack(side=LEFT, padx=10, ipady=4)

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
        # Top control frame
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=X, pady=(0, 10))

        self.bd_run_button = ttk.Button(control_frame, text="Cấu hình và Chạy Job", bootstyle="success", command=self._on_run_bigdata)
        self.bd_run_button.pack(side=LEFT, ipady=4)

        self.bd_status_label = ttk.Label(control_frame, text="  Trạng thái: Sẵn sàng", anchor=W)
        self.bd_status_label.pack(side=LEFT, fill=X, expand=YES, padx=10)

        # Progress bar
        self.bd_progress = ttk.Progressbar(parent, mode='indeterminate', length=100)
        self.bd_progress.pack(fill=X, pady=(0, 5))

        # Log area
        log_frame = ttk.Labelframe(parent, text="Logs", padding=10)
        log_frame.pack(fill=BOTH, expand=YES)
        self.bd_log = ttk.Text(log_frame, height=18, font="-size 10", wrap="word", relief=FLAT)
        self.bd_log.pack(fill=BOTH, expand=YES)
        self.bd_log.configure(state='disabled')

    def _append_bd_log(self, text: str) -> None:
        self.bd_log.configure(state='normal')
        self.bd_log.insert(tk.END, text + "\n")
        self.bd_log.see(tk.END)
        self.bd_log.configure(state='disabled')

    def _on_run_bigdata(self) -> None:
        dialog = SparkConfigDialog(self)
        config = dialog.wait_for_config()

        if not config:
            return

        self.bd_run_button.configure(state='disabled')
        self.bd_status_label.configure(text="  Trạng thái: Đang chạy...")
        self.bd_progress.start()

        # Clear previous logs
        self.bd_log.configure(state='normal')
        self.bd_log.delete("1.0", tk.END)
        self.bd_log.configure(state='disabled')

        self.spark_job = SparkJobManager(config, self.spark_queue)
        self.spark_job.start()
        self.after(100, self._check_spark_queue)

    def _check_spark_queue(self) -> None:
        try:
            while True:
                message_type, data = self.spark_queue.get_nowait()
                if message_type == "log":
                    self._append_bd_log(data)
                elif message_type == "status":
                    self.bd_status_label.configure(text=f"  Trạng thái: {data}")
                elif message_type == "done":
                    self.bd_progress.stop()
                    self.bd_run_button.configure(state='normal')
                    if data == "success":
                        messagebox.showinfo("Thành công", "Xử lý Big Data hoàn tất!")
                    else:
                        messagebox.showerror("Lỗi", "Đã có lỗi xảy ra trong quá trình xử lý. Vui lòng kiểm tra logs.")
                    return # Stop polling
        except queue.Empty:
            pass # No new messages

        self.after(100, self._check_spark_queue)

    def _on_check_url(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập URL")
            return

        scan_mode = self.url_scan_mode_var.get()
        # To prevent UI freeze, run content scan in a separate thread
        if scan_mode == "content":
            # Simple threading for single URL scan to avoid freezing the UI
            thread = threading.Thread(target=self._run_url_analysis_thread, args=(url, scan_mode))
            thread.daemon = True
            thread.start()
        else:
            # URL scan is fast, can run directly
            try:
                result = analyze_url(url, mode=scan_mode)
                self._display_summary_plus_json(self.url_result, result)
            except Exception as e:
                self._display_error(self.url_result, e)

    def _run_url_analysis_thread(self, url: str, scan_mode: str) -> None:
        """Helper to run analysis in a thread and schedule UI update."""
        try:
            result = analyze_url(url, mode=scan_mode)
            # Schedule the UI update to run in the main thread
            self.after(0, self._display_summary_plus_json, self.url_result, result)
        except Exception as e:
            self.after(0, self._display_error, self.url_result, e)

    def _on_check_text(self) -> None:
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập văn bản")
            return

        scan_mode = self.text_scan_mode_var.get()

        # Run analysis in a separate thread to avoid freezing the UI, especially for AI
        thread = threading.Thread(target=self._run_text_analysis_thread, args=(text, scan_mode))
        thread.daemon = True
        thread.start()

    def _run_text_analysis_thread(self, text: str, scan_mode: str) -> None:
        """Helper to run text analysis in a thread and schedule UI update."""
        try:
            if scan_mode == "ai":
                # Load the latest user keywords and pass them to the AI
                user_keywords = load_user_keywords()
                result = analyze_text_with_ai(text, user_keywords=user_keywords)
            else: # keyword
                result = analyze_text(text)

            # Schedule the UI update to run in the main thread
            self.after(0, self._display_summary_plus_json, self.text_result, result)
        except Exception as e:
            self.after(0, self._display_error, self.text_result, e)

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
        messagebox.showerror("Lỗi", f"Đã có lỗi xảy ra trong quá trình phân tích:\n{error}")

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

        # Insert the analyzed URL with color coding based on risk
        analyzed_url = payload.get("url", "N/A")
        widget.insert(tk.END, f"{analyzed_url}\n\n", risk_tag)

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
