"""Fuzzy team name matching across Odds API, MLB API, and statcast cache."""


def teams_match(cache_team, query_team):
    """True when cache row team corresponds to slate/API team name."""
    if not cache_team or not query_team:
        return False
    if cache_team == query_team:
        return True
    c = str(cache_team).lower().strip()
    q = str(query_team).lower().strip()
    if c == q or c in q or q in c:
        return True
    # Last-token nickname match (e.g. Dodgers == Los Angeles Dodgers)
    c_tail = c.split()[-1] if c else ""
    q_tail = q.split()[-1] if q else ""
    if c_tail and q_tail and c_tail == q_tail and len(c_tail) > 3:
        return True
    return False
