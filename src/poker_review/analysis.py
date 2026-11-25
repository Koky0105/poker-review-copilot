"""Decision facts are computed before the action, without future cards."""

from decimal import Decimal

from poker_review.engine import decision_metrics, initial_state, pot_layers, replay_hand
from poker_review.models import PokerHand, Street


def analyze(hand: PokerHand) -> dict:
    steps = replay_hand(hand)
    hero = next(p for p in hand.players if p.is_hero)
    timeline, decisions = [], []
    for index, step in enumerate(steps):
        before, after, action = step.before, step.after, step.action
        visible = {Street.PREFLOP: 0, Street.FLOP: 3, Street.TURN: 4, Street.RIVER: 5}[action.street]
        timeline.append({
            "index": index, "street": action.street.value, "player": action.player_id,
            "action": action.type.value, "amount_to": action.amount_to,
            "added": step.added, "refunded": step.refunded, "pot_before": before.pot,
            "pot": after.pot, "remaining": after.remaining, "folded": sorted(after.folded),
            "board": list(hand.board[:visible]), "pending": after.pending,
        })
        if action.player_id != hero.player_id:
            continue
        metrics = decision_metrics(before, hero.player_id)
        active = before.active
        opponents = [p for p in active if p != hero.player_id]
        effective = min(before.remaining[hero.player_id], max((before.remaining[p] for p in opponents), default=Decimal(0)))
        premium = hero_cards_class(hand.hero_cards) == "premium_pair"
        raises_before = sum(s.action.street == Street.PREFLOP and s.action.type.value == "raise" for s in steps[:index])
        large_open = action.street == Street.PREFLOP and raises_before == 1 and before.current_bet >= hand.big_blind * 10
        postflop = action.street != Street.PREFLOP and metrics.to_call > 0
        # Categories describe opportunities. They do not claim optimal strategy.
        contexts = []
        if premium and large_open:
            contexts.append("premium_large_open")
        if postflop and metrics.street_start_spr is not None and metrics.street_start_spr <= 3:
            contexts.append("low_spr_facing_bet")
        aggressor = next((s for s in reversed(steps[:index]) if s.action.street == action.street and s.action.type.value in {"bet", "raise"}), None)
        if postflop and aggressor and aggressor.action.type.value == "bet" and aggressor.added >= aggressor.before.pot:
            contexts.append("facing_large_bet")
        decisions.append({
            "index": index, "street": action.street.value, "position": hero.position.value,
            "action": action.type.value, "cards": list(hand.hero_cards),
            "board": list(hand.board[:visible]), "pot": metrics.pot,
            "stack": metrics.stack, "to_call": metrics.to_call,
            "call_price": metrics.call_price, "street_start_spr": metrics.street_start_spr,
            "effective_remaining_bb": effective / hand.big_blind,
            "active_players": len(active), "contexts": contexts,
            "preflop_raises_before": raises_before,
        })
    state = steps[-1].after if steps else initial_state(hand)
    return {
        "hand_id": hand.hand_id, "hero_id": hero.player_id, "hero_position": hero.position.value,
        "hero_cards": list(hand.hero_cards), "hand_class": hero_cards_class(hand.hero_cards),
        "timeline": timeline, "decisions": decisions, "pot": state.pot,
        "depth_bucket": depth_bucket(decisions[0]["effective_remaining_bb"]) if decisions else "unknown",
        "pot_type": ("unopened" if decisions[0]["preflop_raises_before"] == 0 else "single_raise" if decisions[0]["preflop_raises_before"] == 1 else "three_bet_plus") if decisions else "unknown",
        "remaining": state.remaining, "complete": state.complete,
        "next_player": state.pending[0] if state.pending else None,
        "pots": [{"amount": amount, "eligible": eligible} for amount, eligible in pot_layers(state.contributed, state.folded)],
        "assumptions": ["未計 rake、ante、straddle；底池保留於派彩前。", "跟注價格不等於實際 equity，也不直接代表最佳動作。"],
    }


def depth_bucket(bb):
    return "short" if bb < 50 else "standard" if bb < 150 else "deep" if bb < 300 else "very_deep"


def hero_cards_class(cards) -> str:
    if cards[0][0] == cards[1][0]:
        return "premium_pair" if cards[0][0] in "AKQ" else "pair"
    return "suited" if cards[0][1] == cards[1][1] else "offsuit"


CONTEXTS = {
    "premium_large_open": ("強口袋對面對超大 open", "call", "檢查翻前是否比較過跟注、加注與棄牌的計畫；尺寸本身不能決定最佳動作。"),
    "low_spr_facing_bet": ("低 SPR 面對翻牌後下注", "fold", "檢查翻前計畫與翻牌後範圍；低 SPR 也可能合理棄牌。"),
    "facing_large_bet": ("面對至少一個原底池的下注", "call", "逐手檢查價值／詐唬範圍和跟注價格，避免只看結果。"),
}


def aggregate_patterns(hands: list[dict]) -> dict:
    personal = [h for h in hands if not h["is_demo"]]
    patterns = []
    for key, (title, target, suggestion) in CONTEXTS.items():
        opportunities = [(h, d) for h in personal for d in h["report"]["decisions"] if key in d["contexts"]]
        matches = [(h, d) for h, d in opportunities if d["action"] == target]
        patterns.append({
            "id": key, "title": title, "target_action": target,
            "opportunities": len(opportunities), "matches": len(matches),
            "rate": len(matches) / len(opportunities) if opportunities else None,
            "status": "repeated_pattern" if len(matches) >= 3 else "insufficient_evidence",
            "suggestion": suggestion,
            "evidence": [{"hand_id": h["id"], "decision_index": d["index"]} for h, d in matches[:10]],
        })
    return {"hands": len(personal), "demo_hands": len(hands) - len(personal),
            "decisions": sum(len(h["report"]["decisions"]) for h in personal), "patterns": patterns,
            "limitation": "僅反映你選擇記錄的牌局。三次為介面顯示門檻，並非統計信心或已證實的策略漏洞。"}
