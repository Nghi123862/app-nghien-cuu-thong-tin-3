# preload_model.py
from transformers import pipeline
import os

# A reliable, well-maintained model for zero-shot classification.
MODEL_NAME = "facebook/bart-large-mnli"
CACHE_DIR = "huggingface_cache"

print(f"--- Pre-loading model: {MODEL_NAME} ---")
print(f"--- Cache directory: {os.path.abspath(CACHE_DIR)} ---")

try:
    # This command downloads the model and tokenizer and saves them to the cache_dir.
    pipeline("zero-shot-classification", model=MODEL_NAME, cache_dir=CACHE_DIR)
    print("--- Model pre-loading complete. ---")
except Exception as e:
    print(f"--- ERROR: Failed to pre-load model. ---")
    print(f"--- Reason: {e} ---")
    # Fail the Docker build if pre-loading fails.
    exit(1)
