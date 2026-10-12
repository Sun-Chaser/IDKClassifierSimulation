"""Memoized expected-cost DP for move-by-K and search-for-all policies."""

from math import fsum, isfinite


class DPSimulation:
    """Optimize a policy for separate, possibly ragged P and C matrices.

    State entries are one-based indices of the last attempted classifier;
    0 means no classifier has run in that set. Both input matrices must
    include a dummy zero at index 0 in every row. The initial state is
    (0, ..., 0), with M entries in class order (class i uses state[i-1]).
    Matrices have a dummy [0] row at index 0; classes use rows 1 through M.
    Priors and returned posteriors also include a dummy zero at index 0. A state
    represents failure of all attempts so far. Priors describe mutually
    exclusive classes/sets and default to uniform.

    Every attempt pays the full destination cost C[i][j], not a difference
    in costs. Exhausting all classifiers has zero remaining cost, even if
    some probability of failure remains, as in the supplied recurrence.
    """

    def __init__(self, probabilities, costs, priors=None):
        self.P = tuple(tuple(row) for row in probabilities)
        self.C = tuple(tuple(row) for row in costs)
        if len(self.P) < 2 or len(self.P) != len(self.C):
            raise ValueError("Probability and cost matrices must have matching, nonzero row counts")
        if self.P[0] != (0,) or self.C[0] != (0,):
            raise ValueError("Both matrices must have a dummy [0] row at index 0")
        for p, c in zip(self.P[1:], self.C[1:]):
            if len(p) < 2 or len(p) != len(c):
                raise ValueError("Each set must have matching rows with a dummy and at least one classifier")
            if p[0] != 0 or c[0] != 0:
                raise ValueError("Each probability and cost row must begin with a dummy zero")
            if any(not isfinite(x) or not 0 <= x <= 1 for x in p):
                raise ValueError("Probabilities must be finite and between 0 and 1")
            if any(not isfinite(x) or x < 0 for x in c):
                raise ValueError("Costs must be finite and nonnegative")
            if any(a > b for a, b in zip(p, p[1:])):
                raise ValueError("Probability rows must be nondecreasing")
            if any(a > b for a, b in zip(c, c[1:])):
                raise ValueError("Cost rows must be nondecreasing")
        self.M = len(self.P) - 1
        self.priors = tuple(priors) if priors is not None else (0.0,) + (1 / self.M,) * self.M
        if len(self.priors) != self.M + 1 or self.priors[0] != 0 or any(
            not isfinite(x) or x < 0 for x in self.priors
        ):
            raise ValueError("Priors must start with dummy zero, followed by M finite, nonnegative weights")
        total = fsum(self.priors)
        if not isfinite(total) or total <= 0:
            raise ValueError("Prior weights must have a finite, positive sum")
        self.priors = tuple(x / total for x in self.priors)
        self.V = {}
        self.choice = {}

    def _state(self, state):
        state = (0,) * self.M if state is None else tuple(state)
        if len(state) != self.M or any(
            isinstance(j, bool) or not isinstance(j, int) or not 0 <= j < len(row)
            for j, row in zip(state, self.P[1:])
        ):
            raise ValueError("State must contain one valid classifier index (or 0) per set")
        return state

    def _failure_weights(self, state):
        return tuple(
            prior * (1 - row[j])
            for prior, row, j in zip(self.priors[1:], self.P[1:], state)
        )

    def posterior_probability(self, state=None):
        """Return PP(state, P); reject conditioning on zero-probability failure."""
        weights = self._failure_weights(self._state(state))
        denominator = fsum(weights)
        if denominator == 0:
            raise ValueError("Posterior is undefined: failure has probability zero")
        return [0.0] + [weight / denominator for weight in weights]

    def run(self, mode="all", K=None, state=None):
        """Return the minimum expected remaining cost from state.

        mode='k' allows jumps of 1 through K; mode='all' allows every
        later classifier. V and choice are reset on every run. choice[s]
        is (set_index, destination_classifier_index), or None at a leaf.
        Both class and classifier indices start at 1. Equal-cost ties use the first action.

        This exact DP may visit the product of row lengths (including dummies) states;
        recursion depth can grow with the total number of classifiers.
        """
        if mode not in ("k", "all"):
            raise ValueError("mode must be 'k' or 'all'")
        if mode == "k" and (
            isinstance(K, bool) or not isinstance(K, int) or K < 1
        ):
            raise ValueError("K must be a positive integer for mode='k'")
        if mode == "all" and K is not None:
            raise ValueError("K is only used with mode='k'")
        start = self._state(state)
        self.V = {}
        self.choice = {}
        terminal = tuple(len(row) - 1 for row in self.P[1:])

        def dp(s):
            if s in self.V:
                return self.V[s]
            denominator = fsum(self._failure_weights(s))
            if s == terminal or denominator == 0:
                self.V[s] = 0.0
                self.choice[s] = None
                return 0.0
            best_cost = float("inf")
            best_choice = None
            for i in range(1, self.M + 1):
                row = self.P[i]
                last = s[i - 1]
                stop = len(row) if mode == "all" else min(len(row), last + K + 1)
                previous_p = row[last]
                for j in range(last + 1, stop):
                    # Algebraically PP[i] * delta_p / (1 - P[i][last]);
                    # cancelling the factors also avoids division by zero.
                    q_success = self.priors[i] * (row[j] - previous_p) / denominator
                    q_failure = max(0.0, min(1.0, 1.0 - q_success))
                    next_state = s[:i - 1] + (j,) + s[i:]
                    candidate = self.C[i][j] + q_failure * dp(next_state)
                    if best_choice is None or candidate < best_cost:
                        best_cost = candidate
                        best_choice = (i, j)
            self.V[s] = best_cost
            self.choice[s] = best_choice
            return best_cost

        return dp(start)
