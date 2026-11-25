# Poker Review Copilot

A learning project for post-game review of 9-max No-Limit Hold'em cash hands.

## Current milestone

Lessons 1 and 2 implement a validated hand-history schema and deterministic
betting replay, with per-action pot and stack snapshots and Hero decision prices.
Strategy retrieval and LLM reviews are planned.

## Run locally

Python 3.11 or newer is required. From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m poker_review examples/qq_large_open.json
.\.venv\Scripts\python.exe -m poker_review examples/qq_large_open.json --replay
.\.venv\Scripts\python.exe -m pytest -q
```

Using the virtual environment's Python directly also works when PowerShell
script activation is disabled. On macOS/Linux, use `.venv/bin/python` instead.

## Learning path

- [x] Validate a complete nine-player hand-history schema.
- [x] Replay non-all-in actions to reconstruct pots and remaining stacks.
- [ ] Build a FastAPI backend and React/TypeScript hand-entry interface.
- [ ] Retrieve relevant notes and historical hands with source metadata.
- [ ] Generate reviews that distinguish facts, assumptions, and suggestions.
- [ ] Evaluate retrieval quality, grounding, latency, and cost.

Read the [first lesson in Traditional Chinese](docs/lesson-01.md).
Continue with [Lesson 2: pot and stack replay](docs/lesson-02.md).

## Design decisions

- Chip amounts use `Decimal`; JSON examples encode them as strings.
- `amount_to` means a player's total contribution on the current street,
  including live blinds on preflop. It is not an additional payment.
- The opening milestone requires all nine seats to be represented, even if
  players fold. Partial hand histories will need an explicit future format.
- Python will calculate poker arithmetic; retrieved evidence and an LLM will
  support explanations after the arithmetic engine is implemented.

## Current limits

Replay validates turn order, calls/checks, full minimum raises, street transitions,
and chip conservation for standard-blind hands without all-ins. It returns unmatched
bets after folds. All-ins (including all-in blinds) explicitly raise an unsupported
error; side pots and short-raise reopening need their own milestone. A call-price
report also rejects decisions that would require an all-in call.

SPR is recorded at the start of a heads-up postflop street. Multiway pots do not
receive a single SPR value. Call price is a mathematical break-even fraction under
full equity realization and no further investment, not an estimate of hand equity
or a recommendation to call. The engine holds the pot before payout; it does not
evaluate showdown or award winnings. Rake, antes and straddles are not implemented.
Partial histories remain explicitly incomplete. The sample is synthetic.
