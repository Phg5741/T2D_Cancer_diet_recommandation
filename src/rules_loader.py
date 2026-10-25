"""Read the rule / config CSV files. No medical numbers live in Python code."""
import pandas as pd
from src.paths import RULES


def load_targets():
    """nutrition_targets.csv -> {parameter: float or None}  (blank = not set)."""
    t = pd.read_csv(RULES / "nutrition_targets.csv")
    return {r.parameter: (None if pd.isna(r.value) else float(r.value)) for r in t.itertuples()}


def load_rules():
    """Return a dict with every rule table the recommender needs."""
    return {
        "conditions": pd.read_csv(RULES / "conditions.csv").set_index("condition_id"),
        "cancer_rules": pd.read_csv(RULES / "cancer_restriction.csv"),
        "state_rules": pd.read_csv(RULES / "symptom_restriction.csv"),
        "conflicts": pd.read_csv(RULES / "conflict_resolution.csv"),
        "static": pd.read_csv(RULES / "static_baseline.csv"),
        "cancer_codes": pd.read_csv(RULES / "cancer_codes.csv").set_index("code")["label"].to_dict(),
        "targets": load_targets(),
        "pool": pd.read_csv(RULES / "candidate_pool.csv"),
    }
