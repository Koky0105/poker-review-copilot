"""Lesson 1: input validation, independent of replay or LLM analysis."""

from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PositiveChips = Annotated[Decimal, Field(gt=0, allow_inf_nan=False, max_digits=14, decimal_places=2)]
Card = Annotated[str, Field(pattern=r"^[2-9TJQKA][cdhs]$")]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Position(str, Enum):
    UTG = "UTG"
    UTG1 = "UTG+1"
    UTG2 = "UTG+2"
    LJ = "LJ"
    HJ = "HJ"
    CO = "CO"
    BTN = "BTN"
    SB = "SB"
    BB = "BB"


class Street(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class ActionType(str, Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"


class Player(InputModel):
    player_id: str = Field(min_length=1, pattern=r"\S")
    seat: int = Field(ge=1, le=9, strict=True)
    position: Position
    starting_stack: PositiveChips
    is_hero: bool = False


class ForcedBet(InputModel):
    player_id: str
    type: Literal["small_blind", "big_blind"]
    amount: PositiveChips


class Action(InputModel):
    street: Street
    player_id: str
    type: ActionType
    # Total committed on this street after acting, not the incremental payment.
    amount_to: PositiveChips | None = None

    @model_validator(mode="after")
    def validate_amount(self) -> "Action":
        moves_chips = self.type in {
            ActionType.CALL, ActionType.BET, ActionType.RAISE
        }
        if moves_chips and self.amount_to is None:
            raise ValueError(f"{self.type.value} requires amount_to")
        if not moves_chips and self.amount_to is not None:
            raise ValueError(f"{self.type.value} cannot have amount_to")
        return self


class PokerHand(InputModel):
    schema_version: Literal[1] = 1
    hand_id: str = Field(min_length=1)
    game: Literal["NLH_CASH"] = "NLH_CASH"
    max_players: Literal[9] = 9
    small_blind: PositiveChips
    big_blind: PositiveChips
    players: list[Player] = Field(min_length=9, max_length=9)
    forced_bets: list[ForcedBet] = Field(min_length=2, max_length=2)
    hero_cards: tuple[Card, Card]
    board: list[Card] = Field(default_factory=list, max_length=5)
    actions: list[Action] = Field(max_length=300)

    @model_validator(mode="after")
    def validate_hand(self) -> "PokerHand":
        if self.small_blind >= self.big_blind:
            raise ValueError("small_blind must be less than big_blind")

        for attribute in ("player_id", "seat", "position"):
            values = [getattr(player, attribute) for player in self.players]
            if len(values) != len(set(values)):
                raise ValueError(f"{attribute} must be unique")

        if sum(player.is_hero for player in self.players) != 1:
            raise ValueError("hand must contain exactly one hero")

        players = {player.player_id: player for player in self.players}
        for event in [*self.forced_bets, *self.actions]:
            if event.player_id not in players:
                raise ValueError(f"unknown player: {event.player_id}")

        blind_types = {bet.type for bet in self.forced_bets}
        if blind_types != {"small_blind", "big_blind"}:
            raise ValueError("exactly one small blind and one big blind required")

        for bet in self.forced_bets:
            expected_position, blind = (
                (Position.SB, self.small_blind)
                if bet.type == "small_blind"
                else (Position.BB, self.big_blind)
            )
            player = players[bet.player_id]
            if player.position != expected_position:
                raise ValueError(f"{bet.type} must be posted by {expected_position.value}")
            if bet.amount != min(blind, player.starting_stack):
                raise ValueError("blind amount must match the blind or remaining stack")

        if len(self.board) not in {0, 3, 4, 5}:
            raise ValueError("board must contain 0, 3, 4, or 5 cards")
        cards = [*self.hero_cards, *self.board]
        if len(cards) != len(set(cards)):
            raise ValueError("duplicate cards detected")
        return self
