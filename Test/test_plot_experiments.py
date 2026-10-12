"""Check aggregation, missing trials, and separation of experimental conditions."""
import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("plot_experiments", Path(__file__).resolve().parents[1] / "Plot" / "plot_experiments.py")
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)


class SummaryTests(unittest.TestCase):
    def test_statistics_and_incomplete_trials(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for k, values in (("1", [(1, 2), (3, 6), (99, ""), ("nan", 3)]),
                              ("all", [(5, 8)]), ("2", [("", "")])):
                with (folder / f"m2_n5_k{k}_ms100_equal_4.csv").open("w", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(["compute_time_seconds", "expected_cost"])
                    writer.writerows(values)
            fixed, rows, omitted = plot.summarize(folder, "k", "runtime")
            indexed = {row["k"]: row for row in rows}
            self.assertEqual(omitted, 3)
            self.assertEqual(indexed["1"]["count"], 2)
            self.assertEqual(indexed["1"]["mean"], 2)
            self.assertAlmostEqual(indexed["1"]["std"], 2 ** 0.5)
            self.assertIsNone(indexed["all"]["std"])
            self.assertIsNone(indexed["2"]["mean"])
            _, costs, _ = plot.summarize(folder, "n", "expected_cost")
            self.assertEqual(len(costs), 3)
            self.assertEqual(next(r for r in costs if r["k"] == "1")["mean"], 4)

    def test_explicit_grouping_pools_trials(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for m in (2, 3):
                for n in (5, 10):
                    for k, values in ((1, [1, 3]), (2, [8])):
                        path = folder / f"m{m}_n{n}_k{k}_ms100_equal_2.csv"
                        with path.open("w", newline="") as stream:
                            writer = csv.writer(stream)
                            writer.writerow(["compute_time_seconds", "expected_cost"])
                            writer.writerows((value, value * 2) for value in values)
            fixed, rows, omitted = plot.summarize(folder, "m", "runtime", ["n"])
            self.assertEqual(fixed, ["n"])
            self.assertEqual(len(rows), 4)
            self.assertEqual(omitted, 0)
            for row in rows:
                self.assertEqual(row["count"], 3)
                self.assertEqual(row["mean"], 4)
                self.assertAlmostEqual(row["std"], 13 ** 0.5)
            fixed, rows, _ = plot.summarize(folder, "m", "expected_cost", ["n", "k"])
            self.assertEqual(fixed, ["n", "k"])
            self.assertEqual(len(rows), 8)
            for row in rows:
                self.assertEqual(row["mean"], 4 if row["k"] == "1" else 16)

    def test_invalid_grouping(self):
        for groupby in (["m"], ["n", "n"], ["unknown"], []):
            with self.subTest(groupby=groupby), self.assertRaises(ValueError):
                plot.summarize(Path("."), "m", "runtime", groupby)


if __name__ == "__main__":
    unittest.main()
