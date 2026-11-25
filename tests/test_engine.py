import json
import subprocess
import sys
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path

import pytest

from poker_review.engine import (
    ReplayError, UnsupportedHandError, apply_action, decision_metrics,
    initial_state, replay_hand,
)
from poker_review.models import Action, PokerHand, Street


@pytest.fixture
def hand():
    path = Path(__file__).parents[1] / "examples/qq_large_open.json"
    return PokerHand.model_validate_json(path.read_text(encoding="utf-8"))


def act(player, kind, amount=None, street="preflop"):
    return Action(street=street, player_id=player, type=kind, amount_to=amount)


def test_qq_replay_and_decision_context(hand):
    steps = replay_hand(hand)
    flop_bet, hero_fold = steps[-2:]
    assert flop_bet.before.pot == D("253")
    assert flop_bet.before.remaining["hero"] == D("525")
    assert flop_bet.before.committed["hero"] == 0
    assert flop_bet.after.pot == D("553")
    metrics = decision_metrics(hero_fold.before, "hero")
    assert metrics.to_call == D("300")
    assert metrics.call_price == D("300") / D("853")
    assert metrics.street_start_spr == D("525") / D("253")
    assert hero_fold.refunded == D("300")
    assert hero_fold.after.pot == D("253")
    assert hero_fold.after.remaining["p1"] == D("525")
    assert hero_fold.after.remaining["hero"] == D("525")
    assert hero_fold.after.active == ("p1",)
    assert hero_fold.after.complete


def test_every_transition_preserves_chips_and_snapshots(hand):
    steps = replay_hand(hand)
    for step in steps:
        assert step.after.pot + sum(step.after.remaining.values()) == D("5850")
        assert all(stack >= 0 for stack in step.after.remaining.values())
    assert steps[0].before.pot == D("3")
    assert steps[0].before.remaining["p1"] == D("650")
    assert steps[0].after.remaining["p1"] == D("525")
    assert steps[-2].after.pot == D("553")  # Refund did not mutate history.


def test_bb_calls_only_the_difference_and_retains_option(hand):
    state = initial_state(hand)
    state = apply_action(state, act("p1", "raise", "25"), 3).after
    for player in ("p2", "p3", "p4", "p5", "p6", "hero", "p8"):
        state = apply_action(state, act(player, "fold"), 3).after
    step = apply_action(state, act("p9", "call", "25"), 3)
    assert step.added == D("23")
    assert step.after.pot == D("51")
    assert step.after.remaining["p9"] == D("625")
    assert not step.after.pending


def test_limped_pot_bb_gets_last_action(hand):
    state = initial_state(hand)
    state = apply_action(state, act("p1", "call", "2"), 3).after
    for player in ("p2", "p3", "p4", "p5", "p6", "hero", "p8"):
        state = apply_action(state, act(player, "fold"), 3).after
    assert state.pending == ("p9",)
    checked = apply_action(state, act("p9", "check"), 3).after
    assert checked.pot == D("5")
    assert not checked.pending


def test_full_raise_reopens_action_and_sets_min_raise(hand):
    state = initial_state(hand)
    state = apply_action(state, act("p1", "raise", "25"), 3).after
    state = apply_action(state, act("p2", "call", "25"), 3).after
    state = apply_action(state, act("p3", "raise", "80"), 3).after
    assert state.pending == ("p4", "p5", "p6", "hero", "p8", "p9", "p1", "p2")
    assert state.min_raise == D("55")
    with pytest.raises(ReplayError, match="minimum"):
        apply_action(state, act("p4", "raise", "100"), 3)
    assert state.remaining["p4"] == D("650")


def test_folding_to_open_returns_only_uncalled_amount(hand):
    state = initial_state(hand)
    state = apply_action(state, act("p1", "raise", "25"), 3).after
    for player in state.order[1:]:
        step = apply_action(state, act(player, "fold"), 3)
        state = step.after
    assert step.refunded == D("23")
    assert state.pot == D("5")  # Winner's matched $2 plus dead blinds $3.
    assert state.remaining["p1"] == D("648")


@pytest.mark.parametrize("action, message", [
    (act("p2", "fold"), "Out of turn"),
    (act("p1", "check"), "Cannot check"),
    (act("p1", "call", "3"), "Call amount_to"),
    (act("p1", "bet", "10"), "Use raise"),
    (act("p1", "raise", "3"), "minimum"),
    (act("p1", "raise", "651"), "exceeds remaining"),
    (act("p1", "bet", "10", "flop"), "before all players"),
])
def test_invalid_actions_leave_input_unchanged(hand, action, message):
    state = initial_state(hand)
    with pytest.raises(ReplayError, match=message):
        apply_action(state, action, 3)
    assert state.pot == D("3")
    assert state.pending[0] == "p1"
    assert state.remaining["p1"] == D("650")


def test_postflop_cannot_raise_unopened_pot_or_bet_too_small(hand):
    state = replay_hand(hand)[8].after
    with pytest.raises(ReplayError, match="Use bet"):
        apply_action(state, act("p1", "raise", "10", "flop"), 3)
    with pytest.raises(ReplayError, match="minimum"):
        apply_action(state, act("p1", "bet", "1", "flop"), 3)


def test_missing_board_and_skipped_streets_rejected(hand):
    state = replay_hand(hand)[8].after
    with pytest.raises(ReplayError, match="Missing board"):
        apply_action(state, act("p1", "check", street="flop"), 0)
    with pytest.raises(ReplayError, match="sequentially"):
        apply_action(state, act("p1", "check", street="turn"), 4)


def test_checked_through_streets_complete_at_river(hand):
    state = replay_hand(hand)[8].after
    for street in ("flop", "turn", "river"):
        state = apply_action(state, act("p1", "check", street=street), 5).after
        state = apply_action(state, act("hero", "check", street=street), 5).after
    assert state.street == Street.RIVER
    assert state.complete
    assert state.pot == D("253")
    with pytest.raises(ReplayError, match="hand has ended"):
        apply_action(state, act("p1", "check", street="river"), 5)


def test_no_actions_after_foldout_and_no_extra_action_after_closed_round(hand):
    final = replay_hand(hand)[-1].after
    with pytest.raises(ReplayError, match="hand has ended"):
        apply_action(final, act("p1", "check", street="flop"), 3)
    preflop_end = replay_hand(hand)[8].after
    with pytest.raises(ReplayError, match="Out of turn"):
        apply_action(preflop_end, act("p1", "check"), 3)


def test_short_all_in_blinds_do_not_enter_action_queue(hand):
    data = json.loads(hand.model_dump_json())
    data["players"][8]["starting_stack"] = "1.5"
    data["forced_bets"][1]["amount"] = "1.5"
    state = initial_state(PokerHand.model_validate(data))
    assert state.remaining["p9"] == 0
    assert "p9" not in state.pending
    assert state.current_bet == D("2")


def test_partial_replay_remains_incomplete(hand):
    state = replay_hand(hand)[0].after
    assert not state.complete
    assert state.pending[0] == "p2"
    with pytest.raises(ReplayError, match="next player"):
        decision_metrics(state, "hero")


def test_multiway_street_start_has_no_single_spr(hand):
    state = initial_state(hand)
    for player in ("p1", "p2"):
        state = apply_action(state, act(player, "call", "2"), 3).after
    for player in ("p3", "p4", "p5", "p6", "hero", "p8"):
        state = apply_action(state, act(player, "fold"), 3).after
    state = apply_action(state, act("p9", "check"), 3).after
    step = apply_action(state, act("p9", "check", street="flop"), 3)
    assert step.before.street_start_spr is None
    assert step.after.pending == ("p1", "p2")


def test_folded_player_cannot_act_again(hand):
    state = apply_action(initial_state(hand), act("p1", "fold"), 3).after
    with pytest.raises(ReplayError, match="Out of turn"):
        apply_action(state, act("p1", "call", "2"), 3)


def test_all_in_price_excludes_ineligible_unmatched_money(hand):
    state = replay_hand(hand)[-1].before
    state = replace(state, remaining={**state.remaining, "hero": D("100")})
    metrics = decision_metrics(state, "hero")
    assert metrics.to_call == D("100")
    assert metrics.call_price == D("100") / D("453")


def test_cli_replay_reports_decision_and_uncalled_refund():
    root = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "poker_review", "examples/qq_large_open.json", "--replay"],
        cwd=root, text=True, capture_output=True,
    )
    assert result.returncode == 0
    assert "to_call=300 call_price=35.17% street_start_spr=2.08" in result.stdout
    assert "pot=253 refunded=300" in result.stdout


def test_cli_short_hero_price_is_capped(hand, tmp_path):
    data = json.loads(hand.model_dump_json())
    data["players"][6]["starting_stack"] = "400"
    path = tmp_path / "short_hero.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "poker_review", str(path), "--replay"],
        text=True, capture_output=True,
    )
    assert result.returncode == 0
    assert "to_call=275 call_price=34.25%" in result.stdout
    assert "Traceback" not in result.stderr
