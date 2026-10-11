"""Generate random classifier sets with increasing probabilities and costs."""
import random


class RandomSetGenerator:
    """Generate M classifier sets, each containing between 1 and N classifiers.

    equal_row_length="random" (default) varies row lengths; "equal" gives
    every set exactly N classifiers, including calls to generate_set().

    Probabilities and costs are returned separately. For multiple sets,
    each matrix has a dummy [0.0] row at index 0 and classes 1 through M; corresponding rows have matching
    lengths, but different sets may have different lengths. At least one
    set in each generated batch has exactly N classifiers. Index 0 holds a
    dummy zero in both matrices, so row lengths range from 2 to N+1. Each row is
    sorted in nondecreasing order. Intermediate probabilities and normalized
    costs are sampled uniformly from [0, 1). Each class's final probability
    is 1, ensuring sum(prior[i] * P[i][-1]) == 1 for normalized priors,
    including the DP's default uniform prior 1/M.
    Supply seed for reproducible sequences
    of sets; each instance uses its own random state. Repeated calls advance
    that state. Omitting seed uses system-provided randomness.
    """

    def __init__(self, M: int, N: int, seed=None, equal_row_length="random"):
        for name, value in (("M", M), ("N", N)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if value < 1:
                raise ValueError(f"{name} must be positive")
        if equal_row_length not in ("random", "equal"):
            raise ValueError('equal_row_length must be "random" or "equal"')
        self.equal_row_length = equal_row_length
        self.M = M
        self.N = N
        self._rng = random.Random(seed)

    def generate_set(self) -> tuple[list[float], list[float]]:
        """Return separate probability and cost arrays for one set."""
        size = self.N if self.equal_row_length == "equal" else self._rng.randint(1, self.N)
        return self._generate_set_of_size(size)

    def _generate_set_of_size(self, size: int) -> tuple[list[float], list[float]]:
        probabilities = [0.0] + sorted(self._rng.random() for _ in range(size - 1)) + [1.0]
        costs = [0.0] + sorted(self._rng.random() for _ in range(size))
        return probabilities, costs

    def generate_sets(self) -> tuple[list[list[float]], list[list[float]]]:
        """Return two (M+1)-row matrices, including dummy row 0."""
        probability_matrix = [[0.0]]
        cost_matrix = [[0.0]]
        full_size_index = self._rng.randrange(self.M) if self.equal_row_length == "random" else None
        for i in range(self.M):
            if i == full_size_index:
                probabilities, costs = self._generate_set_of_size(self.N)
            else:
                probabilities, costs = self.generate_set()
            probability_matrix.append(probabilities)
            cost_matrix.append(costs)
        return probability_matrix, cost_matrix
