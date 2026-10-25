"""Checks cohort_counts() on a tiny hand-made table (real XPT files are not in this folder)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd
from scripts.cohort_audit_xpt import cohort_counts


class TestCohortCounts(unittest.TestCase):
    def test_counts(self):
        demo = pd.DataFrame({"SEQN": [1, 2, 3, 4]})
        diq = pd.DataFrame({"SEQN": [1, 2, 3, 4], "DIQ010": [1, 1, 2, 1]})
        mcq = pd.DataFrame({"SEQN": [1, 2, 3, 4], "MCQ220": [1, 1, 1, 2],
                            "MCQ230A": [16, 30, 14, np.nan], "MCQ230B": [35, np.nan, np.nan, np.nan],
                            "MCQ230C": [np.nan] * 4, "MCQ230D": [np.nan] * 4})
        ghb = pd.DataFrame({"SEQN": [1, 2], "LBXGH": [7.6, np.nan]})
        bmx = pd.DataFrame({"SEQN": [1, 2], "BMXBMI": [41.4, 30.0]})
        c = cohort_counts(demo, diq, mcq, ghb, bmx)
        self.assertEqual(c["diabetes + cancer"], 2)
        self.assertEqual(c["+ HbA1c and BMI available"], 1)
        self.assertEqual(c["diabetes + cancer with >=2 cancer types in A/B/C"], 1)


if __name__ == "__main__":
    unittest.main()
