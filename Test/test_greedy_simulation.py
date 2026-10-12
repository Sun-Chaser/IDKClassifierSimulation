# Allow direct execution as well as unittest discovery from the project root.
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import unittest

from Simulator.DPSimulation import DPSimulation
from Simulator.GreedySimulation import GreedySimulation
from Simulator.RandomClassifierSetGenerator import RandomSetGenerator


class GreedySimulationTests(unittest.TestCase):
    def test_jump_limit_and_expected_cost(self):
        sim = GreedySimulation([[0], [0, 0.5, 0.9]], [[0], [0, 1, 1.2]])
        self.assertAlmostEqual(sim.run(k=1), 1.6)
        self.assertEqual(sim.choice[(0,)], (1, 1))
        self.assertAlmostEqual(sim.run('k', K=2), 1.2)
        self.assertEqual(sim.choice[(0,)], (1, 2))
        self.assertNotIn((1,), sim.choice)  # Reset on rerun.
        self.assertAlmostEqual(sim.run(), 1.2)

    def test_conditional_probability_uses_increment_and_prior(self):
        sim = GreedySimulation(
            [[0], [0, 0.8, 0.9], [0, 0.4]],
            [[0], [0, 1, 1], [0, 1]], priors=[0, 3, 1])
        # At (1,0), weights are .15 and .25; success probabilities .1875 and .25.
        self.assertAlmostEqual(sim.run(k=1, state=(1, 0)), 1.75)
        self.assertEqual(sim.choice[(1, 0)], (2, 1))

    def test_zero_cost_ties_and_leaves(self):
        sim = GreedySimulation([[0], [0, 0, 0.5, 1]], [[0], [0, 0, 0, 0]])
        self.assertEqual(sim.run(), 0)
        self.assertEqual(sim.choice[(0,)], (1, 2))
        self.assertIsNone(sim.choice[(3,)])
        self.assertEqual(sim.run(state=(3,)), 0)
        plateau = GreedySimulation([[0], [0, 0, 0]], [[0], [0, 0, 0]])
        self.assertEqual(plateau.run(), 0)
        self.assertEqual(plateau.choice[(0,)], (1, 1))

    def test_generated_path_cost_and_optimal_bound(self):
        for seed in range(5):
            p, c = RandomSetGenerator(3, 4, seed=seed).generate_sets()
            for k in (1, 2, 4):
                sim = GreedySimulation(p, c)
                value = sim.run(k=k)
                state, expected = (0, 0, 0), 0.0
                while sim.choice[state] is not None:
                    i, j = sim.choice[state]
                    self.assertTrue(1 <= j - state[i - 1] <= k)
                    reach = sum((1 - p[t][state[t - 1]]) / 3 for t in range(1, 4))
                    expected += reach * c[i][j]
                    state = state[:i - 1] + (j,) + state[i:]
                self.assertAlmostEqual(value, expected)
                self.assertLessEqual(DPSimulation(p, c).run('k', K=k), value + 1e-12)

    def test_long_path_and_validation(self):
        n = 1500
        sim = GreedySimulation([[0], [0] + [j / n for j in range(1, n + 1)]],
                               [[0], [0] + [1] * n])
        self.assertAlmostEqual(sim.run(k=1), (n + 1) / 2)
        self.assertEqual(len(sim.V), n + 1)
        for k in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                sim.run(k=k)
        for kwargs in ({'mode': 'bad'}, {'mode': 'k'}, {'K': 1},
                       {'k': 1, 'K': 2}, {'state': (-1,)}):
            with self.assertRaises(ValueError):
                sim.run(**kwargs)


if __name__ == '__main__':
    unittest.main()
