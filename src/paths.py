"""All file locations in one place, so every script uses the same paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_FNDDS = ROOT / "data" / "raw" / "fndds"
RAW_NHANES = ROOT / "data" / "raw" / "nhanes_csv"
PROCESSED = ROOT / "data" / "processed"
RULES = ROOT / "rules"
PERSONAS = ROOT / "personas"
OUTPUTS = ROOT / "outputs"
