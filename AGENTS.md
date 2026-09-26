# AGENTS.md — PC Repair Challenge

## What This Is

Educational pixel-art game that teaches the Linear Assignment Problem. Player competes against a Genetic Algorithm to assign computer components to damaged PCs. Children are the target audience.

## Architecture Rules

- **Separation is mandatory.** Optimization logic (`ProblemGenerator`, `GeneticAlgorithm`, `AssignmentProblem`) must be fully independent of rendering, input, and UI. This is non-negotiable — the spec requires the GA and problem generator to be testable standalone.
- **No math on screen during gameplay.** All optimization is expressed through percentages, colors, progress bars, animations. Equations are forbidden in normal mode.
- **Centralized scoring.** One scoring module. Do not scatter score formulas across files.
- **Deterministic when seeded.** Both `ProblemGenerator` and `GeneticAlgorithm` must accept a random seed and reproduce identical results. Critical for debugging and experiments.

## MVP-First — Do NOT Build Everything

The spec lists 54 sections. Ignore most of them initially. Build **Phase 1 → Phase 4** only until MVP works:

1. Math core (assignment representation, scoring, problem generation)
2. Genetic Algorithm (standalone, testable)
3. Basic game prototype (one level, pixel art, repair animation)
4. PC PLAYER integration (GA vs human)

User profiles, leaderboard, customization, audio progression — **Phase 5+**. No database (user asked to drop it). Do not add until MVP is playable.

## Key Domain Concepts

| Concept | Notes |
|---|---|
| Assignment matrix | Rows = components, Cols = computers, Values = repair contribution |
| Repair requirement | Each computer has a target % |
| Over-repair penalty | Exceeding requirement wastes capacity — penalize in scoring |
| Fitness function | Must balance: requirement satisfaction + efficiency + speed |
| GA population | Operates on the same problem instance as the player |

## Module Structure (Actual)

```
core/            # ProblemGenerator, AssignmentProblem, scoring (no UI deps)
algorithm/       # GeneticAlgorithm (standalone, no UI deps, seeded)
game/            # engine.py (logic), states.py, render.py, tutorial.py + tutorial_render.py
assets/          # pixel-art sprites + logo PNGs in root
ui/              # particle/transition effects
audio/           # synthesized music + sfx (numpy)
tests/           # test_core.py (pure stdlib, no pygame)
```

## Development Phases

- **Phase 1–2**: Pure Python, no rendering. CLI or test-only. Validates math + GA correctness.
- **Phase 3–4**: Add game engine, sprites, animation. MVP becomes playable.
- **Phase 5+**: User profiles, database, progression, polish.

## Gotchas

- The GA must **not** use hardcoded optimal solutions. It must visibly search.
- Three outcomes only: WIN, LOSS, DRAW (with tie threshold).
- Problem difficulty scales via: count of computers/components, value similarity, conflicts, scarcity — not just bigger numbers.
- Pixel art resolution: 320×180 or 384×216, integer-scaled. Never bilinear.
- Color alone must never indicate success/failure — always pair with icons or text.

## Tech Stack

_In use:_ Python + Pygame (pixel art), numpy (audio synthesis).
- Keep dependencies minimal.* The GA and problem generator are pure stdlib.
