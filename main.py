"""
Demo of the Rule-Constrained Adaptive Food Ranker (research prototype, NOT clinical advice).

    python main.py

1. Milestone patient (NHANES SEQN 134825 + scenario nausea) -> ranked foods with reasons
2. Dynamic test: same patient, State A vs State B -> rank_before / rank_after / rank_change
3. Persona evaluation for all models -> outputs/*.csv
"""
import pandas as pd
from src.paths import OUTPUTS
from src.recommender import recommend, format_recommendation
from evaluation.evaluate_personas import evaluate, evaluate_dynamic, dynamic_table


def main():
    OUTPUTS.mkdir(exist_ok=True)
    metrics_df, states, rules, foods = evaluate()

    print("=" * 70, "\n1) Milestone: PM_nausea\n" + "=" * 70)
    st = states["PM_nausea"]
    print("sources:", st.describe_sources())
    res = recommend(st, foods, rules, top_k=10)
    print(format_recommendation(res, top_k=10))
    res["ranking"].assign(reasons=res["ranking"].reasons.map(" | ".join)).to_csv(
        OUTPUTS / "milestone_PM_nausea_ranking.csv", index=False)

    print("\n" + "=" * 70, "\n2) Dynamic re-ranking: PM_stateA -> PM_stateB\n" + "=" * 70)
    t = dynamic_table(states, rules, foods, "PM_stateA", "PM_stateB")
    focus = ["chicken breast (roasted)", "congee with meat/poultry/seafood", "grilled shrimp",
             "New England clam chowder", "mashed potato (with milk)", "almonds (unsalted)"]
    print(t[t.short_name.isin(focus)][["short_name", "rank_before", "rank_after", "rank_change"]].to_string(index=False))

    print("\n" + "=" * 70, "\n3) Persona evaluation\n" + "=" * 70)
    metrics_df.to_csv(OUTPUTS / "persona_metrics.csv", index=False)
    dyn, dyn_sum = evaluate_dynamic(states, rules, foods)
    dyn.to_csv(OUTPUTS / "dynamic_reranking.csv", index=False)
    dyn_sum.to_csv(OUTPUTS / "dynamic_accuracy.csv", index=False)
    pd.set_option("display.width", 200)
    print(metrics_df.drop(columns="top_k").round(3).to_string(index=False))
    print(dyn_sum.to_string(index=False))


if __name__ == "__main__":
    main()
