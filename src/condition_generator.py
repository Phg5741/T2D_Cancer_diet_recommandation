"""
Patient state -> list of active conditions.

Two rule tables are kept apart on purpose:
    rules/cancer_restriction.csv   cancer type (+ optional symptom requirement)
    rules/symptom_restriction.csv  symptom / diabetes / nutrition state (any cancer)

Missing values: a trigger that is unknown (None) does NOT activate its rule.
It is reported in `inactive_unknown` so the user can see what was skipped.
"""

ACTION_STRENGTH = {"hard_filter": 2, "soft": 1}


def derive_triggers(state, targets):
    """
    input : PatientState, thresholds from nutrition_targets.csv
    output: {trigger_name: True / False / None(unknown)}
    """
    def at_least(value, param):
        cut = targets.get(param)
        if value is None or cut is None:
            return None
        return value >= cut

    t = {
        "always": True,
        # MCQ220=1, or at least one cancer code; None = unknown
        "has_cancer_history": True if (state.cancer_history or state.cancers) else state.cancer_history,
        "has_diabetes_dx": state.diabetes_dx,
        "hba1c_above_target": at_least(state.hba1c, "hba1c_target_pct"),
        "bmi_obese": at_least(state.bmi, "bmi_obesity_kg_m2"),
        "weight_loss_significant": at_least(state.weight_loss_pct, "weight_loss_significant_pct"),
    }
    for s in ["poor_appetite", "dysphagia", "mouth_sore", "nausea", "vomiting",
              "malabsorption", "digestion_problem"]:
        t[s] = getattr(state, s)
    return t


def _check(expr, triggers):
    """'mouth_sore|dysphagia' -> True if any is True; None if none True and some unknown."""
    values = [triggers.get(part.strip()) for part in str(expr).split("|")]
    if any(v is True for v in values):
        return True
    if any(v is None for v in values):
        return None
    return False


def _add(active, condition_id, action, rule_id, reason):
    """Merge one rule hit into `active`; the stricter action wins for the same condition."""
    if condition_id == "none":
        return
    c = active.setdefault(condition_id, {"condition_id": condition_id, "action": action,
                                         "rule_ids": [], "reasons": []})
    if ACTION_STRENGTH[action] > ACTION_STRENGTH[c["action"]]:
        c["action"] = action
    c["rule_ids"].append(rule_id)
    c["reasons"].append(reason)


def resolve_conflicts(active, conflicts):
    """Drop the losing condition when two opposite conditions are both active."""
    dropped = []
    for r in conflicts.itertuples():
        if r.condition_a in active and r.condition_b in active:
            loser = r.condition_b if r.keep == r.condition_a else r.condition_a
            dropped.append({"dropped": loser, "kept": r.keep, "status": r.status})
            del active[loser]
    return dropped


def generate_conditions(state, rules, scope="full"):
    """
    input : PatientState, rules from rules_loader.load_rules(),
            scope = 'full' | 'diabetes_only' | 'cancer_only' | 'static'
    output: dict with
            active           {condition_id: {action, rule_ids, reasons}}
            inactive_unknown [rule ids skipped because a trigger was unknown]
            conflicts        [conditions removed by conflict_resolution.csv]
    """
    active, unknown = {}, []
    if scope == "static":
        for cid in rules["static"].condition_id:
            _add(active, cid, "soft", "STATIC", "static baseline (no patient input)")
        return {"active": active, "inactive_unknown": [], "conflicts": []}

    triggers = derive_triggers(state, rules["targets"])
    labels = rules["cancer_codes"]

    if scope in ("full", "cancer_only"):
        cr = rules["cancer_rules"]
        for r in cr[cr.enabled == 1].itertuples():
            if int(r.cancer_code) not in state.cancers:
                continue
            ok = _check(r.requires_state, triggers)
            if ok is None:
                unknown.append(r.rule_id)
            elif ok:
                cond = "" if r.requires_state == "always" else f" + {r.requires_state}"
                _add(active, r.condition_id, r.action, r.rule_id,
                     f"cancer history {labels.get(int(r.cancer_code))}{cond}")

    if scope in ("full", "diabetes_only", "cancer_only"):
        sr = rules["state_rules"]
        allowed = {"full": {"diabetes", "symptom", "nutrition_state", "general_cancer"},
                   "diabetes_only": {"diabetes"},
                   "cancer_only": {"general_cancer"}}[scope]
        for r in sr[(sr.enabled == 1) & sr.scope.isin(allowed)].itertuples():
            ok = _check(r.trigger, triggers)
            if ok is None:
                unknown.append(r.rule_id)
            elif ok:
                _add(active, r.condition_id, r.action, r.rule_id, r.trigger)

    dropped = resolve_conflicts(active, rules["conflicts"])
    return {"active": active, "inactive_unknown": unknown, "conflicts": dropped}
