# detectors/ai_detector.py
from transformers import pipeline
from typing import Dict, Any, List

# --- Model Setup ---
# This model name must match the one in preload_model.py
MODEL_NAME = "facebook/bart-large-mnli"
CACHE_DIR = "huggingface_cache"

# --- Model Loading with Error Handling ---
classifier = None
model_loading_error = None

print(f"AI Detector: Loading Zero-Shot pipeline with model '{MODEL_NAME}'...")
try:
    # This should load the model from the cache populated during the Docker build.
    classifier = pipeline("zero-shot-classification", model=MODEL_NAME, cache_dir=CACHE_DIR)
    print("AI Detector: Pipeline loaded successfully.")
except Exception as e:
    model_loading_error = f"Không thể tải mô hình AI '{MODEL_NAME}'. Lý do: {e}"
    print(f"AI Detector: CRITICAL - {model_loading_error}")


# --- Analysis Function ---
def analyze_text_with_ai(text: str, user_keywords: List[str] = []) -> Dict[str, Any]:
    """
    Analyzes text using the pre-loaded Zero-Shot Classification model.
    """
    if not classifier:
        return {
            "risk_level": "Không xác định",
            "verdict": "Lỗi: Mô hình AI chưa được tải",
            "confidence": 0,
            "rationale": model_loading_error or "Mô hình AI không khả dụng.",
        }

    try:
        candidate_labels = ["an toàn", "tin giả", "kích động", "lừa đảo", "tiêu cực"]
        if user_keywords:
            unique_user_keywords = set(kw.strip().lower() for kw in user_keywords if kw.strip())
            candidate_labels.extend(list(unique_user_keywords))

        results = classifier(text, candidate_labels, multi_label=False)

        top_result = results['labels'][0]
        confidence = results['scores'][0] * 100

        risk_level = "Thấp"
        verdict = f"Nội dung được phân loại là '{top_result}'"

        risky_labels = ["tin giả", "kích động", "lừa đảo", "tiêu cực"]
        # Also consider user-added keywords as risky for classification purposes
        if top_result in risky_labels or top_result in user_keywords:
            risk_level = "Cao"
            verdict = f"Nội dung có dấu hiệu vi phạm, được phân loại là '{top_result}'"

        return {
            "risk_score": 100 if risk_level == "Cao" else 0,
            "risk_level": risk_level,
            "verdict": verdict,
            "confidence": round(confidence),
            "rationale": f"Mô hình AI xác định chủ đề là '{top_result}'.",
            "ai_model": MODEL_NAME,
            "ai_label": top_result,
        }
    except Exception as e:
        return {
            "risk_level": "Không xác định",
            "verdict": "Lỗi trong quá trình phân tích AI",
            "confidence": 0,
            "rationale": str(e),
        }
