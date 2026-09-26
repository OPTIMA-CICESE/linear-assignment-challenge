"""
Centralized scoring — single source of truth.
"""

from __future__ import annotations
from typing import List

from .problem import AssignmentProblem, Solution, MISSING


class ScoringSystem:
    WEIGHT_REQ_MET = 100
    WEIGHT_EFFICIENCY = 60
    WEIGHT_WASTE_PENALTY = 40
    WEIGHT_BONUS = 20

    @classmethod
    def evaluate(cls, problem: AssignmentProblem, assignment: List[int]) -> Solution:
        sol = Solution(list(assignment))

        total_req = 0
        total_used = 0
        met = 0
        waste = 0.0

        for cpu_idx in range(problem.num_computers):
            total_req += problem.requirements[cpu_idx]

        for comp_idx, cpu_idx in enumerate(assignment):
            if cpu_idx == MISSING:
                continue
            total_used += problem.contributions[comp_idx][cpu_idx]

        cover_amount = [0] * problem.num_computers
        for comp_idx, cpu_idx in enumerate(assignment):
            if cpu_idx != MISSING:
                cover_amount[cpu_idx] += problem.contributions[comp_idx][cpu_idx]

        for cpu_idx in range(problem.num_computers):
            if cover_amount[cpu_idx] >= problem.requirements[cpu_idx]:
                met += 1
                over = cover_amount[cpu_idx] - problem.requirements[cpu_idx]
                waste += over / max(problem.requirements[cpu_idx], 1)

        sol.requirement_met = met
        sol.waste = waste / max(problem.num_computers, 1)

        req_score = (met / max(problem.num_computers, 1)) * cls.WEIGHT_REQ_MET

        if total_used > 0 and total_req > 0:
            sol.efficiency = min(total_req / total_used, 1.0)
        else:
            sol.efficiency = 0.0
        eff_score = sol.efficiency * cls.WEIGHT_EFFICIENCY

        waste_penalty = sol.waste * cls.WEIGHT_WASTE_PENALTY

        bonus = cls.WEIGHT_BONUS if met == problem.num_computers else 0

        sol.score = req_score + eff_score - waste_penalty + bonus
        sol.fitness = sol.score
        return sol

    @classmethod
    def compare(
        cls, player: Solution, ai: Solution, tie_threshold: float = 0.0
    ) -> str:
        """Criterio de victoria por PUNTAJE (score):

        Gana quien obtiene mayor puntaje final. Igualar la mejor solucion del
        algoritmo tambien es victoria: si el jugador llega a la misma solucion
        optima, la carrera se gana. Solo hay EMPATE dentro del umbral, es
        decir, cuando el jugador quedo cerca pero sin igualar al algoritmo.
        """
        diff = player.score - ai.score
        if diff >= 0:
            return "WIN"
        elif diff < -tie_threshold:
            return "LOSS"
        return "DRAW"
