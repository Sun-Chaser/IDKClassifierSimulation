# IDKClassifierSimulation

## Greedy simulation

```python
from Simulator.RandomClassifierSetGenerator import RandomSetGenerator
from Simulator.GreedySimulation import GreedySimulation

p, c = RandomSetGenerator(5, 10, seed=42, equal_row_length="equal").generate_sets()
sim = GreedySimulation(p, c)
expected_cost = sim.run(k=3)
print(expected_cost)
state = (0,) * sim.M
while sim.choice[state] is not None:
    i, j = sim.choice[state]
    print(i, j)
    state = state[:i - 1] + (j,) + state[i:]
```

The greedy score is conditional success probability divided by the full
classifier cost. At state s, success probability for (i,j) is
`prior[i] * (P[i][j] - P[i][s[i-1]]) / sum(prior[t] * (1-P[t][s[t-1]]))`.
Thus already-attempted probability is excluded and class priors are respected.
`k` limits candidate destinations to the next k classifiers in each set;
it does not evaluate multi-action sequences. `run()` considers all later
classifiers; `run(mode="k", K=3)` also matches the DP API.

The return value is expected cost of the greedy policy. `choice` and `V`
store only the selected failure path and its expected remaining costs.
Ties choose the first candidate in set/classifier order. Positive success
probability at zero cost scores infinity; zero probability and zero cost
scores zero. Traversal is iterative and ends at exhaustion or zero remaining
failure probability. Greedy decisions need not minimize total expected cost.

## Project structure and tests

Models live in `Simulator/`, experiment tools in `Experiment/`, and tests in
`Test/`. Run from the project root (Python 3.9 or newer; standard library only):

```sh
python -m unittest discover -v
python -m Test.test_dp_simulation
python Experiment/generate_config.py --help
python Experiment/run_experiments.py --help
```

Direct test execution, such as `python Test/test_dp_simulation.py`, is also supported.
