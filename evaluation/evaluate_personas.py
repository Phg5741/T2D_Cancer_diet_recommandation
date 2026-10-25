"""
Run every persona through 4 models and compute the metrics.

Models (scope): static | diabetes_only | cancer_only | full (adaptive)
Safety and nutrition metrics are always judged against the FULL rule set,
so a baseline that ignores a rule is penalised for breaking it.
unsafe_rate is a stress test on ALL annotated foods (incl. drinks and alcohol, use_pool=False);
the other metrics use the default candidate pool (rules/candidate_pool.csv).

Outputs: outputs/persona_metrics.csv, outputs/dynamic_reranking.csv
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from src.paths import PERSONAS, PROCESSED, OUTPUTS
from src.patient_state import load_persona
from src.food_loader import load_foods
from src.rules_loader import load_rules
from src.recommender import recommend
from evaluation import metrics

SCOPES = ["static", "diabetes_only", "cancer_only", "full"]


def load_all():
    rules = load_rules()
    foods = load_foods()
    patients = pd.read_csv(PROCESSED / "patients_model.csv")
    personas = pd.read_csv(PERSONAS / "personas.csv", dtype=str)
    states = {r["persona_id"]: load_persona(r, patients) for _, r in personas.iterrows()}
    return rules, foods, states


def rank_dict(result):
    return dict(zip(result["ranking"].fdc_id, result["ranking"]["rank"]))


def evaluate(top_k=10):
    rules, foods, states = load_all()
    expected = pd.read_csv(PERSONAS / "expected_rankings.csv")
    catalog = rules["conditions"]
    rows = []
    for pid, st in states.items():
        full = recommend(st, foods, rules, top_k, "full")
        forbidden = set(recommend(st, foods, rules, top_k, "full", use_pool=False)["removed"].fdc_id)
        numeric = [c for c in full["violations"].columns if catalog.loc[c, "kind"] == "numeric"]
        exp = expected[expected.persona_id == pid]
        for scope in SCOPES:
            res = full if scope == "full" else recommend(st, foods, rules, top_k, scope)
            top_ids = res["top_k"].fdc_id.tolist()
            stress_ids = recommend(st, foods, rules, top_k, scope, use_pool=False)["top_k"].fdc_id.tolist()
            row = {"persona_id": pid, "model": scope,
                   "n_active_conditions": len(res["conditions"]["active"]),
                   "unsafe_rate@k_all_foods": metrics.unsafe_recommendation_rate(stress_ids, forbidden),
                   "nutrition_violation@k": metrics.nutrition_target_violation(full["violations"], top_ids, numeric),
                   "top_k": " | ".join(res["top_k"].short_name)}
            if len(exp):
                exp_rank = dict(zip(exp.fdc_id, exp.expected_rank))
                order = [f for f in res["ranking"].fdc_id if f in exp_rank]
                row["ndcg@expected"] = metrics.ndcg_at_k(order, exp_rank, len(exp_rank))
                row["top2_agreement"] = metrics.top_k_agreement(order, sorted(exp_rank, key=exp_rank.get), 2)
            rows.append(row)
    return pd.DataFrame(rows), states, rules, foods


def dynamic_table(states, rules, foods, before, after, scope="full"):
    """rank_before / rank_after / rank_change for every food (change > 0 = moved up)."""
    rb = recommend(states[before], foods, rules, scope=scope)["ranking"]
    ra = recommend(states[after], foods, rules, scope=scope)["ranking"]
    t = rb[["fdc_id", "short_name", "rank", "final_score"]].merge(
        ra[["fdc_id", "rank", "final_score"]], on="fdc_id", suffixes=("_before", "_after"))
    t["rank_change"] = t["rank_before"] - t["rank_after"]
    t.insert(0, "transition", f"{before}->{after}")
    return t.sort_values("rank_after")


def evaluate_dynamic(states, rules, foods):
    exp = pd.read_csv(PERSONAS / "dynamic_expectations.csv")
    tables, summary = [], []
    for (b, a), grp in exp.groupby(["persona_before", "persona_after"]):
        for scope in SCOPES:
            t = dynamic_table(states, rules, foods, b, a, scope)
            if scope == "full":
                tables.append(t)
            rb = dict(zip(t.fdc_id, t.rank_before))
            ra = dict(zip(t.fdc_id, t.rank_after))
            acc = metrics.dynamic_reranking_accuracy(rb, ra, list(zip(grp.fdc_id, grp.expected_direction)))
            summary.append({"transition": f"{b}->{a}", "model": scope, "dynamic_accuracy": acc})
    return pd.concat(tables), pd.DataFrame(summary)


if __name__ == "__main__":
    OUTPUTS.mkdir(exist_ok=True)
    m, states, rules, foods = evaluate()
    m.to_csv(OUTPUTS / "persona_metrics.csv", index=False)
    dyn, dyn_sum = evaluate_dynamic(states, rules, foods)
    dyn.to_csv(OUTPUTS / "dynamic_reranking.csv", index=False)
    dyn_sum.to_csv(OUTPUTS / "dynamic_accuracy.csv", index=False)
    pd.set_option("display.width", 200, "display.max_colwidth", 60)
    print(m.drop(columns="top_k").round(3).to_string(index=False))
    print(dyn_sum.to_string(index=False))
