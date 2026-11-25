import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from poker_review.ai import Observation, ProviderError, ReviewText, generate_review
from poker_review.api import create_app
from poker_review.retrieval import search_notes, embeddings


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("POKER_RETRIEVAL", "bm25")
    with TestClient(create_app(str(tmp_path / "poker.db"))) as client:
        yield client


def example(client):
    return client.get("/api/example").json()


def test_preview_save_read_rules_review_and_persistence(client):
    hand = example(client)
    preview = client.post("/api/analyze", json=hand)
    assert preview.status_code == 200
    assert preview.json()["pot"] == "253"
    assert len(preview.json()["decisions"]) == 2
    assert client.get("/api/hands").json() == []
    saved = client.post("/api/hands", json={"hand":hand,"is_demo":True})
    assert saved.status_code == 201
    assert saved.json()["is_demo"]
    assert client.get("/api/stats").json()["hands"] == 0
    result = client.post(f"/api/hands/{hand['hand_id']}/review", json={"mode":"rules"})
    assert result.status_code == 200
    assert result.json()["mode"] == "rules"
    assert result.json()["sources"]
    assert client.get(f"/api/hands/{hand['hand_id']}").json()["review"]["mode"] == "rules"
    other = TestClient(create_app(client.app.state.store.path))
    assert len(other.get("/api/hands").json()) == 1


def test_duplicate_hands_cannot_inflate_sample(client):
    hand = example(client)
    assert client.post("/api/hands", json={"hand":hand}).status_code == 201
    hand["hand_id"] = "different-id-same-hand"
    assert client.post("/api/hands", json={"hand":hand}).status_code == 409
    assert client.get("/api/stats").json()["hands"] == 1


def test_update_replaces_decisions_and_clears_stale_review(client):
    hand = example(client)
    client.post("/api/hands", json={"hand":hand})
    client.post(f"/api/hands/{hand['hand_id']}/review",json={"mode":"rules"})
    hand["actions"][-2]["amount_to"] = "150"
    result = client.post("/api/hands", json={"hand":hand})
    assert result.status_code == 201
    assert result.json()["review"] is None
    assert client.get("/api/stats").json()["decisions"] == 2


def test_denominators_and_evidence_exclude_demo(client):
    for index in range(4):
        hand = example(client)
        hand["hand_id"] = f"hand-{index}"
        hand["players"][0]["starting_stack"] = str(650+index)
        response = client.post("/api/hands", json={"hand":hand,"is_demo":index==3})
        assert response.status_code == 201
    stats = client.get("/api/stats").json()
    pattern = next(p for p in stats["patterns"] if p["id"] == "premium_large_open")
    assert pattern["opportunities"] == pattern["matches"] == 3
    assert pattern["status"] == "repeated_pattern"
    assert len(pattern["evidence"]) == 3
    assert stats["demo_hands"] == 1


def test_metadata_filter_for_similar_hands(client):
    hand = example(client)
    client.post("/api/hands", json={"hand":hand})
    hand["hand_id"] = "similar"
    hand["players"][0]["starting_stack"] = "700"
    client.post("/api/hands", json={"hand":hand})
    similar = client.get("/api/hands/similar/similar").json()
    assert similar[0]["hand_id"] == "synthetic-qq-large-open"


def test_reject_invalid_replay_without_saving(client):
    hand = example(client)
    hand["actions"][0]["player_id"] = "p2"
    result = client.post("/api/hands", json={"hand":hand})
    assert result.status_code == 422
    assert "Out of turn" in result.json()["detail"]
    assert client.get("/api/hands").json() == []


def test_search_sources_and_new_note(client):
    result = client.get("/api/search", params={"q":"pot odds equity"}).json()
    assert result["backend"] == "bm25"
    assert result["hits"][0]["document_id"] == "note-price"
    note = client.post("/api/notes", json={"title":"獨特情境 zebra", "body":"zebra squeeze scenario", "tags":["custom"]}).json()
    result = client.get("/api/search", params={"q":"zebra","tag":"custom"}).json()
    assert result["hits"][0]["document_id"] == note["id"]
    assert client.get("/api/search",params={"q":"unfindablexyz"}).json()["hits"] == []


def test_live_requires_key_and_config_does_not_leak_secret(client, monkeypatch):
    hand = example(client)
    client.post("/api/hands",json={"hand":hand})
    assert client.post(f"/api/hands/{hand['hand_id']}/review",json={"mode":"openai"}).status_code == 503
    assert client.post("/api/parse",json={"text":"a hand"}).status_code == 503
    monkeypatch.setenv("OPENAI_API_KEY","private-test-key")
    result = client.get("/api/config")
    assert result.json()["ai_enabled"]
    assert "private-test-key" not in result.text


def test_delete_and_unknown_id(client):
    hand = example(client)
    client.post("/api/hands",json={"hand":hand})
    assert client.delete(f"/api/hands/{hand['hand_id']}").status_code == 200
    assert client.get(f"/api/hands/{hand['hand_id']}").status_code == 404
    assert client.get("/api/stats").json()["hands"] == 0


def test_future_cards_do_not_appear_in_earlier_decisions(client):
    hand = example(client)
    result = client.post("/api/analyze",json=hand).json()
    assert result["decisions"][0]["board"] == []
    assert result["decisions"][1]["board"] == ["Ah","8c","2d"]


def test_invalid_citations_are_rejected():
    text = ReviewText(summary="test",observations=[Observation(text="test",source_ids=["invented"])],assumptions=[],alternatives=[],missing_information=[],next_steps=[])
    fake = SimpleNamespace(responses=SimpleNamespace(parse=lambda **kwargs:SimpleNamespace(output_parsed=text,usage=None)))
    with pytest.raises(ProviderError,match="引用"):
        generate_review({"decisions":[],"assumptions":[]}, [], "openai", fake)


def test_live_structured_output_contract_and_usage():
    text = ReviewText(summary="review",observations=[Observation(text="evidence",source_ids=["source:0"])],assumptions=[],alternatives=[],missing_information=[],next_steps=[])
    def parse(**kwargs):
        assert kwargs["store"] is False
        assert kwargs["text_format"] is ReviewText
        return SimpleNamespace(output_parsed=text, usage=SimpleNamespace(model_dump=lambda:{"total_tokens":100}))
    result = generate_review({"decisions":[],"assumptions":[]},[{"id":"source:0"}],"openai",SimpleNamespace(responses=SimpleNamespace(parse=parse)))
    assert result["usage"]["total_tokens"] == 100
    assert result["mode"] == "openai"


def test_embeddings_cached_by_model_and_text(client):
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(index=i,embedding=[float(i),1.0]) for i in range(len(kwargs["input"]))])
    fake = SimpleNamespace(embeddings=SimpleNamespace(create=create))
    first = embeddings(client.app.state.store,["one","two"],fake)
    second = embeddings(client.app.state.store,["one","two"],fake)
    assert first == second
    assert len(calls) == 1
    result = search_notes(client.app.state.store,"SPR",backend="openai",client=fake)
    assert result["backend"] == "openai"
    assert result["hits"]


def test_different_choice_is_in_denominator_but_not_numerator(client):
    hand = example(client)
    hand["actions"][6] = {"street":"preflop","player_id":"hero","type":"fold"}
    hand["actions"] = hand["actions"][:9]
    assert client.post("/api/hands",json={"hand":hand}).status_code == 201
    pattern = next(p for p in client.get("/api/stats").json()["patterns"] if p["id"]=="premium_large_open")
    assert pattern["opportunities"] == 1
    assert pattern["matches"] == 0
    assert pattern["rate"] == 0


def test_provider_failure_does_not_expose_error_body():
    def fail(**kwargs):
        raise RuntimeError("sensitive-key-provider-body")
    fake = SimpleNamespace(responses=SimpleNamespace(parse=fail))
    with pytest.raises(ProviderError) as captured:
        generate_review({"decisions":[],"assumptions":[]},[],"openai",fake)
    assert "sensitive-key" not in str(captured.value)


def test_refused_structured_output_is_not_saved_as_review():
    fake = SimpleNamespace(responses=SimpleNamespace(parse=lambda **kw:SimpleNamespace(output_parsed=None,usage=None)))
    with pytest.raises(ProviderError,match="結構化"):
        generate_review({"decisions":[],"assumptions":[]},[],"openai",fake)


def test_production_frontend_and_unknown_api_routes(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>Felt</title>")
    (dist / "assets" / "app.js").write_text("console.log('Felt')")
    monkeypatch.setenv("POKER_FRONTEND_DIST",str(dist))
    app = TestClient(create_app(str(tmp_path/"app.db")))
    assert "<title>Felt</title>" in app.get("/").text
    assert app.get("/assets/app.js").status_code == 200
    assert app.get("/api/not-a-route").status_code == 404


def test_stale_review_cannot_attach_to_updated_hand(client):
    hand = example(client)
    first = client.post("/api/hands",json={"hand":hand}).json()
    hand["actions"][-2]["amount_to"] = "150"
    client.post("/api/hands",json={"hand":hand})
    with pytest.raises(ValueError,match="已更新"):
        client.app.state.store.save_review(hand["hand_id"],{"summary":"old"},first["updated_at"])
    assert client.get(f"/api/hands/{hand['hand_id']}").json()["review"] is None
