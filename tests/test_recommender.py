"""
Unit tests (standard library unittest, no extra install):

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from src.patient_state import PatientState
from src.food_loader import load_foods
from src.rules_loader import load_rules
from src.condition_generator import generate_conditions
from src.hard_filter import apply_hard_filters
from src.recommender import recommend, select_pool
from evaluation import metrics

RULES = load_rules()
FOODS = load_foods()
CONGEE, CHICKEN, ALMONDS, BEER = 2708981, 2705956, 2707489, 2710616


def patient(**kw):
    base = dict(patient_id="T", age=65, sex="female", bmi=27.0, hba1c=7.6, diabetes_dx=True,
                cancers=[16], poor_appetite=False, dysphagia=False, mouth_sore=False, nausea=False,
                vomiting=False, malabsorption=False, digestion_problem=False, weight_loss_pct=0.0)
    base.update(kw)
    return PatientState(**base)


def ranks(state):
    r = recommend(state, FOODS, RULES)["ranking"]
    return dict(zip(r.fdc_id, r["rank"]))


class TestHardFilter(unittest.TestCase):
    def test_1_alcohol_removed_for_liver_cancer(self):
        # use_pool=False: test on every annotated food, including drinks
        res = recommend(patient(cancers=[22]), FOODS, RULES, use_pool=False)
        self.assertIn("no_alcohol", res["conditions"]["active"])
        alcohol_ids = set(FOODS[FOODS.alcohol_flag == 1].fdc_id)
        self.assertTrue(alcohol_ids)                       # beer, wine, whiskey, nonalcoholic beer (0.3 g)
        self.assertFalse(alcohol_ids & set(res["ranking"].fdc_id))
        self.assertTrue(alcohol_ids <= set(res["removed"].fdc_id))

    def test_alcohol_removed_for_any_cancer_history(self):
        res = recommend(patient(cancers=[16]), FOODS, RULES)      # colon only (GEN-01)
        self.assertIn("GEN-01", res["conditions"]["active"]["no_alcohol"]["rule_ids"])
        self.assertIn(BEER, set(res["removed"].fdc_id))

    def test_alcohol_kept_without_cancer_history(self):
        res = recommend(patient(cancers=[], cancer_history=False), FOODS, RULES)
        self.assertIn(BEER, set(res["ranking"].fdc_id))

    def test_default_pool_has_no_plain_drinks(self):
        pool = select_pool(FOODS, RULES)
        self.assertFalse(set(pool.food_role) & {"beverage", "condiment"})

    def test_protein_preferred_for_cancer_history(self):
        active = generate_conditions(patient(), RULES)["active"]
        self.assertIn("GEN-02", active["prefer_protein"]["rule_ids"])


class TestTexture(unittest.TestCase):
    def test_2_dysphagia_penalises_hard_food(self):
        before = recommend(patient(), FOODS, RULES)["ranking"].set_index("fdc_id")
        after = recommend(patient(dysphagia=True), FOODS, RULES)["ranking"].set_index("fdc_id")
        self.assertLess(after.at[ALMONDS, "final_score"], before.at[ALMONDS, "final_score"])
        self.assertGreater(after.at[ALMONDS, "rank"], before.at[ALMONDS, "rank"])

    def test_3_soft_food_moves_up_when_only_dysphagia_changes(self):
        r0, r1 = ranks(patient(dysphagia=False)), ranks(patient(dysphagia=True))
        self.assertLess(r1[CONGEE], r0[CONGEE])           # smaller rank number = higher
        self.assertGreater(r1[ALMONDS], r0[ALMONDS])


class TestPoorAppetite(unittest.TestCase):
    def test_poor_appetite_reduces_portion_not_ranking(self):
        a = recommend(patient(poor_appetite=False), FOODS, RULES)["ranking"]
        b = recommend(patient(poor_appetite=True), FOODS, RULES)["ranking"]
        self.assertEqual(a.fdc_id.tolist(), b.fdc_id.tolist())           # same order
        factor = RULES["targets"]["poor_appetite_portion_factor"]
        self.assertTrue(((b.recommended_portion_g - a.portion_g * factor).abs() < 1e-9).all())
        self.assertTrue((a.recommended_portion_g == a.portion_g).all())


class TestMultiCancer(unittest.TestCase):
    def test_4_both_cancer_rules_applied(self):
        st = patient(cancers=[22, 26], mouth_sore=True)
        active = generate_conditions(st, RULES, scope="cancer_only")["active"]
        rule_ids = {r for c in active.values() for r in c["rule_ids"]}
        self.assertIn("CA-22-1", rule_ids)                 # liver -> alcohol
        self.assertIn("CA-26-1", rule_ids)                 # mouth + mouth sore -> acidic
        self.assertEqual(active["no_alcohol"]["action"], "hard_filter")
        self.assertIn("avoid_acidic", active)

    def test_symptom_gated_cancer_rule_needs_symptom(self):
        active = generate_conditions(patient(cancers=[17]), RULES, scope="cancer_only")["active"]
        self.assertNotIn("prefer_soft", active)            # esophagus alone does not force soft diet


class TestMissing(unittest.TestCase):
    def test_5_missing_hba1c(self):
        st = patient(hba1c=None)
        out = generate_conditions(st, RULES)
        self.assertIn("limit_carbohydrate", out["active"])   # from diabetes diagnosis
        self.assertNotIn("limit_total_sugar", out["active"]) # needs HbA1c -> skipped
        self.assertIn("DM-02", out["inactive_unknown"])
        self.assertGreater(len(recommend(st, FOODS, RULES)["ranking"]), 0)

    def test_unknown_symptom_does_not_activate(self):
        out = generate_conditions(patient(dysphagia=None), RULES)
        self.assertNotIn("prefer_soft", out["active"])
        self.assertIn("SY-02", out["inactive_unknown"])


class TestMetrics(unittest.TestCase):
    def test_ndcg_perfect_and_reversed(self):
        exp = {"a": 1, "b": 2, "c": 3}
        self.assertAlmostEqual(metrics.ndcg_at_k(["a", "b", "c"], exp, 3), 1.0)
        self.assertLess(metrics.ndcg_at_k(["c", "b", "a"], exp, 3), 1.0)

    def test_dynamic_accuracy(self):
        self.assertEqual(metrics.dynamic_reranking_accuracy({"x": 5}, {"x": 2}, [("x", "up")]), 1.0)

    def test_unsafe_rate(self):
        self.assertEqual(metrics.unsafe_recommendation_rate([1, 2, 3, 4], {4}), 0.25)


if __name__ == "__main__":
    unittest.main()
