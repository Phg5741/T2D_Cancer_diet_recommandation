"""
Patient state = what the recommender knows about one patient right now.

Every value carries a source label so observed NHANES data is never confused
with a made-up scenario value:
    nhanes_observed   measured/asked in NHANES (patients_final.csv)
    derived           calculated from other values (e.g. hba1c_above_target)
    scenario          set by a persona (synthetic, NOT measured)
    unavailable       nobody provided it -> treated as unknown
"""
from dataclasses import dataclass, field
import pandas as pd

OBSERVED_FIELDS = ["age", "sex", "bmi", "hba1c", "insulin", "diabetes_pills",
                   "diabetes_dx", "diabetes_dx_age", "cancer_history", "cancers", "more_than_3_cancers", "weight_kg"]
STATE_FIELDS = ["weight_loss_pct", "poor_appetite", "dysphagia", "mouth_sore", "nausea",
                "vomiting", "malabsorption", "digestion_problem", "treatment_stage"]


@dataclass
class PatientState:
    patient_id: str
    age: float = None
    sex: str = None
    bmi: float = None
    hba1c: float = None
    weight_kg: float = None
    insulin: bool = None
    diabetes_pills: bool = None
    diabetes_dx: bool = None
    diabetes_dx_age: float = None
    cancer_history: bool = None                    # MCQ220 == 1 (history, not active cancer)
    cancers: list = field(default_factory=list)   # all NHANES cancer codes, e.g. [16, 35]
    more_than_3_cancers: bool = False              # MCQ230D == 66, NOT a cancer type
    weight_loss_pct: float = None
    poor_appetite: bool = None
    dysphagia: bool = None
    mouth_sore: bool = None
    nausea: bool = None
    vomiting: bool = None
    malabsorption: bool = None
    digestion_problem: bool = None
    treatment_stage: str = None
    sources: dict = field(default_factory=dict)    # field name -> source label

    def describe_sources(self):
        """Return {field: source} for every field (unknown fields marked 'unavailable')."""
        names = OBSERVED_FIELDS + STATE_FIELDS
        return {n: self.sources.get(n, "unavailable") for n in names}


def _clean(v):
    """pandas missing values -> None; numpy bools/numbers -> python types."""
    if v is None or (not isinstance(v, (list, str)) and pd.isna(v)):
        return None
    if isinstance(v, str):
        low = v.strip().lower()
        if low in ("true", "1", "yes"):
            return True
        if low in ("false", "0", "no"):
            return False
        if low == "":
            return None
        return v.strip()
    return v.item() if hasattr(v, "item") else v


def parse_cancer_codes(text):
    """'16;35' -> [16, 35]. Empty / missing -> []."""
    if text is None or (not isinstance(text, str) and pd.isna(text)) or str(text).strip() == "":
        return []
    return [int(float(c)) for c in str(text).split(";") if c.strip()]


def load_patient(row):
    """
    input : one row (dict or pandas Series) of data/processed/patients_model.csv
    output: PatientState with observed values filled, symptoms left unknown
    """
    row = dict(row)
    st = PatientState(patient_id=row["patient_id"])
    for f in OBSERVED_FIELDS:
        if f == "cancers":
            st.cancers = parse_cancer_codes(row.get("cancer_codes"))
            st.sources["cancers"] = "nhanes_observed"
            continue
        v = _clean(row.get(f))
        if v is not None:
            setattr(st, f, v)
            st.sources[f] = "nhanes_observed"
    return st


def load_persona(persona_row, patients_df=None):
    """
    input : one row of personas/personas.csv (+ patients_model DataFrame if the persona
            is based on a real NHANES SEQN)
    output: PatientState. Observed values come from NHANES when base_seqn is given;
            any value written in the persona file is labelled 'scenario'.
    """
    row = dict(persona_row)
    base_seqn = _clean(row.get("base_seqn"))
    if base_seqn is not None and patients_df is not None:
        base = patients_df[patients_df.seqn == int(base_seqn)]
        if base.empty:
            raise ValueError(f"base_seqn {base_seqn} not in patients_model.csv")
        st = load_patient(base.iloc[0])
    else:
        st = PatientState(patient_id=row["persona_id"])
    st.patient_id = row["persona_id"]
    for f in OBSERVED_FIELDS + STATE_FIELDS:
        key = "cancer_codes" if f == "cancers" else f
        v = row.get(key)
        if f == "cancers":
            codes = parse_cancer_codes(v)
            if codes:
                st.cancers, st.sources["cancers"] = codes, "scenario"
            continue
        v = _clean(v)
        if v is not None:
            if f in ("age", "bmi", "hba1c", "weight_kg", "weight_loss_pct", "diabetes_dx_age"):
                v = float(v)
            setattr(st, f, v)
            st.sources[f] = "scenario"
    return st


def diabetes_label(state, targets):
    """
    Operational diabetes label (kept separate from the recommender on purpose).
    Default: 'diabetes_dx' (DIQ010=1, type not confirmed).
    If nutrition_targets.csv has t1d_exclusion_max_dx_age filled, patients diagnosed before
    that age who use insulin are labelled 'possible_t1d'; others 'probable_t2d'.
    """
    if not state.diabetes_dx:
        return "no_diabetes_dx"
    cut = targets.get("t1d_exclusion_max_dx_age")
    if cut is None:
        return "diabetes_dx"
    if state.diabetes_dx_age is None or state.insulin is None:
        return "diabetes_dx_type_unknown"
    if state.diabetes_dx_age < cut and state.insulin:
        return "possible_t1d"
    return "probable_t2d"
