"""Greedy conditional-success-per-cost policy using the DP's input conventions."""
from math import fsum

from Simulator.DPSimulation import DPSimulation


class GreedySimulation(DPSimulation):
    """Reuse DP validation and posterior calculations, but follow one greedy path.

    At state s, candidate (i, j) has conditional success probability
        q = prior[i] * (P[i][j] - P[i][s[i-1]])
            / sum(prior[t] * (1 - P[t][s[t-1]]), t=1..M).
    Choose the largest q / C[i][j], paying the full destination cost.
    A positive probability at zero cost has infinite score; 0/0 scores zero.
    Ties use the first action in ascending set and destination order.

    V and choice contain only states along the selected failure path, including
    its leaf. V stores expected remaining cost under this greedy policy, not
    the globally optimal cost. The traversal is iterative, avoiding recursion.
    """

    def run(self, mode="all", K=None, state=None, *, k=None):
        """Return greedy expected cost from state (default: all-zero state).

        Use run(k=3), or the DP-compatible run(mode="k", K=3), to consider
        destinations s[i]+1 through s[i]+3 in each set, clipped to its length.
        This bounds available jumps, not a multi-step policy lookahead.
        run() / run(mode="all") considers every later classifier.
        """
        if k is not None:
            if K is not None:
                raise ValueError("Specify only one of k and K")
            if mode not in ("all", "k"):
                raise ValueError("mode must be 'k' or 'all'")
            mode, K = "k", k
        if mode not in ("k", "all"):
            raise ValueError("mode must be 'k' or 'all'")
        if mode == "k" and (isinstance(K, bool) or not isinstance(K, int) or K < 1):
            raise ValueError("K must be a positive integer for mode='k'")
        if mode == "all" and K is not None:
            raise ValueError("K is only used with mode='k'")
        start = self._state(state)
        self.V = {}
        self.choice = {}
        terminal = tuple(len(row) - 1 for row in self.P[1:])
        s = start
        steps = []
        while True:
            denominator = fsum(self._failure_weights(s))
            if s == terminal or denominator == 0:
                self.choice[s] = None
                self.V[s] = 0.0
                break
            best_score = -1.0
            best_action = None
            best_failure = None
            for i in range(1, self.M + 1):
                last = s[i - 1]
                row = self.P[i]
                stop = len(row) if mode == "all" else min(len(row), last + K + 1)
                for j in range(last + 1, stop):
                    q = self.priors[i] * (row[j] - row[last]) / denominator
                    cost = self.C[i][j]
                    score = (float("inf") if q > 0 else 0.0) if cost == 0 else q / cost
                    if best_action is None or score > best_score:
                        best_score = score
                        best_action = (i, j)
                        best_failure = max(0.0, min(1.0, 1.0 - q))
            i, j = best_action
            self.choice[s] = best_action
            steps.append((s, self.C[i][j], best_failure))
            s = s[:i - 1] + (j,) + s[i:]

        remaining = 0.0
        for s, cost, failure in reversed(steps):
            remaining = cost + failure * remaining
            self.V[s] = remaining
        return self.V[start]
