"""Evaluation metrics. Each takes plain lists so it is easy to test by hand."""
import numpy as np


def ndcg_at_k(model_order, expected_rank, k):
    """
    model_order  : list of food ids in model order (restricted to the expected foods)
    expected_rank: {food_id: expected rank (1 = best)}
    Relevance of a food = n - expected_rank + 1 (best food gets the highest relevance).
    """
    n = len(expected_rank)
    rel = {f: n - r + 1 for f, r in expected_rank.items()}
    def dcg(order):
        return sum(rel.get(f, 0) / np.log2(i + 2) for i, f in enumerate(order[:k]))
    ideal = sorted(expected_rank, key=expected_rank.get)
    return dcg(model_order) / dcg(ideal) if dcg(ideal) > 0 else 0.0


def top_k_agreement(model_order, expected_order, k):
    """Share of the expected top-K that also appears in the model top-K."""
    return len(set(model_order[:k]) & set(expected_order[:k])) / k


def unsafe_recommendation_rate(top_k_ids, forbidden_ids):
    """Share of recommended foods that a hard rule forbids (should be 0)."""
    if not top_k_ids:
        return 0.0
    return sum(f in forbidden_ids for f in top_k_ids) / len(top_k_ids)


def dynamic_reranking_accuracy(rank_before, rank_after, expectations):
    """
    expectations: list of (food_id, 'up' | 'down')
    'up' means the rank number gets smaller (moves toward #1).
    """
    if not expectations:
        return float("nan")
    hits = 0
    for food, direction in expectations:
        change = rank_before[food] - rank_after[food]   # positive = moved up
        hits += (change > 0) if direction == "up" else (change < 0)
    return hits / len(expectations)


def nutrition_target_violation(V, top_k_ids, numeric_conditions):
    """Mean numeric-condition violation over the recommended foods (0 = fully meets)."""
    cols = [c for c in numeric_conditions if c in V.columns]
    if not cols or not top_k_ids:
        return float("nan")
    return float(V.loc[top_k_ids, cols].to_numpy().mean())
