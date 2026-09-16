"""Boundary, reproducibility, and corrupted-certificate checks."""

from copy import deepcopy
from fractions import Fraction
import unittest

from generate import allocate_demand, build_instance, json_text
from validate import validate_solution, window_counts


class DatasetChecks(unittest.TestCase):
    def test_rounding_and_tie(self):
        self.assertEqual(allocate_demand(30, Fraction(1, 10), (3, 5, 2)),
                         {"D": 6, "E": 9, "N": 4})
        self.assertEqual(allocate_demand(40, Fraction(1, 10), (3, 5, 2)),
                         {"D": 8, "E": 12, "N": 5})

    def test_final_window_is_checked(self):
        self.assertEqual(list(window_counts("OOOOOODDDDDDD", ["D"], 7))[-1], (7, 7))
        self.assertEqual(list(window_counts("EDND", ["E", "N"], 2)),
                         [(1, 1), (2, 1), (3, 1)])
        self.assertEqual(list(window_counts("DEN", ["D"], 4)), [])

    def test_seed_and_nonmultiple_horizon(self):
        first = build_instance(30, 40, 20260916)
        second = build_instance(30, 40, 20260916)
        changed = build_instance(30, 40, 20260917)
        self.assertEqual(json_text(first[0]), json_text(second[0]))
        self.assertEqual(first[1], second[1])
        self.assertEqual(first[0]["demand"], changed[0]["demand"])
        self.assertNotEqual(first[0]["hard_day_off"], changed[0]["hard_day_off"])
        self.assertTrue(first[2]["valid"])
        self.assertEqual(first[2]["hard_off_residues_max"], 2)

    def test_residual_group_and_long_horizon(self):
        for nurses, days in [(40, 60), (50, 80), (80, 112), (120, 168)]:
            with self.subTest(nurses=nurses, days=days):
                instance, solution, report = build_instance(nurses, days, 20260916)
                self.assertTrue(report["valid"])
                self.assertTrue(validate_solution(instance, solution)["valid"])

    def test_validator_rejects_coverage_failure(self):
        instance, solution, _ = build_instance(30, 40, 20260916)
        corrupt = deepcopy(solution)
        corrupt["schedule"] = [solution["schedule"][0]] * 30
        report = validate_solution(instance, corrupt)
        self.assertFalse(report["valid"])
        # Check demand separately from off so accumulated off errors cannot hide it.
        clean_off = deepcopy(instance)
        clean_off["hard_day_off"] = [[] for _ in range(30)]
        clean_off["generation"]["hard_off_rate"] = "0"
        report = validate_solution(clean_off, corrupt)
        self.assertTrue(any("demand violated" in item for item in report["errors"]))

    def test_validator_rejects_hard_off_failure(self):
        instance, solution, _ = build_instance(30, 40, 20260916)
        corrupt = deepcopy(instance)
        working = next(i + 1 for i, s in enumerate(solution["schedule"][0]) if s != "O")
        corrupt["hard_day_off"][0] = sorted(corrupt["hard_day_off"][0] + [working])
        report = validate_solution(corrupt, solution)
        self.assertFalse(report["valid"])
        self.assertTrue(any("hard_day_off violated" in item for item in report["errors"]))

    def test_validator_rejects_truncated_schedule(self):
        instance, solution, _ = build_instance(30, 40, 20260916)
        solution["schedule"][0] = solution["schedule"][0][:-1]
        self.assertFalse(validate_solution(instance, solution)["valid"])


if __name__ == "__main__":
    unittest.main()
