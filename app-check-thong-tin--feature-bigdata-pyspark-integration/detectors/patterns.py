import os
import re
from typing import List

# This module manages loading and compiling all keywords and patterns from the data directory.
# It ensures that all detectors use the same, up-to-date set of rules, including user feedback.

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def _load_lines_from_file(filename: str) -> List[str]:
    """Loads non-empty, non-comment lines from a file in the data directory."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []

    items: List[str] = []
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip().lower()
                if line and not line.startswith('#'):
                    items.append(line)
    except Exception as e:
        print(f"Warning: Could not read {filename}: {e}")
    return items

def _compile_keywords(keywords: List[str]) -> List[re.Pattern]:
    """Compiles a list of keyword strings into a list of regex patterns."""
    # We create a single, large regex pattern for efficiency.
    # It matches any of the keywords as whole words (\b).
    if not keywords:
        return []
    # Escape special regex characters in keywords
    escaped_keywords = [re.escape(kw) for kw in keywords]
    pattern_str = r"\b(" + "|".join(escaped_keywords) + r")\b"
    return [re.compile(pattern_str, re.IGNORECASE)]

# --- Load all raw keyword lists ---

# Main violation keywords from multiple files
violation_keywords_base = _load_lines_from_file('keywords_violation.txt')
violation_keywords_user = _load_lines_from_file('user_added_keywords.txt')

# Domain lists
DOMAINS_BLOCKLIST = set(_load_lines_from_file('domains_blocklist.txt'))
DOMAINS_WHITELIST = set(_load_lines_from_file('domains_whitelist.txt'))

# Phrase lists for text analysis
PHRASES_WHITE = _load_lines_from_file('phrases_whitelist.txt')
PHRASES_BLACK = _load_lines_from_file('phrases_blacklist.txt')

# --- Combine and Compile Patterns ---

# Combine base and user-added keywords, ensuring uniqueness
all_violation_keywords = sorted(list(set(violation_keywords_base + violation_keywords_user)))

# Compile the combined list into regex patterns for efficient searching.
# This is now the single source of truth for violation patterns.
VIOLATION_PATTERNS = _compile_keywords(all_violation_keywords)

def load_user_keywords() -> List[str]:
    """
    Utility function specifically for the UI to load and pass user keywords to the AI model.
    """
    return _load_lines_from_file('user_added_keywords.txt')

print(f"Loaded {len(all_violation_keywords)} total violation keywords ({len(violation_keywords_user)} from user).")
