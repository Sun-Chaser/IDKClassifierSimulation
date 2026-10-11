import contextlib
import csv
import io
from pathlib import Path
import tempfile
import unittest

from Experiment.run_experiments import run
from RandomClassifierSetGenerator import RandomSetGenerator


class ExperimentTests(unittest.TestCase):
    def test_generator_modes(self):
        default = RandomSetGenerator(5, 10, seed=42).generate_sets()
        explicit = RandomSetGenerator(5, 10, seed=42, equal_row_length="random").generate_sets()
        self.assertEqual(default, explicit)
        generator = RandomSetGenerator(5, 10, seed=42, equal_row_length="equal")
        p, c = generator.generate_sets()
        self.assertTrue(all(len(row) == 11 for row in p[1:] + c[1:]))
        self.assertEqual((p, c), RandomSetGenerator(5, 10, seed=42, equal_row_length="equal").generate_sets())
        self.assertEqual(len(generator.generate_set()[0]), 11)
        with self.assertRaises(ValueError):
            RandomSetGenerator(2, 3, equal_row_length=True)

    def test_csv_results_and_limits(self):
        config = dict(m=[2], n=[3], k=[1, "all"], seeds=[42, 43],
                      row_sizes="equal", timeout_seconds=10, max_states=100)
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            for name, changes in [("ok", {}), ("skip", {"max_states": 1}),
                                  ("timeout", {"timeout_seconds": 0.00001})]:
                settings = config | changes
                output = Path(directory) / name
                run(settings, output)
                self.assertEqual(sorted(p.name for p in output.glob('*.json')),
                                 ["config.json", "environment.json"])
                for k in settings["k"]:
                    path = output / f"m2_n3_k{k}_ms{settings['max_states']}_equal_2.csv"
                    with path.open() as stream:
                        rows = list(csv.DictReader(stream))
                    self.assertEqual([r['seed'] for r in rows], ['42', '43'])
                    if name == "ok":
                        self.assertTrue(all(int(r['number_of_states']) == 16 for r in rows))
                        self.assertTrue(all(float(r['compute_time_seconds']) > 0 for r in rows))
                        self.assertTrue(all(int(r['path_length']) > 0 for r in rows))
                    else:
                        self.assertTrue(all(r['expected_cost'] == '' for r in rows))
                        self.assertTrue((output / 'failures.log').exists())


if __name__ == '__main__':
    unittest.main()
