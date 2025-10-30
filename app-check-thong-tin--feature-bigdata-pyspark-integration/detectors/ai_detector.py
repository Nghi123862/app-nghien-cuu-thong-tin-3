import torch
from transformers import pipeline, AutoTokenizer
from typing import Dict, Any, List

# --- Model Setup ---

# Using a more capable Zero-Shot Classification model.
# This allows us to classify text against arbitrary labels without re-training.
# It's more flexible than a simple sentiment model.
MODEL_NAME = "Moritz/bert-base-uncased-qqp-finetuned-squad-for-zero-shot"
CACHE_DIR = "huggingface_cache" # Ensures models are saved within the project dir

print(f"AI Detector: Loading Zero-Shot pipeline with model '{MODEL_NAME}'...")
try:
    # The pipeline handles tokenization and model loading for us.
    # On first run, this will download and cache the model, which may take time.
    classifier = pipeline("zero-shot-classification", model=MODEL_NAME, cache_dir=CACHE_DIR)
    print("AI Detector: Pipeline loaded successfully.")
except Exception as e:
    print(f"AI Detector: CRITICAL - Failed to load pipeline. AI features will not work. Error: {e}")
    classifier = None

# --- Analysis Function ---

def analyze_text_with_ai(text: str, user_keywords: List[str] = []) -> Dict[str, Any]:
    """
    Analyzes a given text using a Zero-Shot Classification model.
    It classifies the text against a set of candidate labels, including user-provided keywords.
    """
    if not classifier:
        return {
            "risk_level": "Không xác định",
            "verdict": "Lỗi: Mô hình AI chưa được tải",
            "confidence": 0,
            "rationale": "Không thể phân tích do lỗi tải mô hình AI. Vui lòng kiểm tra log.",
        }

    try:
        print(f"AI Detector: Analyzing text with {len(user_keywords)} user keywords...")

        # Base labels for general classification
        candidate_labels = ["an toàn", "tin giả", "kích động", "lừa đảo", "tiêu cực"]
        unique_user_keywords = set() # Initialize outside the if block

        # Add user-provided keywords to the list of labels to check
        # This makes the AI "listen" to user feedback
        if user_keywords:
            # Ensure no duplicates and clean up keywords
            unique_user_keywords = set(kw.strip().lower() for kw in user_keywords if kw.strip())
            candidate_labels.extend(list(unique_user_keywords))

        # 1. Classify the text against the candidate labels
        # The model will return scores for each label.
        results = classifier(text, candidate_labels, multi_label=False)

        # 2. Interpret the results
        top_result = results['labels'][0]
        confidence = results['scores'][0] * 100

        # 3. Map the result to our risk model
        risk_level = "Thấp"
        verdict = "Nội dung có vẻ an toàn"
        rationale = f"Mô hình AI cho rằng chủ đề chính là '{top_result}'."

        # If the top label is one of the risky categories or a user keyword, increase risk
        risky_labels = ["tin giả", "kích động", "lừa đảo", "tiêu cực"]
        if top_result in risky_labels or top_result in unique_user_keywords:
            risk_level = "Cao"
            verdict = "Nội dung có dấu hiệu vi phạm"
            rationale = f"Mô hình AI phát hiện chủ đề '{top_result}' với độ tin cậy cao."

        print(f"AI Detector: Analysis complete. Top Label={top_result}, Confidence={confidence:.2f}%")

        return {
            "risk_score": 100 if risk_level == "Cao" else 0,
            "risk_level": risk_level,
            "verdict": verdict,
            "confidence": round(confidence),
            "rationale": rationale,
            "ai_model": MODEL_NAME,
            "ai_label": top_result,
        }
    except Exception as e:
        print(f"AI Detector: An error occurred during analysis: {e}")
        return {
            "risk_level": "Không xác định",
            "verdict": "Lỗi trong quá trình phân tích AI",
            "confidence": 0,
            "rationale": str(e),
        }
