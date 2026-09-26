"""
Standalone Genetic Algorithm for the Assignment Problem.
No UI dependencies — testable independently.
"""

from __future__ import annotations
import random
from typing import List, Optional, Tuple

from core.problem import AssignmentProblem, MISSING, Solution
from core.scoring import ScoringSystem


class GeneticAlgorithm:
    def __init__(
        self,
        problem: AssignmentProblem,
        population_size: int = 30,
        generations: int = 25,
        mutation_rate: float = 0.15,
        crossover_rate: float = 0.8,
        seed: Optional[int] = None,
    ):
        self.problem = problem
        self.pop_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.rng = random.Random(seed)
        self._population: List[List[int]] = []
        self._fitnesses: List[float] = []
        self._generation = 0
        self._history: List[float] = []

    # ── public interface ──────────────────────────────────

    def initialize(self) -> None:
        self._population = []
        n = self.problem.num_components
        m = self.problem.num_computers
        for _ in range(self.pop_size):
            perm = list(range(m))
            self.rng.shuffle(perm)
            if n > m:
                perm += [MISSING] * (n - m)
            elif n < m:
                perm = perm[:n]
            else:
                perm = perm[:n]
            self._population.append(perm)
        self._evaluate()
        self._generation = 0

    def step(self) -> Solution:
        if not self._population:
            self.initialize()

        parents = self._select()
        children = []
        for i in range(0, len(parents) - 1, 2):
            p1, p2 = parents[i], parents[i + 1]
            c1, c2 = self._crossover(p1, p2)
            c1 = self._mutate(c1)
            c2 = self._mutate(c2)
            children.extend([c1, c2])
        if len(parents) % 2 == 1:
            child = list(parents[-1])
            child = self._mutate(child)
            children.append(child)

        self._population = children[: self.pop_size]
        self._evaluate()
        self._generation += 1
        return self.get_best()

    def run(self) -> Solution:
        self.initialize()
        for _ in range(self.generations):
            self.step()
        return self.get_best()

    def set_population_size(self, size: int) -> None:
        """Reduce la poblacion en marcha, conservando a los mejores individuos.

        Se usa al cambiar de dificultad a mitad de una ronda: el GA sigue
        buscando de verdad, solo que con menos recursos. Nunca se agranda.
        """
        size = max(2, int(size))
        if size >= self.pop_size:
            return
        self.pop_size = size
        if not self._population:
            return
        if len(self._fitnesses) == len(self._population):
            pares = sorted(zip(self._fitnesses, self._population),
                           key=lambda t: t[0], reverse=True)[:size]
            self._population = [ind for _f, ind in pares]
            self._fitnesses = [f for f, _ind in pares]
        else:
            self._population = self._population[:size]

    def get_best(self) -> Solution:
        if not self._fitnesses:
            return Solution([MISSING] * self.problem.num_components)
        best_idx = max(range(len(self._fitnesses)), key=lambda i: self._fitnesses[i])
        return ScoringSystem.evaluate(self.problem, self._population[best_idx])

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def history(self) -> List[float]:
        return list(self._history)

    # ── internals ─────────────────────────────────────────

    def _evaluate(self) -> None:
        self._fitnesses = []
        for ind in self._population:
            sol = ScoringSystem.evaluate(self.problem, ind)
            self._fitnesses.append(sol.fitness)
        if self._fitnesses:
            self._history.append(max(self._fitnesses))

    def _select(self) -> List[List[int]]:
        selected = []
        for _ in range(self.pop_size):
            a, b = self.rng.sample(range(len(self._population)), 2)
            if self._fitnesses[a] >= self._fitnesses[b]:
                selected.append(list(self._population[a]))
            else:
                selected.append(list(self._population[b]))
        return selected

    def _crossover(
        self, p1: List[int], p2: List[int]
    ) -> Tuple[List[int], List[int]]:
        if self.rng.random() > self.crossover_rate:
            return list(p1), list(p2)

        n = len(p1)
        active1 = [(i, v) for i, v in enumerate(p1) if v >= 0]
        active2 = [(i, v) for i, v in enumerate(p2) if v >= 0]

        if len(active1) < 2:
            return list(p1), list(p2)

        size = len(active1)
        start, end = sorted(self.rng.sample(range(size), 2))

        vals1 = [v for _, v in active1]
        vals2 = [v for _, v in active2]

        child1_vals = [-1] * size
        child2_vals = [-1] * size

        child1_vals[start : end + 1] = vals1[start : end + 1]
        child2_vals[start : end + 1] = vals2[start : end + 1]

        fill1 = [v for v in vals2 if v not in child1_vals[start : end + 1]]
        fill2 = [v for v in vals1 if v not in child2_vals[start : end + 1]]

        idx1 = 0
        for i in range(size):
            if child1_vals[i] == -1 and idx1 < len(fill1):
                child1_vals[i] = fill1[idx1]
                idx1 += 1

        idx2 = 0
        for i in range(size):
            if child2_vals[i] == -1 and idx2 < len(fill2):
                child2_vals[i] = fill2[idx2]
                idx2 += 1

        child1 = list(p1)
        child2 = list(p2)
        for idx, (i, _) in enumerate(active1):
            child1[i] = child1_vals[idx]
        for idx, (i, _) in enumerate(active2):
            child2[i] = child2_vals[idx]

        return child1, child2

    def _mutate(self, ind: List[int]) -> List[int]:
        ind = list(ind)
        active = [i for i, v in enumerate(ind) if v >= 0]
        if len(active) < 2:
            return ind

        for i in active:
            if self.rng.random() < self.mutation_rate:
                j = self.rng.choice(active)
                ind[i], ind[j] = ind[j], ind[i]
        return ind
