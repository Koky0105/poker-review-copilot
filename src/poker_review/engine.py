"""Lesson 2: replay standard-blind cash hands without all-ins or rake.

Transitions return new states so prior decision contexts remain available.
All-in actions are rejected until side pots and raise-reopening are supported.
The pot is held for review; payouts and showdown evaluation are not performed.
"""

from dataclasses import dataclass, replace
from decimal import Decimal

from poker_review.models import Action, ActionType, PokerHand, Position, Street

ZERO = Decimal("0")
STREETS = tuple(Street)
PREFLOP_ORDER = tuple(Position)


class ReplayError(ValueError):
    """The event conflicts with the reconstructed betting state."""


class UnsupportedHandError(ReplayError):
    """The hand needs rules intentionally deferred to a later lesson."""


@dataclass(frozen=True)
class PokerState:
    street: Street
    pot: Decimal
    remaining: dict[str, Decimal]
    committed: dict[str, Decimal]
    folded: frozenset[str]
    pending: tuple[str, ...]
    current_bet: Decimal
    min_raise: Decimal
    order: tuple[str, ...]
    big_blind: Decimal
    initial_chips: Decimal
    street_start_spr: Decimal | None = None

    @property
    def active(self) -> tuple[str, ...]:
        return tuple(player for player in self.order if player not in self.folded)

    @property
    def complete(self) -> bool:
        return len(self.active) == 1 or (self.street == Street.RIVER and not self.pending)


@dataclass(frozen=True)
class Transition:
    action: Action
    before: PokerState
    after: PokerState
    added: Decimal
    refunded: Decimal


@dataclass(frozen=True)
class DecisionMetrics:
    pot: Decimal
    stack: Decimal
    to_call: Decimal
    call_price: Decimal | None
    street_start_spr: Decimal | None


def initial_state(hand: PokerHand) -> PokerState:
    by_position = {player.position: player.player_id for player in hand.players}
    order = tuple(by_position[position] for position in PREFLOP_ORDER)
    remaining = {player.player_id: player.starting_stack for player in hand.players}
    committed = dict.fromkeys(order, ZERO)
    pot = ZERO
    for blind in hand.forced_bets:
        if blind.amount >= remaining[blind.player_id]:
            raise UnsupportedHandError("All-in blinds are not supported in Lesson 2")
        remaining[blind.player_id] -= blind.amount
        committed[blind.player_id] = blind.amount
        pot += blind.amount
    return PokerState(
        street=Street.PREFLOP, pot=pot, remaining=remaining, committed=committed,
        folded=frozenset(), pending=order, current_bet=hand.big_blind,
        min_raise=hand.big_blind, order=order, big_blind=hand.big_blind,
        initial_chips=sum(remaining.values(), pot),
    )


def _advance_street(state: PokerState, street: Street, board_size: int) -> PokerState:
    if street == state.street:
        return state
    if state.pending:
        raise ReplayError("Cannot advance street before all players have responded")
    if STREETS.index(street) != STREETS.index(state.street) + 1:
        raise ReplayError("Streets must advance sequentially")
    required_cards = {Street.FLOP: 3, Street.TURN: 4, Street.RIVER: 5}[street]
    if board_size < required_cards:
        raise ReplayError(f"Missing board cards for {street.value}")
    # Rotate UTG..BB to SB, BB, UTG..BTN, excluding folded players.
    order = state.order[-2:] + state.order[:-2]
    pending = tuple(player for player in order if player not in state.folded)
    spr = (
        min(state.remaining[player] for player in pending) / state.pot
        if len(pending) == 2 else None
    )
    return replace(
        state, street=street, committed=dict.fromkeys(state.order, ZERO),
        pending=pending, current_bet=ZERO, min_raise=state.big_blind,
        street_start_spr=spr,
    )


def decision_metrics(state: PokerState, player_id: str) -> DecisionMetrics:
    if not state.pending or state.pending[0] != player_id:
        raise ReplayError("Decision metrics require the next player to act")
    to_call = state.current_bet - state.committed[player_id]
    if to_call >= state.remaining[player_id]:
        raise UnsupportedHandError("All-in calls need side-pot support")
    return DecisionMetrics(
        pot=state.pot, stack=state.remaining[player_id], to_call=to_call,
        call_price=to_call / (state.pot + to_call) if to_call else None,
        street_start_spr=state.street_start_spr,
    )


def apply_action(state: PokerState, action: Action, board_size: int) -> Transition:
    if state.complete:
        raise ReplayError("Cannot act after the hand has ended")
    before = _advance_street(state, action.street, board_size)
    if not before.pending or action.player_id != before.pending[0]:
        expected = before.pending[0] if before.pending else "next street"
        raise ReplayError(f"Out of turn: expected {expected}")

    player = action.player_id
    to_call = before.current_bet - before.committed[player]
    added = ZERO
    folded = before.folded
    pending = before.pending[1:]
    current_bet, min_raise = before.current_bet, before.min_raise

    if action.type == ActionType.FOLD:
        folded = folded | {player}
    elif action.type == ActionType.CHECK:
        if to_call:
            raise ReplayError("Cannot check while facing a bet")
    else:
        # Pydantic guarantees this for validated Action instances.
        assert action.amount_to is not None
        added = action.amount_to - before.committed[player]
        if added <= ZERO:
            raise ReplayError("Chip actions must add chips")
        if added > before.remaining[player]:
            raise ReplayError("Action exceeds remaining stack")
        if added == before.remaining[player]:
            raise UnsupportedHandError("All-in actions are not supported in Lesson 2")

        if action.type == ActionType.CALL:
            if to_call == ZERO or action.amount_to != before.current_bet:
                raise ReplayError("Call amount_to must match the current bet")
        else:
            if action.type == ActionType.BET and before.current_bet != ZERO:
                raise ReplayError("Use raise when a bet already exists")
            if action.type == ActionType.RAISE and before.current_bet == ZERO:
                raise ReplayError("Use bet when no bet exists")
            increment = action.amount_to - before.current_bet
            if increment < before.min_raise:
                raise ReplayError("Bet or raise is smaller than the minimum")
            current_bet, min_raise = action.amount_to, increment
            # A full raise requires every other live player to respond again.
            index = before.order.index(player)
            rotated = before.order[index + 1:] + before.order[:index]
            pending = tuple(other for other in rotated if other not in folded)

    remaining, committed = dict(before.remaining), dict(before.committed)
    remaining[player] -= added
    committed[player] += added
    pot, refunded = before.pot + added, ZERO
    if len(before.order) - len(folded) == 1:
        pending = ()
        # Only the unmatched portion comes back; dead money stays in the pot.
        ranked = sorted(committed, key=committed.get, reverse=True)
        refunded = committed[ranked[0]] - committed[ranked[1]]
        remaining[ranked[0]] += refunded
        committed[ranked[0]] -= refunded
        pot -= refunded

    after = replace(
        before, pot=pot, remaining=remaining, committed=committed,
        folded=frozenset(folded), pending=pending, current_bet=current_bet,
        min_raise=min_raise,
    )
    if after.pot + sum(after.remaining.values(), ZERO) != after.initial_chips:
        raise ReplayError("Chip conservation violated")
    return Transition(action, before, after, added, refunded)


def replay_hand(hand: PokerHand) -> list[Transition]:
    state = initial_state(hand)
    transitions = []
    for index, action in enumerate(hand.actions, 1):
        try:
            transition = apply_action(state, action, len(hand.board))
        except ReplayError as error:
            raise type(error)(f"Action {index}: {error}") from error
        transitions.append(transition)
        state = transition.after
    return transitions
