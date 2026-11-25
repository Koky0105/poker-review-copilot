"""Run with: python -m poker_review examples/qq_large_open.json."""

import argparse
from pathlib import Path

from pydantic import ValidationError

from poker_review.engine import ReplayError, decision_metrics, initial_state, replay_hand
from poker_review.models import PokerHand


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a 9-max hand history")
    parser.add_argument("hand_file", type=Path)
    parser.add_argument("--replay", action="store_true", help="Replay bets and print Hero decisions")
    args = parser.parse_args()
    try:
        hand = PokerHand.model_validate_json(args.hand_file.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        parser.exit(1, f"Hand validation failed:\n{error}\n")

    if args.replay:
        try:
            transitions = replay_hand(hand)
        except ReplayError as error:
            parser.exit(1, f"Replay failed:\n{error}\n")
        hero = next(player.player_id for player in hand.players if player.is_hero)
        print(f"Replay: {hand.hand_id} (no rake; pot held before payout)")
        for index, step in enumerate(transitions, 1):
            action = step.action
            print(
                f"{index:02} {action.street.value} {action.player_id} {action.type.value} "
                f"| added={step.added} pot={step.after.pot} refunded={step.refunded}"
            )
            if action.player_id == hero:
                try:
                    metrics = decision_metrics(step.before, hero)
                except ReplayError as error:
                    parser.exit(1, f"Decision metrics unavailable:\n{error}\n")
                price = f"{metrics.call_price:.2%}" if metrics.call_price is not None else "n/a"
                spr = f"{metrics.street_start_spr:.2f}" if metrics.street_start_spr is not None else "n/a"
                print(
                    f"   Hero BEFORE action: pot={metrics.pot} stack={metrics.stack} "
                    f"to_call={metrics.to_call} call_price={price} street_start_spr={spr}"
                )
        state = transitions[-1].after if transitions else initial_state(hand)
        print(f"Betting complete: {state.complete} | Unawarded pot: {state.pot}")
        return

    print(f"Valid hand: {hand.hand_id}")
    print(f"Players: {len(hand.players)} | Actions: {len(hand.actions)}")
    print(hand.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
