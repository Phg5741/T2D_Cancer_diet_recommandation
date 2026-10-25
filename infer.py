"""
Inference: one patient input -> ranked food recommendations with reasons.

    python infer.py                                   # uses input/patient_input.json
    python infer.py --input input/my_patient.json     # another input file
    python infer.py --output output/other.txt

Writes output/final_results.txt (research prototype, NOT clinical advice).

Input JSON keys (null = unknown -> related rule skipped):
    patient_id, base_seqn (optional NHANES SEQN; its observed values are used when a key is null),
    age, sex, bmi, hba1c, diabetes_dx, insulin, diabetes_pills,
    cancers (names like "colon" or NHANES codes like 16; see rules/cancer_codes.csv),
    weight_loss_pct, poor_appetite, dysphagia, mouth_sore, nausea, vomiting,
    malabsorption, digestion_problem, treatment_stage, top_k
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.paths import ROOT, PROCESSED
from src.patient_state import PatientState, load_patient, OBSERVED_FIELDS, STATE_FIELDS
from src.food_loader import load_foods
from src.rules_loader import load_rules
from src.recommender import recommend, format_recommendation

NUMERIC = {"age", "bmi", "hba1c", "weight_kg", "weight_loss_pct", "diabetes_dx_age"}


def parse_cancers(values, code_to_label):
    """['colon', 16, 'Stomach'] -> [16, 35]. Unknown names raise an error (no guessing)."""
    label_to_code = {v.lower(): k for k, v in code_to_label.items()}
    codes = []
    for v in values or []:
        if isinstance(v, (int, float)) or str(v).isdigit():
            code = int(v)
            if code not in code_to_label:
                raise ValueError(f"unknown cancer code {v}; see rules/cancer_codes.csv")
        else:
            key = str(v).strip().lower().replace(" ", "_")
            if key not in label_to_code:
                raise ValueError(f"unknown cancer name '{v}'. Allowed: {', '.join(sorted(label_to_code))}")
            code = label_to_code[key]
        codes.append(code)
    return sorted(set(codes))


def build_state(data, rules):
    """
    input : dict from the input JSON
    output: PatientState. Values written in the input file are labelled 'user_input';
            values taken from base_seqn are 'nhanes_observed'.
    """
    if data.get("base_seqn") is not None:
        patients = pd.read_csv(PROCESSED / "patients_model.csv")
        base = patients[patients.seqn == int(data["base_seqn"])]
        if base.empty:
            raise ValueError(f"base_seqn {data['base_seqn']} not in patients_model.csv")
        st = load_patient(base.iloc[0])
    else:
        st = PatientState(patient_id="input")
    st.patient_id = data.get("patient_id") or st.patient_id
    for f in OBSERVED_FIELDS + STATE_FIELDS:
        if f == "cancers":
            if data.get("cancers"):
                st.cancers = parse_cancers(data["cancers"], rules["cancer_codes"])
                st.sources["cancers"] = "user_input"
            continue
        v = data.get(f)
        if v is None:
            continue
        setattr(st, f, float(v) if f in NUMERIC else v)
        st.sources[f] = "user_input"
    if st.cancers and st.cancer_history is None:
        st.cancer_history = True
        st.sources["cancer_history"] = "derived"
    return st


def input_section(st, rules):
    labels = rules["cancer_codes"]
    lines = ["[INPUT]  (value | source)"]
    for f, src in st.describe_sources().items():
        v = getattr(st, f)
        if f == "cancers":
            v = ", ".join(f"{labels.get(c)}({c})" for c in v) or None
        lines.append(f"  {f:<20} {str(v):<25} | {src}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(ROOT / "input" / "patient_input.json"))
    ap.add_argument("--output", default=str(ROOT / "output" / "final_results.txt"))
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rules, foods = load_rules(), load_foods()
    st = build_state(data, rules)
    top_k = int(data.get("top_k") or 10)
    res = recommend(st, foods, rules, top_k=top_k)

    text = "\n".join([
        "T2DCancer Adaptive Food Ranker - final results",
        "Research prototype. NOT a clinical decision system. Rules are provisional.",
        f"generated: {datetime.now():%Y-%m-%d %H:%M}   input: {args.input}",
        "=" * 78,
        input_section(st, rules),
        "=" * 78,
        "[CONDITIONS / FILTERS]",
        format_recommendation(res, top_k=top_k, max_reasons=6),
        "=" * 78,
        "Notes: score = 1 - mean(violation of active soft conditions); V=0 means satisfied.",
        "Cancer = history (NHANES MCQ230), not active cancer. Diabetes = diagnosis, not confirmed T2D.",
        "Food texture/taste flags are manual annotation (draft, not yet reviewed).",
    ])
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
