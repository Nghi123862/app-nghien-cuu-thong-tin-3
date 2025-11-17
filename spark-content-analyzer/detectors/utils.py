# detectors/utils.py
import os
from typing import List

def find_project_root(marker_file: str = 'README.md'):
    """Finds the project root by searching upwards for a marker file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        if marker_file in os.listdir(current_dir):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            # Reached the filesystem root, fallback to a default structure
            return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        current_dir = parent_dir

# --- Reliable Data Loading ---
PROJECT_ROOT = find_project_root()
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

def load_data_file(filename: str) -> List[str]:
    """
    Loads lines from a file in the data directory.
    This function is robust to being called from different working directories.
    """
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"⚠️ [Data Loader] Cảnh báo: Không tìm thấy tệp dữ liệu '{filename}' tại '{path}'")
        return []

    items: List[str] = []
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                items.append(line.lower())
        print(f"✅ [Data Loader] Đã tải thành công {len(items)} mục từ '{filename}'")
        return items
    except Exception as e:
        print(f"❌ [Data Loader] Lỗi khi đọc tệp '{filename}': {e}")
        return []
