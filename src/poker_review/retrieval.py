"""BM25 baseline, optional cached embeddings, and metadata-filtered hand search."""

import hashlib
import math
import os
import re
from collections import Counter


def tokens(text):
    words = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.lower())
    result = []
    for word in words:
        result.extend([word] if word.isascii() else [word[i:i + 2] for i in range(max(1, len(word) - 1))])
    return result


def chunks(notes):
    result = []
    for note in notes:
        for offset in range(0, len(note["body"]), 550):
            body = note["body"][offset:offset + 700]
            result.append({"id": f"{note['id']}:{offset}", "document_id": note["id"],
                           "title": note["title"], "body": body, "source": note["source"],
                           "tags": note["tags"], "offset": offset})
    return result


def bm25(query, documents):
    terms = set(tokens(query))
    corpus = [tokens(d["title"] + " " + " ".join(d["tags"]) + " " + d["body"]) for d in documents]
    mean_length = sum(map(len, corpus)) / max(1, len(corpus))
    scores = []
    for terms_in_doc in corpus:
        counts = Counter(terms_in_doc)
        score = 0.0
        for term in terms:
            frequency = counts[term]
            df = sum(term in doc for doc in corpus)
            idf = math.log(1 + (len(corpus) - df + 0.5) / (df + 0.5))
            norm = frequency + 1.2 * (0.25 + 0.75 * len(terms_in_doc) / max(1, mean_length))
            score += idf * frequency * 2.2 / norm if frequency else 0
        scores.append(score)
    return scores


def embeddings(store, texts, client=None):
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    keys = [hashlib.sha256((model + "\0" + text).encode()).hexdigest() for text in texts]
    vectors = [store.vector(key) for key in keys]
    missing = [i for i, vector in enumerate(vectors) if vector is None]
    if missing:
        if client is None:
            from openai import OpenAI
            client = OpenAI(timeout=30, max_retries=1)
        response = client.embeddings.create(model=model, input=[texts[i] for i in missing])
        for item in response.data:
            index = missing[item.index]
            vectors[index] = item.embedding
            store.save_vector(keys[index], item.embedding)
    return vectors


def search_notes(store, query, top_k=3, tag=None, backend=None, client=None):
    documents = chunks([n for n in store.notes() if not tag or tag in n["tags"]])
    backend = backend or os.getenv("POKER_RETRIEVAL", "bm25")
    if not documents or not query.strip():
        return {"backend": backend, "hits": []}
    if backend == "openai":
        vectors = embeddings(store, [query] + [d["title"] + " " + d["body"] for d in documents], client)
        q = vectors[0]
        def cosine(v):
            return sum(a * b for a, b in zip(q, v)) / max(1e-12, math.sqrt(sum(x*x for x in q) * sum(x*x for x in v)))
        scores = [cosine(v) for v in vectors[1:]]
    else:
        scores = bm25(query, documents)
        backend = "bm25"
    ranked = sorted(zip(scores, documents), key=lambda pair: (-pair[0], pair[1]["id"]))
    return {"backend": backend, "hits": [{**doc, "score": round(score, 4)} for score, doc in ranked[:top_k] if score > 0]}


def similar_hands(store, report, exclude=None, include_demo=False):
    results = []
    for hand in store.hands():
        if hand["id"] == exclude or (hand["is_demo"] and not include_demo):
            continue
        other = hand["report"]
        # Hard filter first: similar position AND card class. Then rank decision contexts.
        if other["hero_position"] != report["hero_position"] or other["hand_class"] != report["hand_class"]:
            continue
        if other.get("depth_bucket") != report.get("depth_bucket") or other.get("pot_type") != report.get("pot_type"):
            continue
        a = {c for d in report["decisions"] for c in d["contexts"]}
        b = {c for d in other["decisions"] for c in d["contexts"]}
        score = len(a & b) / max(1, len(a | b))
        results.append({"hand_id": hand["id"], "score": score, "cards": other["hero_cards"],
                        "position": other["hero_position"], "is_demo": hand["is_demo"]})
    return sorted(results, key=lambda item: (-item["score"], item["hand_id"]))[:5]
