import json

def extract_totals():
    # Load latest results
    with open('reports/latest_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Also load the snapshot for consensus over/under splits
    import glob, os
    snapshots = sorted(glob.glob('data/snapshot_*.json'), key=os.path.getmtime, reverse=True)
    consensus_data = {}
    if snapshots:
        with open(snapshots[0], 'r', encoding='utf-8') as f:
            snap = json.load(f)
        # Try to extract over/under consensus by event_id or team
        for game in snap.get('games', []) + snap.get('matchups', []):
            home = game.get('home_team', game.get('home', ''))
            away = game.get('away_team', game.get('away', ''))
            over_pct = game.get('over_pct', game.get('ou_over_pct', None))
            under_pct = game.get('under_pct', game.get('ou_under_pct', None))
            line = game.get('total', game.get('ou_line', None))
            line_move = game.get('total_move', game.get('ou_move', 0))
            if home and away:
                consensus_data[frozenset([home, away])] = {
                    'over_pct': over_pct, 'under_pct': under_pct,
                    'line': line, 'line_move': line_move
                }

    teams = data.get('teams', [])
    games = {}
    for team in teams:
        matchup_key = frozenset([team['team'], team['opponent']])
        if matchup_key not in games:
            games[matchup_key] = []
        games[matchup_key].append(team)

    print("\n=== SHARP TOTALS DIVERGENCE (Early 8-Game Slate) ===\n")
    print(f"{'Game':<40} {'TT Move':<12} {'Consensus':<25} {'Sharp Lean'}")
    print("-" * 95)

    for match_key, game_teams in sorted(games.items(), key=lambda x: abs(sum(t.get('tt_move',0) for t in x[1])), reverse=True):
        teams_list = list(match_key)
        label = f"{teams_list[0]} vs {teams_list[1]}"
        game_tt_move = sum(t.get('tt_move', 0) for t in game_teams)

        con = consensus_data.get(match_key, {})
        over_pct = con.get('over_pct')
        under_pct = con.get('under_pct')
        line = con.get('line', '?')
        line_move = con.get('line_move', 0)

        if over_pct and under_pct:
            consensus_str = f"O:{over_pct}% / U:{under_pct}%"
        elif over_pct:
            consensus_str = f"O:{over_pct}% bets"
        else:
            consensus_str = "No split data"

        if game_tt_move > 0.4:
            lean = ">>> SHARP OVER"
        elif game_tt_move < -0.4:
            lean = "<<< SHARP UNDER"
        else:
            lean = "    NEUTRAL"

        print(f"{label:<40} {game_tt_move:+.1f} runs   {consensus_str:<25} {lean}")

        for t in game_teams:
            move = t.get('tt_move', 0)
            div = t.get('divergence', 0)
            arrow = "UP" if move > 0 else "DN" if move < 0 else "--"
            ml_move = t.get('ml_move', 0)
            print(f"  {t['team']:<38} TT:{move:+.1f} ({arrow})  ML:{ml_move:+.0f}  Div:{div:+d}")

    print("\nKey: TT Move = Team Total line movement. Negative = UNDER pressure. Positive = OVER pressure.")
    print("Div = ML betting divergence (sharp $ vs public %). ML = moneyline move in cents.")

if __name__ == "__main__":
    extract_totals()
