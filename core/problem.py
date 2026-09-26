"""
Assignment problem representation and generation.
Separable from any UI code.
"""

from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

MISSING = -1


@dataclass
class AssignmentProblem:
    num_computers: int
    num_components: int
    requirements: List[int]
    contributions: List[List[int]]
    seed: Optional[int] = None
    level_name: str = ""


@dataclass
class Solution:
    assignment: List[int]
    score: float = 0.0
    fitness: float = 0.0
    efficiency: float = 0.0
    requirement_met: int = 0
    waste: float = 0.0


class ProblemGenerator:
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self._rng = random.Random(seed)

    def generate(
        self,
        num_computers: int,
        num_components: int,
        req_range: Tuple[int, int] = (40, 80),
        cap_range: Tuple[int, int] = (30, 95),
        level_name: str = "",
    ) -> AssignmentProblem:
        requirements = [
            self._rng.randint(req_range[0], req_range[1])
            for _ in range(num_computers)
        ]
        contributions = []
        for _ in range(num_components):
            row = [
                self._rng.randint(cap_range[0], cap_range[1])
                for _ in range(num_computers)
            ]
            contributions.append(row)

        return AssignmentProblem(
            num_computers=num_computers,
            num_components=num_components,
            requirements=requirements,
            contributions=contributions,
            seed=self.seed,
            level_name=level_name,
        )
