"""
Cohort / data audit that needs the ORIGINAL NHANES XPT files (excluded from Git).
Run from the project root after preparing the raw files:

    python scripts/cohort_audit_xpt.py raw_data

First copy the FNDDS CSVs as described in data/README.md; the DR1IFF food-code
check also reads data/raw/fndds/survey_fndds_food.csv.

Prints: row counts, duplicate SEQN, cohort sizes (section 20), multi-cancer counts,
MCQ230D distribution, and how DR1IFF_L food codes link to FNDDS (no merge into patients).
Only pandas is needed (pandas.read_sas reads .xpt).
"""
import sys
from pathlib import Path
import pandas as pd

FILES = ["DEMO_L", "DIQ_L", "MCQ_L", "BMX_L", "GHB_L", "DR1TOT_L", "DR1IFF_L", "DRXFCD_L"]


def read_xpt(folder, name):
    path = next(Path(folder).rglob(f"{name}.[xX][pP][tT]"), None)
    return None if path is None else pd.read_sas(path, format="xport")


def describe(name, df):
    dup = df["SEQN"].duplicated().sum() if "SEQN" in df else "no SEQN"
    print(f"{name}: rows={len(df)}, cols={df.shape[1]}, duplicate SEQN={dup}")


def cohort_counts(demo, diq, mcq, ghb, bmx):
    """Section 20 counts. All inputs are person-level DataFrames keyed by SEQN."""
    p = demo[["SEQN"]].merge(diq[["SEQN", "DIQ010"]], on="SEQN", how="left") \
        .merge(mcq[["SEQN", "MCQ220", "MCQ230A", "MCQ230B", "MCQ230C", "MCQ230D"]], on="SEQN", how="left") \
        .merge(ghb[["SEQN", "LBXGH"]], on="SEQN", how="left") \
        .merge(bmx[["SEQN", "BMXBMI"]], on="SEQN", how="left")
    dm, ca = p.DIQ010.eq(1), p.MCQ220.eq(1)
    both = dm & ca
    cancer_cols = p[["MCQ230A", "MCQ230B", "MCQ230C"]]
    n_types = (cancer_cols.notna() & ~cancer_cols.isin([77, 99])).sum(axis=1)
    return {
        "all participants (DEMO)": len(p),
        "diabetes diagnosis (DIQ010=1)": int(dm.sum()),
        "cancer history (MCQ220=1)": int(ca.sum()),
        "diabetes + cancer": int(both.sum()),
        "+ HbA1c available": int((both & p.LBXGH.notna()).sum()),
        "+ BMI available": int((both & p.BMXBMI.notna()).sum()),
        "+ HbA1c and BMI available": int((both & p.LBXGH.notna() & p.BMXBMI.notna()).sum()),
        "diabetes + cancer with >=2 cancer types in A/B/C": int((both & (n_types >= 2)).sum()),
        "MCQ230D distribution (diabetes + cancer)": p.loc[both, "MCQ230D"].value_counts(dropna=False).to_dict(),
    }


def food_link(dr1iff, fndds_survey_csv):
    """How many DR1IFF food codes exist in FNDDS survey_fndds_food.food_code."""
    survey = pd.read_csv(fndds_survey_csv)
    codes = dr1iff["DR1IFDCD"].dropna().astype(int)
    return {"DR1IFF rows": len(dr1iff), "persons": dr1iff.SEQN.nunique(),
            "distinct food codes": codes.nunique(),
            "codes found in FNDDS": int(codes.drop_duplicates().isin(survey.food_code).sum())}


def main(folder):
    data = {n: read_xpt(folder, n) for n in FILES}
    for n, df in data.items():
        print(f"{n}: NOT FOUND") if df is None else describe(n, df)
    if all(data[n] is not None for n in ["DEMO_L", "DIQ_L", "MCQ_L", "GHB_L", "BMX_L"]):
        for k, v in cohort_counts(data["DEMO_L"], data["DIQ_L"], data["MCQ_L"], data["GHB_L"], data["BMX_L"]).items():
            print(f"  {k}: {v}")
    if data["DR1IFF_L"] is not None:
        survey = Path(__file__).resolve().parent.parent / "data" / "raw" / "fndds" / "survey_fndds_food.csv"
        if "DR1IFDCD" in data["DR1IFF_L"]:
            print("  DR1IFF -> FNDDS:", food_link(data["DR1IFF_L"], survey))
        else:
            print("  DR1IFF columns:", list(data["DR1IFF_L"].columns))
    if data["DRXFCD_L"] is not None:
        print("  DRXFCD columns:", list(data["DRXFCD_L"].columns))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
