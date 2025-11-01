# detectors/ai_detector.py
import requests
import json
from typing import Dict, Any, List

# --- Ollama Configuration ---
import os

def get_ollama_url():
    """
    Determines the correct Ollama URL based on the execution environment.
    """
    # Check for a common Docker environment indicator file.
    if os.path.exists('/.dockerenv'):
        # Running inside Docker, connect to the host machine.
        print("AI Detector: Running inside Docker. Using host.docker.internal for Ollama.")
        return "http://host.docker.internal:11434/api/generate"
    else:
        # Running on the host machine directly.
        print("AI Detector: Running on host. Using localhost for Ollama.")
        return "http://localhost:11434/api/generate"

# The application will connect to this Ollama server endpoint.
OLLAMA_URL = get_ollama_url()
# The user specified 'gemma3 4b'. In Ollama, this is typically just 'gemma'.
# The user can pull whichever Gemma version they prefer (e.g., 'ollama pull gemma:2b').
OLLAMA_MODEL = "gemma"

# --- Helper Function to Create the Prompt ---
def create_prompt(text: str, user_keywords: List[str]) -> str:
    """
    Creates a detailed, structured prompt for the Gemma model to ensure
    it performs the classification task correctly and returns a parsable JSON response.
    """

    # Base labels for classification
    candidate_labels = ["an toàn", "tin giả", "kích động", "lừa đảo", "tiêu cực"]

    # Add user-provided keywords to the list of labels
    if user_keywords:
        unique_user_keywords = set(kw.strip().lower() for kw in user_keywords if kw.strip())
        candidate_labels.extend(list(unique_user_keywords))

    # The instruction for the model
    # We ask it to act as a content moderator and return a JSON object.
    prompt = f"""
    Bạn là một trợ lý kiểm duyệt nội dung. Phân tích văn bản sau đây và phân loại nó vào một trong các nhãn sau: {', '.join(candidate_labels)}.

    Văn bản cần phân tích:
    ---
    {text}
    ---

    Hãy chỉ trả về một đối tượng JSON duy nhất có định dạng sau:
    {{
      "label": "<nhãn bạn đã chọn>",
      "reason": "<giải thích ngắn gọn cho lựa chọn của bạn>"
    }}
    """
    return prompt

# --- Analysis Function ---
def analyze_text_with_ai(text: str, user_keywords: List[str] = []) -> Dict[str, Any]:
    """
    Analyzes text by sending a request to a running Ollama server.
    """
    print(f"AI Detector: Sending text to Ollama model '{OLLAMA_MODEL}'...")

    # Construct the payload for the Ollama API
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": create_prompt(text, user_keywords),
        "stream": False,  # We want a single response, not a stream
        "format": "json"  # Request JSON output from the model
    }

    try:
        # Send the request to the Ollama server
        response = requests.post(OLLAMA_URL, json=payload, timeout=60) # 60-second timeout
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # Parse the JSON response from Ollama
        ollama_response = response.json()

        # The actual model output is a JSON string inside the 'response' key.
        # We need to parse this inner JSON.
        try:
            model_output = json.loads(ollama_response.get("response", "{}"))
            label = model_output.get("label", "không xác định")
            reason = model_output.get("reason", "Không có giải thích.")
        except json.JSONDecodeError:
            print(f"AI Detector: Error parsing JSON from model response: {ollama_response.get('response')}")
            raise ValueError("Phản hồi từ mô hình không phải là JSON hợp lệ.")

        # Map the result to our application's format
        risk_level = "Thấp"
        verdict = f"Nội dung được phân loại là '{label}'"

        risky_labels = ["tin giả", "kích động", "lừa đảo", "tiêu cực"]
        if label in risky_labels or label in user_keywords:
            risk_level = "Cao"
            verdict = f"Nội dung có dấu hiệu vi phạm, được phân loại là '{label}'"

        print(f"AI Detector: Analysis complete. Label='{label}'")

        return {
            "risk_score": 100 if risk_level == "Cao" else 0,
            "risk_level": risk_level,
            "verdict": verdict,
            "confidence": 100, # Confidence is harder to get from generative models, default to 100
            "rationale": reason,
            "ai_model": f"Ollama ({OLLAMA_MODEL})",
            "ai_label": label,
        }

    except requests.exceptions.ConnectionError:
        error_msg = f"Không thể kết nối đến Ollama server tại {OLLAMA_URL}. Hãy chắc chắn rằng Ollama đang chạy."
        print(f"AI Detector: CRITICAL - {error_msg}")
        return {
            "risk_level": "Không xác định",
            "verdict": "Lỗi kết nối AI",
            "confidence": 0,
            "rationale": error_msg,
        }
    except Exception as e:
        error_msg = f"Đã xảy ra lỗi khi giao tiếp với Ollama: {e}"
        print(f"AI Detector: ERROR - {error_msg}")
        return {
            "risk_level": "Không xác định",
            "verdict": "Lỗi phân tích AI",
            "confidence": 0,
            "rationale": error_msg,
        }
