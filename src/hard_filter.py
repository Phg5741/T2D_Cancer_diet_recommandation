"""Hard filter: remove foods that break a safety condition. Runs BEFORE scoring."""


def apply_hard_filters(foods, conditions, catalog):
    """
    input : foods DataFrame, active conditions (generate_conditions()['active']),
            condition catalog (rules/conditions.csv)
    output: (kept_foods, removed_foods) - removed_foods has a 'removed_by' column
    """
    hard = [cid for cid, c in conditions.items() if c["action"] == "hard_filter"]
    removed_by = foods["fdc_id"].map(lambda _: [])
    for cid in hard:
        info = catalog.loc[cid]
        if info.kind != "binary" or info.direction != "avoid":
            raise ValueError(f"hard filter only supports binary 'avoid' conditions: {cid}")
        hit = foods[info.feature] == 1
        removed_by = removed_by.where(~hit, removed_by.map(lambda lst, c=cid: lst + [c]))
    mask = removed_by.map(len) > 0
    removed = foods[mask].copy()
    removed["removed_by"] = removed_by[mask].map(", ".join)
    return foods[~mask].copy(), removed
