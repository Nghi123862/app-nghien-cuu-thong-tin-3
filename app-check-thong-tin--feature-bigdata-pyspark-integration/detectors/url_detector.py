import os
import re
import socket
from urllib.parse import urlparse
from typing import Dict, List, Tuple
import requests
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


def _load_lines(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    items: List[str] = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            items.append(line.lower())
    return items


def _load_blocklist() -> List[str]:
    return _load_lines(os.path.join(DATA_DIR, 'domains_blocklist.txt'))


def _load_whitelist() -> List[str]:
    return _load_lines(os.path.join(DATA_DIR, 'domains_whitelist.txt'))


BLOCKLIST = set(_load_blocklist())
WHITELIST = set(_load_whitelist())


def _domain_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.hostname or ''
    except Exception:
        return ''


def _resolve_ip(host: str) -> str:
    try:
        return socket.gethostbyname(host)
    except Exception:
        return ''


def _fetch_text(url: str, timeout: int = 8) -> Tuple[str, Dict[str, str]]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ContentSafety/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        meta = {"final_url": resp.url, "status": str(resp.status_code)}
        return text, meta
    except Exception as e:
        return '', {"error": str(e)}


VIOLATION_PATTERNS = [
    re.compile(r"\b(lừa đảo|đồi trụy|kích động|bạo lực|thù hằn|khủng bố)\b", re.IGNORECASE),
    re.compile(r"\b(fake news|scam|porn|hate speech|terror)\b", re.IGNORECASE),
]


def _verdict_from_score(score: int, has_block: bool, text_hits: int, is_whitelist: bool) -> Tuple[str, int, str]:
    truth_confidence = max(5, min(95, 95 - score))
    if score >= 70:
        verdict = "Thông tin giả/vi phạm"
        rationale = "Rủi ro cao" + (", tên miền cảnh báo" if has_block else "") + (f", {text_hits} dấu hiệu nội dung" if text_hits else "")
        truth_confidence = max(5, min(truth_confidence, 25))
    elif score >= 35:
        verdict = "Trung tính nhưng có rủi ro"
        rationale = "Một số dấu hiệu" + (", tên miền cảnh báo" if has_block else "") + (f", {text_hits} dấu hiệu nội dung" if text_hits else "")
        truth_confidence = max(20, min(truth_confidence, 70))
    else:
        verdict = "Thông tin có vẻ thật/an toàn"
        rationale = "Không phát hiện dấu hiệu đáng kể" + (", nguồn tin uy tín" if is_whitelist else "")
        truth_confidence = max(75, truth_confidence)
    return verdict, truth_confidence, rationale


def analyze_url(url: str) -> Dict[str, object]:
    domain = _domain_from_url(url).lower()
    in_block = domain in BLOCKLIST or any(domain.endswith('.' + d) for d in BLOCKLIST)
    in_white = domain in WHITELIST or any(domain.endswith('.' + d) for d in WHITELIST)

    resolved_ip = _resolve_ip(domain) if domain else ''

    page_text, meta = _fetch_text(url)

    indicators: List[str] = []
    if in_block:
        indicators.append(f"Tên miền nằm trong danh sách cảnh báo: {domain}")
    if in_white:
        indicators.append(f"Tên miền thuộc nguồn tin uy tín: {domain}")
    if resolved_ip:
        if resolved_ip.startswith('10.') or resolved_ip.startswith('192.168.'):
            indicators.append("Tên miền trỏ về mạng nội bộ (bất thường)")
    else:
        indicators.append("Không phân giải được DNS cho tên miền")

    # Handle unreachable/non-existent links
    unreachable = False
    if not resolved_ip:
        unreachable = True
    if 'error' in meta:
        err = meta.get('error', '').lower()
        if any(key in err for key in ['name or service not known', 'nodename nor servname', 'failed to establish a new connection', 'name_resolved', 'dns', 'not found', '404']):
            unreachable = True
            indicators.append(f"Lỗi truy cập: {meta.get('error')}")

    text_hits: List[str] = []
    if page_text:
        for pat in VIOLATION_PATTERNS:
            if pat.search(page_text):
                text_hits.append(pat.pattern)

    risk_score = 0
    if in_block:
        risk_score += 60
    if text_hits:
        risk_score += 30
    if not page_text:
        risk_score += 10
    if in_white:
        risk_score = max(0, risk_score - 25)
    if unreachable:
        risk_score += 25  # unreachable link => cannot verify → at least medium risk

    # Special verdict for unreachable
    if unreachable:
        return {
            "url": url,
            "domain": domain,
            "resolved_ip": resolved_ip,
            "blocklisted": in_block,
            "whitelisted": in_white,
            "text_match_count": len(text_hits),
            "indicators": indicators,
            "meta": meta,
            "risk_score": max(risk_score, 40),
            "risk_level": 'Trung bình' if risk_score < 80 else 'Cao',
            "verdict": "Liên kết không tồn tại/không đủ dữ liệu",
            "confidence": 20,
            "rationale": "Không phân giải DNS hoặc truy cập thất bại, không đủ dữ liệu xác thực",
        }

    risk_level = 'Thấp'
    if risk_score >= 70:
        risk_level = 'Cao'
    elif risk_score >= 35:
        risk_level = 'Trung bình'

    verdict, confidence, rationale = _verdict_from_score(risk_score, in_block, len(text_hits), in_white)

    return {
        "url": url,
        "domain": domain,
        "resolved_ip": resolved_ip,
        "blocklisted": in_block,
        "whitelisted": in_white,
        "text_match_count": len(text_hits),
        "indicators": indicators,
        "meta": meta,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "verdict": verdict,
        "confidence": confidence,
        "rationale": rationale,
    }
