"""Load candidate foods = FNDDS nutrients (foods_model.csv) + manual annotation."""
import pandas as pd
from src.paths import PROCESSED

ANNOTATION_FLAGS = ["spicy", "acidic", "hard_texture", "soft", "puree", "oily",
                    "strong_smell", "hot_temperature", "thin_liquid"]


def load_foods(foods_path=PROCESSED / "foods_model.csv", annotation_path=PROCESSED / "food_annotation.csv"):
    """
    input : paths to foods_model.csv and food_annotation.csv
    output: one DataFrame, one row per candidate food (key = fdc_id)
    """
    foods = pd.read_csv(foods_path)
    ann = pd.read_csv(annotation_path)
    df = foods.merge(ann, on="fdc_id", how="inner", validate="1:1")
    if len(df) != len(ann):
        raise ValueError("some annotated foods are missing from foods_model.csv")
    for f in ANNOTATION_FLAGS:
        if df[f].isna().any():
            raise ValueError(f"annotation column {f} has empty values")
        df[f] = df[f].astype(int)
    return df.reset_index(drop=True)
