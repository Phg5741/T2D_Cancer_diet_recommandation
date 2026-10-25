"""
recommend(): the whole pipeline in one call.

Patient State -> conditions -> hard filter -> violations -> ranking -> Top-K
"""
from src.condition_generator import generate_conditions
from src.hard_filter import apply_hard_filters
from src.violation_score import violation_matrix
from src.ranker import rank_foods


def select_pool(foods, rules):
    """Keep only food roles marked include=1 in rules/candidate_pool.csv."""
    pool = rules["pool"]
    roles = set(pool[pool.include == 1].food_role)
    return foods[foods.food_role.isin(roles)].reset_index(drop=True)


def add_portion_advice(ranking, kept, state, targets):
    """
    Poor appetite changes HOW MUCH to eat, not WHICH food ranks first (user decision 2026-10-09).
    recommended_portion_g = FNDDS default portion x poor_appetite_portion_factor (nutrition_targets.csv).
    """
    cols = ["fdc_id", "portion_g", "energy_kcal_portion", "protein_g_portion", "carbohydrate_g_portion"]
    out = ranking.merge(kept[cols], on="fdc_id", how="left")
    factor = targets.get("poor_appetite_portion_factor")
    if state is not None and state.poor_appetite is True and factor:
        out["portion_factor"], out["portion_note"] = factor, "reduced: poor appetite"
    else:
        out["portion_factor"], out["portion_note"] = 1.0, "default FNDDS portion"
    out["recommended_portion_g"] = out["portion_g"] * out["portion_factor"]
    for c in ["energy_kcal", "protein_g", "carbohydrate_g"]:
        out[f"recommended_{c}"] = out[f"{c}_portion"] * out["portion_factor"]
    return out


def recommend(state, foods, rules, top_k=10, scope="full", use_pool=True):
    """
    input : PatientState, candidate foods (food_loader.load_foods()), rules (rules_loader.load_rules()),
            top_k, scope ('full' | 'diabetes_only' | 'cancer_only' | 'static'),
            use_pool: restrict to roles in rules/candidate_pool.csv (percentiles use this pool)
    output: dict with 'ranking' (all kept foods), 'top_k', 'removed', 'conditions'
    """
    if use_pool:
        foods = select_pool(foods, rules)
    cond = generate_conditions(state, rules, scope)
    catalog = rules["conditions"]
    kept, removed = apply_hard_filters(foods, cond["active"], catalog)
    V, methods = violation_matrix(foods, cond["active"], catalog, rules["targets"])
    ranking = add_portion_advice(rank_foods(kept, V, catalog, methods), kept, state, rules["targets"])
    return {"ranking": ranking, "top_k": ranking.head(top_k), "removed": removed,
            "conditions": cond, "violations": V, "methods": methods}


def format_recommendation(result, top_k=10, max_reasons=4):
    """Readable text: rank | food | score | reasons."""
    c = result["conditions"]
    lines = ["Active conditions:"]
    for cid, info in c["active"].items():
        lines.append(f"  [{info['action']}] {cid}  <- {', '.join(info['rule_ids'])} ({'; '.join(info['reasons'])})")
    if c["inactive_unknown"]:
        lines.append(f"  skipped (input unknown): {', '.join(c['inactive_unknown'])}")
    for d in c["conflicts"]:
        lines.append(f"  conflict: dropped {d['dropped']} (kept {d['kept']}, {d['status']})")
    if len(result["removed"]):
        lines.append("Hard-filtered: " + "; ".join(
            f"{r.short_name} [{r.removed_by}]" for r in result["removed"].itertuples()))
    lines.append("")
    for r in result["ranking"].head(top_k).itertuples():
        lines.append(f"{r.rank:>2}. {r.short_name}  score={r.final_score:.3f}  "
                     f"portion {r.recommended_portion_g:.0f} g ({r.portion_note}; "
                     f"{r.recommended_energy_kcal:.0f} kcal, protein {r.recommended_protein_g:.1f} g)")
        for reason in r.reasons[:max_reasons]:
            lines.append(f"      {reason}")
        lines.append("      no hard restriction violation")
    return "\n".join(lines)
