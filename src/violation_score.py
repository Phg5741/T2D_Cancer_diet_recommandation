"""
Violation V_ij in [0, 1] for food i and condition j (0 = no violation, 1 = maximal).

binary  avoid  : V = 1 if the food has the flag, else 0
binary  prefer : V = 0 if the food has the flag, else 1
numeric (relative_rank, default): V = share of the OTHER candidate foods that are better
        than this food on that feature (percentile within the candidate set).
        Used because no verified per-portion clinical target exists yet.
numeric (threshold, only if nutrition_targets.csv value is filled):
        upper limit  V = clip((x - L) / L, 0, 1)
        lower target V = clip((T - x) / T, 0, 1)
"""
import numpy as np
import pandas as pd


def binary_violation(flag_values, direction):
    v = flag_values.astype(float)
    return v if direction == "avoid" else 1.0 - v


def relative_rank_violation(values, direction):
    """Percentile of how many foods are better. Ties share the best rank."""
    n = len(values)
    if n <= 1:
        return pd.Series(0.0, index=values.index)
    if direction == "lower_better":
        better = values.rank(method="min") - 1           # foods strictly lower
    else:
        better = (-values).rank(method="min") - 1        # foods strictly higher
    return better / (n - 1)


def threshold_violation(values, direction, target):
    if direction == "lower_better":
        return ((values - target) / target).clip(0, 1)
    return ((target - values) / target).clip(0, 1)


def calculate_violation(foods, condition_id, catalog, targets):
    """
    input : ALL candidate foods (before hard filter, so filtering does not shift percentiles),
            one condition id, catalog, targets
    output: (Series of V per food, method used)
    """
    info = catalog.loc[condition_id]
    x = foods[info.feature]
    if info.kind == "binary":
        return binary_violation(x, info.direction), "flag"
    target = targets.get(info.target_param) if isinstance(info.target_param, str) else None
    if target:
        return threshold_violation(x, info.direction, target), "threshold"
    return relative_rank_violation(x, info.direction), "relative_rank"


def violation_matrix(foods, conditions, catalog, targets):
    """
    output: DataFrame (index = fdc_id, one column per SOFT active condition) and
            {condition_id: method}
    """
    cols, methods = {}, {}
    for cid, c in conditions.items():
        if c["action"] != "soft":
            continue
        cols[cid], methods[cid] = calculate_violation(foods, cid, catalog, targets)
    V = pd.DataFrame(cols, index=foods.index)
    V.index = foods["fdc_id"].values
    return V, methods
