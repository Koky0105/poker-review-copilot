# Poker Review Copilot

A post-game review tool for 9-max No-Limit Hold'em cash games.

## Problem

Hand histories are often incomplete, and language models can
miscalculate pots or give strategy advice without enough context.

## Approach

- Validate structured hand histories.
- Calculate pot sizes, remaining stacks, SPR, and pot odds in Python.
- Retrieve relevant strategy notes and previously reviewed hands.
- Generate explanations with sources and explicit assumptions.

## Planned Stack

Python, FastAPI, Pydantic, React, TypeScript, PostgreSQL, pgvector.

## Milestones

- [ ] Define and validate the hand-history schema.
- [ ] Reconstruct pots and stacks from player actions.
- [ ] Build a hand-entry and replay interface.
- [ ] Retrieve relevant notes and historical hands.
- [ ] Generate grounded reviews.
- [ ] Evaluate retrieval and answer quality.

## Initial Scope

Nine-handed NLH cash games with standard blinds.
Additional formats will be added incrementally.