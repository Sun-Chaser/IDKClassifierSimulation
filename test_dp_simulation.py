import unittest

from DPSimulation import DPSimulation
from RandomClassifierSetGenerator import RandomSetGenerator


class DPSimulationTests(unittest.TestCase):
    def test_generated_matrices_use_dummy_zero(self):
        for m, n in ((1, 1), (1, 5), (3, 1), (3, 5)):
            p, c = RandomSetGenerator(m, n).generate_sets()
            self.assertEqual(len(p), m + 1)
            self.assertEqual(len(c), m + 1)
            self.assertEqual(max(map(len, p)), n + 1)
            for probabilities, costs in zip(p[1:], c[1:]):
                self.assertEqual(probabilities[0], 0)
                self.assertEqual(probabilities[-1], 1)
                self.assertEqual(costs[0], 0)
                self.assertEqual(len(probabilities), len(costs))
                self.assertTrue(2 <= len(probabilities) <= n + 1)
            simulation = DPSimulation(p, c)
            self.assertAlmostEqual(
                sum(simulation.priors[i] * p[i][-1] for i in range(1, m + 1)), 1
            )
            constrained = simulation.run("k", K=1)
            unrestricted = simulation.run("all")
            self.assertLessEqual(unrestricted, constrained + 1e-12)
            self.assertIn((0,) * m, simulation.V)
            for action in simulation.choice.values():
                if action is not None:
                    i, j = action
                    self.assertTrue(1 <= j < len(p[i]))

    def test_generator_endpoints_with_custom_priors_and_seed(self):
        generator = RandomSetGenerator(3, 5, seed=42)
        p, c = generator.generate_sets()
        self.assertEqual((p, c), RandomSetGenerator(3, 5, seed=42).generate_sets())
        simulation = DPSimulation(p, c, priors=[0, 2, 3, 5])
        self.assertAlmostEqual(
            sum(simulation.priors[i] * p[i][-1] for i in range(1, 4)), 1
        )
        probabilities, costs = generator.generate_set()
        self.assertEqual(probabilities[-1], 1)
        self.assertEqual(len(probabilities), len(costs))

    def test_single_set_hand_calculation(self):
        simulation = DPSimulation([[0], [0, 0.5, 0.9]], [[0], [0, 1, 1.2]])
        self.assertAlmostEqual(simulation.run("k", K=1), 1 + 0.5 * 1.2)
        self.assertAlmostEqual(simulation.run("all"), 1.2)
        self.assertEqual(simulation.choice[(0,)], (1, 2))

    def test_posterior_and_certain_success(self):
        simulation = DPSimulation([[0], [0, 0.5, 1], [0, 1]], [[0], [0, 0, 2], [0, 3]], [0, 3, 1])
        self.assertEqual(simulation.posterior_probability(), [0, 0.75, 0.25])
        self.assertEqual(simulation.posterior_probability((1, 0)), [0, 0.6, 0.4])
        self.assertAlmostEqual(simulation.run(state=(2, 0)), 3)
        self.assertEqual(simulation.run(state=(2, 1)), 0)
        with self.assertRaises(ValueError):
            simulation.posterior_probability((2, 1))

    def test_modes_against_exhaustive_paths(self):
        # Enumerate full failure paths, weighting each paid cost by the
        # unconditional probability of reaching that step (no DP/posterior).
        p = [[0, 0.2, 0.8], [0, 0.3, 0.6, 0.95]]
        c = [[0, 0.1, 0.7], [0, 0.2, 0.4, 0.9]]
        prior = [0.4, 0.6]
        terminal = (2, 3)

        def path_costs(state, accumulated, limit):
            if state == terminal:
                yield accumulated
                return
            reach = sum(prior[i] * (1 - p[i][j])
                        for i, j in enumerate(state))
            for i, last in enumerate(state):
                for j in range(last + 1, min(len(p[i]), last + limit + 1)):
                    following = state[:i] + (j,) + state[i + 1:]
                    yield from path_costs(following, accumulated + reach * c[i][j], limit)

        simulation = DPSimulation([[0]] + p, [[0]] + c, [0] + prior)
        values = []
        for k in (1, 2, 3):
            value = simulation.run("k", K=k)
            self.assertAlmostEqual(value, min(path_costs((0, 0), 0, k)))
            values.append(value)
        self.assertGreaterEqual(values[0], values[1])
        self.assertGreaterEqual(values[1], values[2])
        self.assertAlmostEqual(simulation.run("all"), values[2])

    def test_zero_cost_and_validation(self):
        simulation = DPSimulation([[0], [0, 0, 0.5]], [[0], [0, 0, 0]])
        self.assertEqual(simulation.run("k", K=1), 0)
        self.assertEqual(simulation.choice[(0,)], (1, 1))
        for k in (0, -1, True, 1.5, None):
            with self.assertRaises(ValueError):
                simulation.run("k", K=k)
        with self.assertRaises(ValueError):
            simulation.run(state=(3,))
        with self.assertRaises(ValueError):
            simulation.run(state=(-1,))
        with self.assertRaises(ValueError):
            DPSimulation([[0], [0, 0.8, 0.2]], [[0], [0, 1, 2]])
        with self.assertRaises(ValueError):
            DPSimulation([[0], [0.2, 0.8]], [[0], [0, 1]])
        with self.assertRaises(ValueError):
            DPSimulation([[0], [0, 0.8]], [[0], [1, 2]])
        with self.assertRaises(ValueError):
            DPSimulation([[0], [0.2]], [[0], [1, 2]])


if __name__ == "__main__":
    unittest.main()
