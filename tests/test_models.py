import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from poker_review.models import PokerHand


@pytest.fixture
def hand_data():
    path = Path(__file__).parents[1] / "examples" / "qq_large_open.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_example_validates_and_round_trips(hand_data):
    hand = PokerHand.model_validate(hand_data)
    assert len(hand.players) == 9
    assert hand.players[6].is_hero
    assert hand.actions[0].amount_to == Decimal("125")
    assert PokerHand.model_validate_json(hand.model_dump_json()) == hand


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda d: d["players"].pop(), "at least 9"),
        (lambda d: d["players"][0].update(seat=7), "seat must be unique"),
        (lambda d: d["players"][0].update(player_id="hero"), "player_id must be unique"),
        (lambda d: d["players"][0].update(position="BTN"), "position must be unique"),
        (lambda d: d["players"][0].update(is_hero=True), "exactly one hero"),
        (lambda d: d["players"][6].update(is_hero=False), "exactly one hero"),
        (lambda d: d.update(hero_cards=["Qs", "Qs"]), "duplicate cards"),
        (lambda d: d.update(board=["Qs", "8c", "2d"]), "duplicate cards"),
        (lambda d: d.update(hero_cards=["Qx", "Qh"]), "pattern"),
        (lambda d: d.update(board=["Ah", "8c"]), "board must contain"),
        (lambda d: d["actions"][0].update(player_id="unknown"), "unknown player"),
        (lambda d: d["actions"][0].pop("amount_to"), "requires amount_to"),
        (lambda d: d["actions"][1].update(amount_to="5"), "cannot have amount_to"),
        (lambda d: d["actions"][0].update(amount_to="-1"), "greater than 0"),
        (lambda d: d["players"][0].update(starting_stack="NaN"), "finite"),
        (lambda d: d.update(small_blind="2"), "less than big_blind"),
        (lambda d: d["forced_bets"][0].update(player_id="hero"), "must be posted by"),
        (lambda d: d["forced_bets"][0].update(amount="2"), "blind amount must match"),
        (lambda d: d["forced_bets"][0].update(type="big_blind"), "exactly one small blind"),
        (lambda d: d["actions"][0].update(amount=125), "Extra inputs"),
    ],
)
def test_inconsistent_histories_are_rejected(hand_data, change, message):
    change(hand_data)
    with pytest.raises(ValidationError, match=message):
        PokerHand.model_validate(hand_data)


def test_short_stack_can_post_partial_blind(hand_data):
    hand_data["players"][8]["starting_stack"] = "1.5"
    hand_data["forced_bets"][1]["amount"] = "1.5"
    assert PokerHand.model_validate(hand_data).forced_bets[1].amount == Decimal("1.5")


def test_amount_to_includes_existing_blind(hand_data):
    # With $2 already posted, raise-to $40 means $38 more. Replay comes in Lesson 2.
    hand_data["actions"] = [
        {"street": "preflop", "player_id": "p9", "type": "raise", "amount_to": "40"}
    ]
    hand = PokerHand.model_validate(hand_data)
    assert hand.actions[0].amount_to - hand.forced_bets[1].amount == Decimal("38")


def test_input_is_not_mutated(hand_data):
    original = deepcopy(hand_data)
    PokerHand.model_validate(hand_data)
    assert hand_data == original
