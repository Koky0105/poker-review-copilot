"""Local-first application API and built React application host."""

import os
import re
import uuid
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from poker_review.ai import ProviderError, generate_review, parse_hand
from poker_review.analysis import aggregate_patterns, analyze
from poker_review.engine import ReplayError
from poker_review.knowledge import seed_notes
from poker_review.models import PokerHand
from poker_review.retrieval import search_notes, similar_hands
from poker_review.storage import Store, encode


class SaveHand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hand: PokerHand
    is_demo: bool = False


class NoteInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20000)
    source: str = Field(default="個人筆記（未驗證策略）", max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=20)


class TextInput(BaseModel):
    text: str = Field(min_length=1, max_length=30000)


class ReviewInput(BaseModel):
    mode: Literal["rules", "openai"] = "rules"


def response(value, status=200):
    import json
    return JSONResponse(json.loads(encode(value)), status_code=status)


def create_app(db_path=None):
    load_dotenv()
    store = Store(db_path or os.getenv("POKER_DB", ".local/poker.db"))
    seed_notes(store)
    app = FastAPI(title="Felt / Poker Review Copilot", version="1.0.0")
    app.state.store = store
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])

    @app.exception_handler(ReplayError)
    async def replay_error(request, exc):
        return response({"detail": str(exc)}, 422)

    @app.exception_handler(ProviderError)
    async def provider_error(request, exc):
        return response({"detail": str(exc)}, 503)

    @app.get("/api/config")
    def config():
        return {"ai_enabled": bool(os.getenv("OPENAI_API_KEY")), "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                "retrieval": os.getenv("POKER_RETRIEVAL", "bm25"), "version": "1.0.0"}

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/example")
    def example():
        # Packaged resource works after installation and in Docker.
        path = Path(__file__).parent / "data" / "example.json"
        return response(PokerHand.model_validate_json(path.read_text(encoding="utf-8")))

    @app.post("/api/analyze")
    def preview(hand: PokerHand):
        return response(analyze(hand))

    @app.post("/api/hands")
    def save(payload: SaveHand):
        if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}", payload.hand.hand_id):
            raise HTTPException(422, "hand_id 請使用 1–100 個英文、數字、點、底線或連字號。")
        report = analyze(payload.hand)
        try:
            return response(store.save_hand(payload.hand, report, payload.is_demo), 201)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @app.get("/api/hands")
    def hands(q: str = "", position: str = "", include_demo: bool = True):
        items = store.hands()
        return response([h for h in items if (not q or q.lower() in (h["id"] + " " + " ".join(h["report"]["hero_cards"])).lower())
                         and (not position or h["report"]["hero_position"] == position) and (include_demo or not h["is_demo"])])

    def get_hand(hand_id):
        hand = store.hand(hand_id)
        if not hand:
            raise HTTPException(404, "找不到牌局")
        return hand

    @app.get("/api/hands/{hand_id}")
    def hand(hand_id: str):
        return response(get_hand(hand_id))

    @app.delete("/api/hands/{hand_id}")
    def delete(hand_id: str):
        get_hand(hand_id)
        store.delete_hand(hand_id)
        return {"deleted": True}

    @app.get("/api/hands/{hand_id}/similar")
    def similar(hand_id: str):
        item = get_hand(hand_id)
        return response(similar_hands(store, item["report"], exclude=hand_id))

    @app.post("/api/hands/{hand_id}/review")
    def review(hand_id: str, payload: ReviewInput):
        item = get_hand(hand_id)
        contexts = [c for d in item["report"]["decisions"] for c in d["contexts"]]
        query = " ".join(item["report"]["hero_cards"] + contexts + ["pot odds SPR position"])
        try:
            retrieved = search_notes(store, query)
        except Exception as error:
            raise ProviderError("語意檢索失敗；請檢查 API 設定或使用 bm25。") from error
        result = generate_review(item["report"], retrieved["hits"], payload.mode)
        result["retrieval_backend"] = retrieved["backend"]
        try:
            store.save_review(hand_id, result, item["updated_at"])
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        return response(result)

    @app.get("/api/stats")
    def stats():
        return response(aggregate_patterns(store.hands()))

    @app.get("/api/notes")
    def notes():
        return response(store.notes())

    @app.post("/api/notes")
    def add_note(note: NoteInput):
        item = {"id": f"note-{uuid.uuid4().hex[:12]}", **note.model_dump()}
        store.save_note(item)
        return response(item, 201)

    @app.get("/api/search")
    def search(q: str = Query(min_length=1, max_length=1000), tag: str | None = None,
               top_k: int = Query(default=3, ge=1, le=10)):
        try:
            return response(search_notes(store, q, top_k, tag))
        except Exception as error:
            raise ProviderError("搜尋失敗；請檢查語意搜尋設定。") from error

    @app.post("/api/parse")
    def parse(payload: TextInput):
        return response(parse_hand(payload.text, PokerHand.model_json_schema()))

    dist = Path(os.getenv("POKER_FRONTEND_DIST", "frontend/dist")).resolve()
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        if (dist / "index.html").is_file():
            return FileResponse(dist / "index.html")
        return {"message": "API ready. Run npm install && npm run dev in frontend/.", "docs": "/docs"}

    return app
