"""
Standalone tests for the math core and the Genetic Algorithm.
Pure stdlib — no pygame. Run with: python3 tests/test_core.py
(or pytest tests/).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.problem import ProblemGenerator, MISSING
from core.scoring import ScoringSystem
from algorithm.genetic import GeneticAlgorithm


def _fixed_problem():
    return ProblemGenerator(seed=7).generate(
        num_computers=3, num_components=3, level_name="test"
    )


def test_generator_deterministic():
    a = ProblemGenerator(seed=42).generate(3, 3)
    b = ProblemGenerator(seed=42).generate(3, 3)
    c = ProblemGenerator(seed=43).generate(3, 3)
    assert a.requirements == b.requirements
    assert a.contributions == b.contributions
    assert a != c  # different seed -> different problem (very unlikely collision)


def test_generator_different_seeds_differ():
    a = ProblemGenerator(seed=1).generate(4, 4)
    b = ProblemGenerator(seed=2).generate(4, 4)
    same = (a.requirements == b.requirements
            and a.contributions == b.contributions)
    assert not same


def test_missing_is_invalid():
    assert MISSING == -1


def test_ga_deterministic_with_seed():
    p = _fixed_problem()
    sol_a = GeneticAlgorithm(p, seed=99).run()
    sol_b = GeneticAlgorithm(p, seed=99).run()
    assert sol_a.assignment == sol_b.assignment
    assert sol_a.score == sol_b.score
    assert GeneticAlgorithm(p, seed=98).run().assignment != sol_a.assignment


def test_ga_history_is_deterministic():
    p = _fixed_problem()
    ga = GeneticAlgorithm(p, generations=5, seed=5)
    ga.run()
    h1 = ga.history
    ga2 = GeneticAlgorithm(p, generations=5, seed=5)
    ga2.run()
    assert h1 == ga2.history


def test_ga_improves_over_running():
    p = _fixed_problem()
    ga = GeneticAlgorithm(p, generations=20, seed=3)
    ga.initialize()
    first = max(ga.history)
    final = ga.run()
    assert final.score >= first - 1e-9


def test_ga_produces_valid_one_to_one_assignment():
    p = _fixed_problem()
    sol = GeneticAlgorithm(p, seed=11).run()
    active = [c for c in sol.assignment if c != MISSING]
    assert len(active) == len(set(active)), "a computer used twice"
    assert all(0 <= c < p.num_computers for c in active)


def test_ga_uses_same_problem_as_player():
    p = _fixed_problem()
    sol = GeneticAlgorithm(p, seed=21).run()
    for comp_idx, cpu in enumerate(sol.assignment):
        if cpu == MISSING:
            continue
        assert p.contributions[comp_idx][cpu] >= 0  # value comes from the problem


def _perfect_problem():
    # Two computers, two components, zero waste if each goes to its match.
    from core.problem import AssignmentProblem
    return AssignmentProblem(
        num_computers=2,
        num_components=2,
        requirements=[50, 50],
        contributions=[[50, 70], [90, 50]],
        seed=None,
    )


def test_scoring_requirements_and_efficiency():
    p = _perfect_problem()
    sol = ScoringSystem.evaluate(p, [0, 1])  # 50->PC1, 50->PC2, no waste
    assert sol.requirement_met == 2
    assert abs(sol.waste) < 1e-9
    assert sol.score == 100 + 60 + 20  # req + efficiency * 60? (100% eff) + bonus


def test_scoring_punishes_over_repair():
    p = _perfect_problem()
    ok = ScoringSystem.evaluate(p, [0, 1])
    over = ScoringSystem.evaluate(p, [1, 1])  # 70 + 50 on PC2, PC1 unmet
    assert over.waste > 0
    assert over.score < ok.score


def test_scoring_missing_component_ignored():
    p = _perfect_problem()
    sol = ScoringSystem.evaluate(p, [0, MISSING])
    assert sol.requirement_met == 1
    assert sol.score < ScoringSystem.evaluate(p, [0, 1]).score


def test_compare_igualar_al_algoritmo_es_victoria():
    p = _perfect_problem()
    player = ScoringSystem.evaluate(p, [0, 1])
    ai = ScoringSystem.evaluate(p, [1, 0])  # also 90/70 -> PC1, but PC1=50, PC2=50
    assert ScoringSystem.compare(player, ai, 0.0) == "WIN"
    assert ScoringSystem.compare(ai, player, 0.0) == "LOSS"
    # Cerca pero sin igualar: solo hay empate dentro del umbral.
    assert ScoringSystem.compare(ai, player, 10_000) == "DRAW"
    # Llegar a la MISMA solucion que el algoritmo tambien gana la carrera.
    mismo = ScoringSystem.evaluate(p, [0, 1])
    assert mismo.score == player.score
    assert ScoringSystem.compare(mismo, player, 0.0) == "WIN"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL  {name}: {e}")
    if failures:
        sys.exit(1)
    print(f"\n{sum(1 for n in globals() if n.startswith('test_') and callable(globals()[n])) - failures} passed")