"""
Build data/processed/foods_all_nutrients.csv (all 5,431 FNDDS foods with nutrients)
and data/processed/foods_model.csv (only the annotated candidate foods).

Data conventions used by this script:
- food_nutrient.amount is per 100 g of food (Download_API_Field_Descriptions.xlsx).
- In this FNDDS download, food_nutrient.nutrient_id joins nutrient.nutrient_nbr
  (NOT nutrient.id). Joining on nutrient.id gives 0 matches.
- food.fdc_id == survey_fndds_food.fdc_id (1:1); food_code comes from survey_fndds_food.
- Portion: food_portion row with modifier 90000 ("Quantity not specified") is used as the
  default portion gram weight.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from src.paths import RAW_FNDDS, PROCESSED

# nutrient_nbr -> our column name (checked against nutrient.csv names/units)
NUTRIENTS = {
    208: "energy_kcal",          # Energy, KCAL
    205: "carbohydrate_g",       # Carbohydrate, by difference, G
    269: "total_sugar_g",        # Total Sugars, G
    203: "protein_g",            # Protein, G
    204: "total_fat_g",          # Total lipid (fat), G
    606: "saturated_fat_g",      # Fatty acids, total saturated, G
    291: "fiber_g",              # Fiber, total dietary, G
    307: "sodium_mg",            # Sodium, Na, MG
    221: "alcohol_g",            # Alcohol, ethyl, G
    255: "water_g",              # Water, G
}
QNS_PORTION_CODE = 90000  # "Quantity not specified"


def load_nutrients_wide():
    fn = pd.read_csv(RAW_FNDDS / "food_nutrient.csv", usecols=["fdc_id", "nutrient_id", "amount"])
    fn = fn[fn.nutrient_id.isin(NUTRIENTS)]
    wide = fn.pivot_table(index="fdc_id", columns="nutrient_id", values="amount", aggfunc="first")
    wide = wide.rename(columns=NUTRIENTS).add_suffix("_100g").reset_index()
    return wide


def load_default_portion():
    fp = pd.read_csv(RAW_FNDDS / "food_portion.csv")
    qns = fp[(fp.modifier == QNS_PORTION_CODE) & (fp.gram_weight > 0)]
    qns = qns[["fdc_id", "gram_weight", "portion_description"]].rename(
        columns={"gram_weight": "portion_g", "portion_description": "portion_description"})
    qns["portion_source"] = "FNDDS_quantity_not_specified"
    return qns


def build_all():
    food = pd.read_csv(RAW_FNDDS / "food.csv")
    survey = pd.read_csv(RAW_FNDDS / "survey_fndds_food.csv")
    cat = pd.read_csv(RAW_FNDDS / "wweia_food_category.csv")
    df = (food[["fdc_id", "description"]].rename(columns={"description": "food_name"})
          .merge(survey[["fdc_id", "food_code", "wweia_category_number"]], on="fdc_id", how="inner", validate="1:1")
          .merge(cat.rename(columns={"wweia_food_category": "wweia_category_number",
                                     "wweia_food_category_description": "wweia_category"}),
                 on="wweia_category_number", how="left", validate="m:1")
          .merge(load_nutrients_wide(), on="fdc_id", how="inner", validate="1:1")
          .merge(load_default_portion(), on="fdc_id", how="left", validate="1:1"))
    for col in [c for c in df.columns if c.endswith("_100g")]:
        df[col.replace("_100g", "_portion")] = df[col] * df["portion_g"] / 100
    df["protein_g_per_100kcal"] = (df["protein_g_100g"] / df["energy_kcal_100g"] * 100).where(df["energy_kcal_100g"] > 0)
    df["alcohol_flag"] = (df["alcohol_g_100g"] > 0).astype(int)  # derived from nutrient data, not annotation
    return df


def main():
    all_foods = build_all()
    all_foods.to_csv(PROCESSED / "foods_all_nutrients.csv", index=False)
    ann = pd.read_csv(PROCESSED / "food_annotation.csv")
    missing = set(ann.fdc_id) - set(all_foods.fdc_id)
    if missing:
        raise ValueError(f"annotated fdc_id not found in FNDDS: {missing}")
    model = all_foods[all_foods.fdc_id.isin(ann.fdc_id)].copy()
    if model.portion_g.isna().any():
        raise ValueError("candidate food without default portion: " + str(model[model.portion_g.isna()].food_name.tolist()))
    model.to_csv(PROCESSED / "foods_model.csv", index=False)
    print(f"foods_all_nutrients.csv: {len(all_foods)} foods "
          f"({all_foods.portion_g.isna().sum()} without default portion)")
    print(f"foods_model.csv: {len(model)} candidate foods")


if __name__ == "__main__":
    main()
