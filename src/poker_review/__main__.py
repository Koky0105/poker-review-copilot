"""Run with: python -m poker_review examples/qq_large_open.json."""

import argparse
from pathlib import Path

from pydantic import ValidationError

from poker_review.models import PokerHand


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a 9-max hand history")
    parser.add_argument("hand_file", type=Path)
    args = parser.parse_args()
    try:
        hand = PokerHand.model_validate_json(args.hand_file.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        parser.exit(1, f"Hand validation failed:\n{error}\n")

    print(f"Valid hand: {hand.hand_id}")
    print(f"Players: {len(hand.players)} | Actions: {len(hand.actions)}")
    print(hand.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
