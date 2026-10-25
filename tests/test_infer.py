"""infer.py: input dict -> PatientState -> results file."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from infer import build_state
from src.rules_loader import load_rules

RULES = load_rules()


class TestInfer(unittest.TestCase):
    def test_cancer_names_and_codes(self):
        st = build_state({"cancers": ["colon", 35], "diabetes_dx": True}, RULES)
        self.assertEqual(st.cancers, [16, 35])
        self.assertEqual(st.sources["cancers"], "user_input")

    def test_unknown_cancer_name_rejected(self):
        with self.assertRaises(ValueError):
            build_state({"cancers": ["colonn"]}, RULES)

    def test_null_stays_unknown(self):
        st = build_state({"hba1c": None, "dysphagia": None}, RULES)
        self.assertIsNone(st.hba1c)
        self.assertEqual(st.describe_sources()["dysphagia"], "unavailable")

    def test_base_seqn_fills_observed_values(self):
        st = build_state({"base_seqn": 134825, "nausea": True}, RULES)
        self.assertEqual(st.hba1c, 7.6)
        self.assertEqual(st.sources["hba1c"], "nhanes_observed")
        self.assertEqual(st.sources["nausea"], "user_input")


if __name__ == "__main__":
    unittest.main()
