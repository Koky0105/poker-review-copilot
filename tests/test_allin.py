from decimal import Decimal as D
import json
from pathlib import Path

import pytest

from poker_review.engine import ReplayError, apply_action, initial_state, pot_layers, decision_metrics
from poker_review.models import Action, PokerHand


def start(stacks=None):
    data = json.loads((Path(__file__).parents[1] / "examples/qq_large_open.json").read_text())
    for i, stack in (stacks or {}).items():
        data["players"][i]["starting_stack"] = str(stack)
    return initial_state(PokerHand.model_validate(data))


def act(state, player, kind, amount=None):
    return apply_action(state, Action(street=state.street, player_id=player, type=kind, amount_to=amount), 5).after


def test_multiway_allin_sidepots_and_conservation():
    state = start({0:100, 1:200, 2:300})
    state = act(state, "p1", "raise", "100")
    state = act(state, "p2", "raise", "200")
    state = act(state, "p3", "call", "200")
    for player in ("p4", "p5", "p6", "hero", "p8", "p9"):
        state = act(state, player, "fold")
    assert state.complete
    assert state.pot == D("503")
    layers = pot_layers(state.contributed, state.folded)
    assert sum(amount for amount, _ in layers) == D("503")
    assert sum(amount for amount, eligible in layers if "p1" in eligible) == D("303")
    assert sum(amount for amount, eligible in layers if "p2" in eligible) == D("503")
    assert all("p8" not in eligible and "p9" not in eligible for _, eligible in layers)
    assert sum(state.remaining.values()) + state.pot == state.initial_chips


def test_short_allin_cannot_reopen_prior_caller():
    state = start({2:35})
    state = act(state, "p1", "raise", "25")
    state = act(state, "p2", "call", "25")
    state = act(state, "p3", "raise", "35")
    for player in ("p4", "p5", "p6", "hero", "p8", "p9"):
        state = act(state, player, "fold")
    with pytest.raises(ReplayError, match="not reopened"):
        act(state, "p1", "raise", "100")
    state = act(state, "p1", "call", "35")
    state = act(state, "p2", "call", "35")
    assert state.pending == ()


def test_cumulative_short_allins_reopen_after_full_increment():
    state = start({2:35, 3:48})
    for player, kind, amount in (("p1","raise","25"),("p2","call","25"),("p3","raise","35"),("p4","raise","48")):
        state = act(state, player, kind, amount)
    for player in ("p5", "p6", "hero", "p8", "p9"):
        state = act(state, player, "fold")
    state = act(state, "p1", "raise", "100")
    assert state.current_bet == D("100")
    assert state.pending == ("p2",)


def test_short_call_refunds_excess_and_reports_contestable_price():
    state = start({1:100})
    state = act(state, "p1", "raise", "650")
    metrics = decision_metrics(state, "p2")
    assert metrics.to_call == D("100")
    assert metrics.call_price == D("100") / D("203")
    state = act(state, "p2", "call", "100")
    for player in ("p3","p4","p5","p6","hero","p8","p9"):
        state = act(state, player, "fold")
    assert state.complete
    assert state.pot == D("203")
    assert state.remaining["p1"] == D("550")
    assert sum(state.remaining.values()) + state.pot == state.initial_chips


def test_allin_player_cannot_act_again():
    state = act(start(), "p1", "raise", "650")
    with pytest.raises(ReplayError, match="Out of turn"):
        act(state, "p1", "check")


def test_lone_caller_cannot_raise_against_only_allin_opponents():
    state = start({0:100})
    state = act(state, "p1", "raise", "100")
    for player in ("p2","p3","p4","p5","p6"):
        state = act(state, player, "fold")
    # Blinds still have chips, so Hero can raise now. Fold them out first in another setup.
    state = act(state, "hero", "fold")
    state = act(state, "p8", "fold")
    with pytest.raises(ReplayError, match="all opponents are all-in"):
        act(state, "p9", "raise", "200")


def test_short_bb_with_only_sb_left_matches_actual_wager():
    data = json.loads((Path(__file__).parents[1]/"examples/qq_large_open.json").read_text())
    data["players"][8]["starting_stack"] = "1.50"
    data["forced_bets"][1]["amount"] = "1.50"
    state = initial_state(PokerHand.model_validate(data))
    for player in ("p1","p2","p3","p4","p5","p6","hero"):
        state = act(state, player, "fold")
    assert state.current_bet == D("1.50")
    state = act(state,"p8","call","1.50")
    assert state.complete
    assert state.pot == D("3")


def test_checked_player_not_reopened_by_subminimum_allin_open():
    data = json.loads((Path(__file__).parents[1]/"examples/qq_large_open.json").read_text())
    data["players"][1]["starting_stack"] = "3"
    state = initial_state(PokerHand.model_validate(data))
    for player in ("p1","p2"):
        state = act(state,player,"call","2")
    for player in ("p3","p4","p5","p6","hero","p8"):
        state = act(state,player,"fold")
    state = act(state,"p9","check")
    state = apply_action(state,Action(street="flop",player_id="p9",type="check"),5).after
    state = act(state,"p1","check")
    state = act(state,"p2","bet","1")
    with pytest.raises(ReplayError,match="not reopened"):
        act(state,"p9","raise","3")
