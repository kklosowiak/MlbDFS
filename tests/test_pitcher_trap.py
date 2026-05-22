"""Sticky TRAP when prop odds drop from the feed."""
from utils.pitcher_trap import resolve_pitcher_trap


def test_myers_style_refresh_keeps_trap_when_k_odds_vanish():
    """Export (8)->(9): k_odds 146 -> None should not clear Vulnerable TRAP."""
    prev = {
        "is_trap": True,
        "trap_type": "Vulnerable",
        "k_odds": 146,
        "k_line": 2.5,
        "is_death_sentence": False,
    }
    res = resolve_pitcher_trap(
        prev_pitcher=prev,
        ml_move=25,
        k_move=0,
        k_line=4.5,
        k_odds=None,
        outs_line=14.5,
        outs_odds=None,
    )
    assert res["is_trap"] is True
    assert res["trap_type"] == "Vulnerable"
    assert res["props_feed_status"] in ("partial", "held")
    assert res.get("trap_prop_note")


def test_clears_trap_when_k_odds_repriced():
    prev = {
        "is_trap": True,
        "trap_type": "Vulnerable",
        "k_odds": 146,
        "is_death_sentence": False,
    }
    res = resolve_pitcher_trap(
        prev_pitcher=prev,
        ml_move=25,
        k_move=0,
        k_line=4.5,
        k_odds=-110,
        outs_line=14.5,
        outs_odds=None,
    )
    assert res["is_trap"] is False
    assert res["props_feed_status"] == "repriced"


def test_fresh_trap_on_juiced_k():
    res = resolve_pitcher_trap(
        prev_pitcher=None,
        ml_move=0,
        k_move=0,
        k_line=4.5,
        k_odds=146,
        outs_line=14.5,
        outs_odds=None,
    )
    assert res["is_trap"] is True
    assert res["trap_type"] == "Vulnerable"
