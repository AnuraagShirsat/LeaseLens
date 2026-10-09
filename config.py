# config.py
from pathlib import Path

MODEL_NAME = "gemma3:4b"          # swap to "gemma4:e4b" for accuracy

MAX_IMAGE_SIDE = 1600

# Real knowledge base for the analysis stage.
KB_PATH = Path("kb") / "karnataka_rules.json"

VAULT_DIR = "vault_data"
LAST_RESULT_PATH = "vault_data/last_result.json"