"""
Ranking: FinalScore_i = 1 - mean(V_ij over active soft conditions j).
Every active condition counts equally (no hand-made weights).
Binary and numeric means are also returned so they can be inspected separately.
"""
import pandas as pd


def _reason_lines(fdc_id, V, catalog, foods_by_id, methods):
    lines = []
    for cid in V.columns:
        v = V.at[fdc_id, cid]
        info = catalog.loc[cid]
        if info.kind == "numeric":
            value = foods_by_id.at[fdc_id, info.feature]
            detail = f"{info.feature}={value:.1f}, {methods[cid]}"
        else:
            detail = f"{info.feature}={int(foods_by_id.at[fdc_id, info.feature])}"
        sign = "+" if v == 0 else "-"
        lines.append((v, f"{sign} {cid} (V={v:.2f}; {detail})"))
    lines.sort(key=lambda t: -t[0])
    return [text for _, text in lines]


def rank_foods(kept_foods, V, catalog, methods):
    """
    input : foods left after hard filter, violation matrix (all candidates), catalog, methods
    output: DataFrame sorted by rank with final_score, mean violations and reasons
    """
    ids = kept_foods["fdc_id"].tolist()
    Vk = V.loc[ids] if len(V.columns) else pd.DataFrame(index=ids)
    binary_cols = [c for c in Vk.columns if catalog.loc[c, "kind"] == "binary"]
    numeric_cols = [c for c in Vk.columns if catalog.loc[c, "kind"] == "numeric"]
    out = kept_foods[["fdc_id", "food_code", "short_name", "food_name"]].copy().set_index("fdc_id")
    out["n_conditions"] = len(Vk.columns)
    out["mean_violation"] = Vk.mean(axis=1) if len(Vk.columns) else 0.0
    out["binary_mean_violation"] = Vk[binary_cols].mean(axis=1) if binary_cols else float("nan")
    out["numeric_mean_violation"] = Vk[numeric_cols].mean(axis=1) if numeric_cols else float("nan")
    out["final_score"] = 1 - out["mean_violation"]
    foods_by_id = kept_foods.set_index("fdc_id")
    out["reasons"] = [_reason_lines(i, Vk, catalog, foods_by_id, methods) for i in out.index]
    out = out.reset_index().sort_values(["final_score", "short_name"], ascending=[False, True])
    out["rank"] = out["final_score"].rank(ascending=False, method="min").astype(int)
    return out.reset_index(drop=True)
