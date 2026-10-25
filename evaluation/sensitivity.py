"""
What changes if the team enables a disabled rule? (does NOT edit the rule files)

    python -m evaluation.sensitivity GEN-01 GEN-02
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from evaluation.evaluate_personas import load_all, dynamic_table
from evaluation import metrics
from src.recommender import recommend


def with_rules_enabled(rules, rule_ids):
    r = dict(rules)
    for key in ("state_rules", "cancer_rules"):
        t = rules[key].copy()
        t.loc[t.rule_id.isin(rule_ids), "enabled"] = 1
        r[key] = t
    return r


def compare(rule_ids, personas=("PM_nausea", "PA_base", "PA_dys"), top_k=5):
    rules, foods, states = load_all()
    variant = with_rules_enabled(rules, rule_ids)
    rows = []
    for pid in personas:
        for name, rs in (("default", rules), ("+" + "+".join(rule_ids), variant)):
            top = recommend(states[pid], foods, rs, top_k)["top_k"]
            rows.append({"persona": pid, "rules": name, "top_k": " | ".join(top.short_name)})
    exp = pd.read_csv(Path(__file__).resolve().parent.parent / "personas" / "dynamic_expectations.csv")
    for name, rs in (("default", rules), ("variant", variant)):
        for (b, a), g in exp.groupby(["persona_before", "persona_after"]):
            t = dynamic_table(states, rs, foods, b, a)
            acc = metrics.dynamic_reranking_accuracy(dict(zip(t.fdc_id, t.rank_before)),
                                                     dict(zip(t.fdc_id, t.rank_after)),
                                                     list(zip(g.fdc_id, g.expected_direction)))
            rows.append({"persona": f"{b}->{a}", "rules": name, "top_k": f"dynamic_accuracy={acc:.2f}"})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ids = sys.argv[1:] or ["GEN-01", "GEN-02"]
    pd.set_option("display.width", 250, "display.max_colwidth", 200)
    print(compare(ids).to_string(index=False))
