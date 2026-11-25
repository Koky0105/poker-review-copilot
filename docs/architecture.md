# Architecture and interview discussion

## Product boundary

Felt is a single-user, local post-game review application. A hand can stop at a decision point.
The application identifies repeated recorded behavior and supplies references; it does not claim to solve poker.

## Data path

1. `models.py` validates input contracts: nine unique positions/seats, card uniqueness, player references and explicit action amounts.
2. `engine.py` replays events into before/after snapshots. A call adds only the difference from street commitment. Each transition preserves total chips.
3. `analysis.py` captures Hero decisions with only board cards visible on that street. It derives contexts and denominators from computed facts.
4. `storage.py` persists raw input, deterministic reports and optional review output. Updating a hand clears stale review text. Identical payloads under different IDs are rejected.
5. `retrieval.py` chunks notes with source IDs and overlapping character spans, then ranks them with BM25. Optional real embeddings use cosine similarity and model/text-digest caches.
6. `ai.py` passes decision facts and retrieved references to a structured-output model. It validates every cited source ID before saving the output. A separate deterministic baseline is labeled as rules, never as AI.
7. `api.py` serves JSON endpoints and the production React build. Decimal values cross the API as strings; the frontend formats them for display rather than recalculating pots.

## Poker state invariants

- Remaining chips plus unawarded pot equals initial chips after every action.
- A folded or all-in player cannot take a later action.
- Players may check only with no amount to call.
- Short calls are allowed only up to the player's remaining stack.
- Full raises update the minimum increment; cumulative short all-ins are compared with each player's last faced wager and raise requirement.
- Only unmatched contributions are refunded after a round closes. Folded money remains in pot layers; folded players are excluded from eligible winners.
- The replay engine does not evaluate cards or distribute the pot at showdown.

No-limit raise/reopening conventions were checked against [Poker TDA's rules](https://www.pokertda.com/view-poker-tda-rules/) and the [short-opening-bet discussion](https://www.pokertda.com/forum/index.php?topic=1456.0). These are conventions used by this engine; a cash room's house rules can differ. Non-standard verbal declarations, string bets and floor rulings are outside the event model.

## Retrieval design

The zero-key baseline is lexical BM25, including Chinese bigram tokens. It is explicitly not called semantic search. Optional OpenAI embeddings add semantic retrieval without introducing a large orchestration framework. Notes retain document IDs, chunk offsets and source labels. The corpus is tiny, so an in-process cosine scan is adequate. At larger scale, move vector indexing to a database and evaluate latency/recall.

Similar personal hands are filtered by position, hand class, effective-depth bucket and pot type before ranking shared contexts. The current classifier uses broad buckets, so similar results remain comparisons, not proof that strategies should match. Demo hands are excluded.

## Pattern detection

There are three transparent opportunity categories: premium pairs facing a single oversized preflop open (at least 10 BB), low heads-up street-start SPR (at most 3) facing a bet, and facing an opening postflop bet at least as large as its original pot. Counts describe call/fold frequencies in those opportunities.

Three matching decisions trigger the UI label “repeated pattern”; this is only a display threshold. No statistical confidence is attached. Correct strategy requires an independent range/solver/coach baseline and suitable sampling. Selection bias remains even after exact duplicate prevention.

## AI reliability and limits

The [structured output contract](https://developers.openai.com/api/docs/guides/structured-outputs) controls shape, not correctness. Citation-ID validation prevents nonexistent references, not unsupported prose. Retrieved content is explicitly treated as untrusted data in the prompt. Computed arithmetic is displayed separately. Source notes can be wrong or inapplicable, and prompt instructions cannot guarantee protection against every injection.

The [embedding API](https://developers.openai.com/api/docs/guides/embeddings) is optional, cached and configured only on the backend. Missing keys, provider refusals, rate limits and invalid outputs are surfaced as failed operations, with no silently generated “AI” substitute.

## Interview pitch

> I built a local-first nine-handed poker review studio with React and FastAPI. A deterministic replay engine reconstructs pots and stacks, validates betting transitions, and captures pre-decision snapshots. A retrieval layer supplies traceable notes to structured AI reviews, while a separate aggregation layer reports repeated behavior with explicit opportunity denominators. I separated arithmetic, retrieval and generation so they can be tested independently.

Be precise about implementation: SQLite and optional cached vectors are implemented; PostgreSQL/pgvector, authentication, solver integration and cloud deployment are not. The offline rules baseline runs end to end. Live provider contracts have mock tests, while paid output quality still needs validation using a real key and a larger reviewed dataset.
