"""
Reproducible audit of the files that ARE in this folder (patients_final.csv + FNDDS CSVs).

    python scripts/audit_uploads.py > outputs/audit_output.txt
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from src.paths import RAW_FNDDS, RAW_NHANES

pd.set_option("display.width", 200)


def audit_patients():
    p = pd.read_csv(RAW_NHANES / "patients_final.csv")
    print("== patients_final.csv", p.shape, "duplicate SEQN:", p.SEQN.duplicated().sum())
    print(pd.DataFrame({"dtype": p.dtypes.astype(str), "missing_ratio": p.isna().mean().round(3)}).T.to_string())
    for c in ["RIAGENDR", "DIQ010", "MCQ220", "DIQ050", "DIQ070", "DIQ060U", "MCQ230A", "MCQ230B", "MCQ230C", "MCQ230D"]:
        print(c, p[c].value_counts(dropna=False).sort_index().to_dict())
    print(p[["RIDAGEYR", "DID040", "DID060", "BMXBMI", "LBXGH"]].describe().round(2).to_string())
    cols = p[["MCQ230A", "MCQ230B", "MCQ230C"]]
    n_types = (cols.notna() & ~cols.isin([77, 99])).sum(axis=1)
    print("number of known cancer types per person:", n_types.value_counts().sort_index().to_dict())
    print("HbA1c available:", p.LBXGH.notna().sum(), " BMI available:", p.BMXBMI.notna().sum(),
          " both:", (p.LBXGH.notna() & p.BMXBMI.notna()).sum())


def audit_fndds():
    print("\n== FNDDS CSV files")
    for f in sorted(RAW_FNDDS.glob("*.csv")):
        df = pd.read_csv(f, low_memory=False)
        print(f"{f.name}: rows={len(df)}, cols={df.shape[1]}, columns={list(df.columns)}")
    fn = pd.read_csv(RAW_FNDDS / "food_nutrient.csv")
    n = pd.read_csv(RAW_FNDDS / "nutrient.csv")
    ids = set(fn.nutrient_id)
    print("food_nutrient.nutrient_id matches nutrient.id:", len(ids & set(n.id)),
          "| matches nutrient.nutrient_nbr:", len(ids & set(n.nutrient_nbr.dropna().astype(int))),
          "| distinct nutrient_id:", len(ids))
    food = pd.read_csv(RAW_FNDDS / "food.csv")
    print("foods:", len(food), "| foods with nutrients:", fn.fdc_id.nunique(),
          "| without:", food[~food.fdc_id.isin(fn.fdc_id)].description.tolist())
    fp = pd.read_csv(RAW_FNDDS / "food_portion.csv")
    qns = fp[fp.modifier == 90000]
    print("foods with 'Quantity not specified' portion:", qns.fdc_id.nunique(),
          "| with gram_weight 0:", (qns.gram_weight == 0).sum())
    fa = pd.read_csv(RAW_FNDDS / "food_attribute.csv")
    print("food_attribute names:", fa.name.value_counts().to_dict())


if __name__ == "__main__":
    audit_patients()
    audit_fndds()
