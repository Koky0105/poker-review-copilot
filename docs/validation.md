# Validation record

## Executed locally

- Python 3.12: 74 tests cover schema validation, replay arithmetic, turn order, street transitions, side-pot eligibility, all-in refunds, cumulative short-raise reopening, persistence, exact duplicates, statistic denominators, source lookup, provider contracts, citation rejection, stale-review protection and production static routing.
- TypeScript type checking and Vite production build passed.
- Three Playwright browser tests passed: record/save/replay/review/source lookup/search/delete; invalid input remains editable; mobile navigation and no full-page horizontal overflow at 390px.
- Desktop (1440px) and mobile (390px) screenshots were inspected during development.
- Ten handwritten BM25 query/source regression pairs: hit@3 = 1.0; MRR@3 = 1.0. Queries intentionally target the six seed notes and are not a held-out quality benchmark.
- The CLI reproduces the QQ example: flop pot 253, Hero stack 525, street-start SPR 2.08, call price 35.17%, and uncalled refund 300 after the fold.

## Validation limits

- OpenAI structured reviews, parsing and embeddings were exercised with mocked provider contracts and explicit failure cases. No real paid provider request was made; real-account model availability and prose quality remain user-configured checks.
- Docker and Compose files are provided, but a Docker daemon was not available for a local image build.
- The Windows startup script is supplied; the commands were validated through their Linux equivalents, not a native Windows PowerShell session.
- Browser tests ran with a registry-distributed headless Chromium executable via `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`. Normal installations use `npx playwright install chromium`.
- CI configuration is included. This document reports local runs and does not claim a GitHub Actions result.
- No solver, expert-labeled strategy dataset, equity evaluator, live gameplay integration or public hosting is included. Pattern rates must not be presented as confirmed leaks or accuracy metrics.

## Reproduce

Follow README startup and validation commands. Tests use temporary synthetic data. Exact counts are tied to this version; new tests may increase them.
