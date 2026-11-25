"""Small, explicit offline retrieval regression set; not a poker-quality score."""

import json
import tempfile
from pathlib import Path

from poker_review.knowledge import seed_notes
from poker_review.retrieval import search_notes
from poker_review.storage import Store

CASES = [
    ("pot odds equity", "note-price"), ("跟注價格", "note-price"),
    ("SPR low spr", "note-spr"), ("低SPR", "note-spr"),
    ("QQ premium large open", "note-premium"), ("強口袋對", "note-premium"),
    ("overbet bluff catch", "note-overbet"), ("超池下注", "note-overbet"),
    ("position multiway OOP", "note-position"), ("selection bias leak", "note-evidence"),
]


def evaluate():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(str(Path(folder) / "eval.db"))
        seed_notes(store)
        rows = []
        for query, expected in CASES:
            hits = search_notes(store, query, backend="bm25")["hits"]
            ids = [hit["document_id"] for hit in hits]
            rank = ids.index(expected) + 1 if expected in ids else None
            rows.append({"query":query,"expected":expected,"rank":rank})
    return {"dataset":"10 hand-written query/source pairs; original educational notes", "backend":"bm25",
            "hit_at_3":sum(r["rank"] is not None for r in rows)/len(rows),
            "mrr_at_3":sum(1/r["rank"] if r["rank"] else 0 for r in rows)/len(rows), "cases":rows}


if __name__ == "__main__":
    print(json.dumps(evaluate(),ensure_ascii=False,indent=2))
