"""Scale pitcher talent for stack matchup math (0–100)."""


def pitcher_physics_0_100(pitcher_rep=None, physics_score=None, is_trap=False):
    """
    Stack engine expects opp_pitcher_physics on 0–100.
    UI physics_score is the weighted display slice (~45% of talent).
    """
    if pitcher_rep:
        physics_score = pitcher_rep.get("physics_score", 0) or 0
        is_trap = pitcher_rep.get("is_trap", False)
    raw = min(100.0, max(0.0, float(physics_score or 0) / 0.45))
    if is_trap:
        raw = min(raw, 65.0)
    return round(raw, 1)
