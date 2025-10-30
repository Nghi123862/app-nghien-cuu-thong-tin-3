# preload_model.py
# This script is designed to be run during the Docker build process.
# Its purpose is to download and cache the Hugging Face model,
# so the application doesn't need to download it at runtime.

from transformers import pipeline
import os

MODEL_NAME = "Moritz/bert-base-uncased-qqp-finetuned-squad-for-zero-shot"
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
    # Exit with a non-zero status code to fail the Docker build if pre-loading fails.
    exit(1)
