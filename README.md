# Poker Review Copilot

A learning project for post-game review of 9-max No-Limit Hold'em cash hands.

## Current milestone

Lesson 1 implements a validated hand-history schema and a synthetic nine-player
example. Pot reconstruction, strategy retrieval, and LLM reviews are planned.

## Run locally

Python 3.11 or newer is required. From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m poker_review examples/qq_large_open.json
.\.venv\Scripts\python.exe -m pytest -q
```

Using the virtual environment's Python directly also works when PowerShell
script activation is disabled. On macOS/Linux, use `.venv/bin/python` instead.

## Learning path

- [x] Validate a complete nine-player hand-history schema.
- [ ] Replay actions to reconstruct pots and remaining stacks.
- [ ] Build a FastAPI backend and React/TypeScript hand-entry interface.
- [ ] Retrieve relevant notes and historical hands with source metadata.
- [ ] Generate reviews that distinguish facts, assumptions, and suggestions.
- [ ] Evaluate retrieval quality, grounding, latency, and cost.

Read the [first lesson in Traditional Chinese](docs/lesson-01.md).

## Design decisions

- Chip amounts use `Decimal`; JSON examples encode them as strings.
- `amount_to` means a player's total contribution on the current street,
  including live blinds on preflop. It is not an additional payment.
- The opening milestone requires all nine seats to be represented, even if
  players fold. Partial hand histories will need an explicit future format.
- Python will calculate poker arithmetic; retrieved evidence and an LLM will
  support explanations after the arithmetic engine is implemented.

## Limits of Lesson 1

Schema validation checks the shape and consistency of input. It does not yet
validate turn order, betting legality, stack conservation, or street completion.
There is no solver, equity calculator, or strategy recommendation in this version.
The sample is synthetic and illustrates the input format.
