import os
from typing import Dict
import chardet
from .text_detector import analyze_text


def _read_text_file(path: str) -> str:
    with open(path, 'rb') as f:
        raw = f.read()
    enc = chardet.detect(raw).get('encoding') or 'utf-8'
    try:
        return raw.decode(enc, errors='ignore')
    except Exception:
        return raw.decode('utf-8', errors='ignore')


def _read_pdf(path: str) -> str:
    try:
        from pdfminer.high_level import extract_text  # type: ignore
        return extract_text(path) or ''
    except Exception:
        return ''


def _read_docx(path: str) -> str:
    try:
        import docx  # type: ignore
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ''


def _extract_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.txt', '.md', '.csv', '.log'):
        return _read_text_file(path)
    if ext == '.pdf':
        return _read_pdf(path)
    if ext in ('.docx',):
        return _read_docx(path)
    return ''


def analyze_file(path: str) -> Dict[str, object]:
    if not os.path.exists(path):
        return {"error": "File không tồn tại", "risk_level": "Không có dữ liệu", "risk_score": 0, "verdict": "Không đủ dữ liệu", "confidence": 0, "rationale": ""}
    text = _extract_text_from_file(path)
    text_result = analyze_text(text)
    return {"path": path, "extracted_chars": len(text), **text_result}
