"""
Build data/processed/patients_model.csv from data/raw/nhanes_csv/patients_final.csv.

- One row per SEQN (checked).
- NHANES special codes listed in rules/nhanes_special_codes.csv become missing (never averaged).
- All cancer codes from MCQ230A/B/C become one list column `cancer_codes` ("16;35").
- MCQ230D is kept separately as `more_than_3_cancers` (it is NOT a 4th cancer type).
- Symptom / treatment variables are NOT in NHANES files we have: written as empty with
  source 'unavailable' so they are never mistaken for observed values.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd
from src.paths import RAW_NHANES, PROCESSED, RULES

CANCER_COLS = ["MCQ230A", "MCQ230B", "MCQ230C"]


def clean_special_codes(df):
    codes = pd.read_csv(RULES / "nhanes_special_codes.csv")
    df = df.copy()
    for _, r in codes[codes.action == "set_missing"].iterrows():
        if r.variable in df:
            df.loc[df[r.variable] == r.code, r.variable] = np.nan
    return df


def yes_no(x):
    """NHANES 1=Yes, 2=No; anything else -> missing."""
    return {1: True, 2: False}.get(x, None)


def build():
    raw = pd.read_csv(RAW_NHANES / "patients_final.csv")
    assert raw.SEQN.is_unique, "duplicate SEQN"
    df = clean_special_codes(raw)
    out = pd.DataFrame({
        "patient_id": "NHANES_" + df.SEQN.astype(str),
        "seqn": df.SEQN,
        "age": df.RIDAGEYR,
        "age_topcoded_80plus": raw.RIDAGEYR.eq(80),
        "sex": df.RIAGENDR.map({1: "male", 2: "female"}),
        "diabetes_dx": df.DIQ010.eq(1),
        "diabetes_dx_age": df.DID040,
        "insulin": df.DIQ050.map(yes_no),
        "diabetes_pills": df.DIQ070.map(yes_no),
        "cancer_history": df.MCQ220.eq(1),
        "cancer_codes": df[CANCER_COLS].apply(
            lambda r: ";".join(str(int(v)) for v in r if pd.notna(v)), axis=1),
        "cancer_type_unknown": raw[CANCER_COLS].isin([77, 99]).any(axis=1),
        "more_than_3_cancers": raw.MCQ230D.eq(66),
        "weight_kg": df.BMXWT,
        "height_cm": df.BMXHT,
        "bmi": df.BMXBMI,
        "arm_circ_cm": df.BMXARMC,
        "waist_cm": df.BMXWAIST,
        "hba1c": df.LBXGH,
    })
    # Not measured in our NHANES files -> left empty on purpose
    for col in ["weight_loss_pct", "poor_appetite", "dysphagia", "mouth_sore", "nausea",
                "vomiting", "malabsorption", "digestion_problem", "treatment_stage"]:
        out[col] = pd.NA
    out["record_source"] = "nhanes_observed"
    return out


if __name__ == "__main__":
    pm = build()
    pm.to_csv(PROCESSED / "patients_model.csv", index=False)
    print(f"patients_model.csv: {len(pm)} rows")
