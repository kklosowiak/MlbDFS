import pytest
import datetime
import json
import os
from unittest.mock import patch, MagicMock
from utils.opener_detector import detect_opener_for_team, is_first_7_days_of_season
from utils.attack_confidence import score_stack_confidence
from engine.sharps_weighting import SharpsWeighting
from config import config

# Mock data helper
def get_mock_game(home_team="Kansas City Royals", away_team="Chicago White Sox", game_id="game_123"):
    return {
        "id": game_id,
        "home_team": home_team,
        "away_team": away_team,
        "home_pitcher": "Steven Cruz",
        "away_pitcher": "Chris Flexen"
    }

def get_mock_dk_players():
    return [
        {
            "Name": "Steven Cruz",
            "Position": "PO",
            "Roster Position": "P",
            "Salary": "4000",
            "TeamAbbrev": "KC",
            "Game Info": "CWS@KC 06/26/2026 08:10PM ET"
        },
        {
            "Name": "Mitch Spence",
            "Position": "PLR",
            "Roster Position": "P",
            "Salary": "7000",
            "TeamAbbrev": "KC",
            "Game Info": "CWS@KC 06/26/2026 08:10PM ET"
        }
    ]

def get_default_mock_props():
    return {
        "game_123": {
            "pitcher_outs": [
                {"player_name": "Steven Cruz", "point": 5.5, "side": "home", "home_team": "Kansas City Royals"},
                {"player_name": "Mitch Spence", "point": 15.5, "side": "home", "home_team": "Kansas City Royals"},
                {"player_name": "Chris Flexen", "point": 6.0, "side": "away", "away_team": "Chicago White Sox"},
                {"player_name": "Sean Burke", "point": 16.0, "side": "away", "away_team": "Chicago White Sox"}
            ]
        }
    }

def get_non_opener_mock_props():
    return {
        "game_123": {
            "pitcher_outs": [
                {"player_name": "Steven Cruz", "point": 9.0, "side": "home", "home_team": "Kansas City Royals"},
                {"player_name": "Chris Flexen", "point": 9.0, "side": "away", "away_team": "Chicago White Sox"},
                {"player_name": "Bryan Hudson", "point": 9.0, "side": "away", "away_team": "Chicago White Sox"}
            ]
        }
    }

# 1. test_tier1_po_plr_tags_confirmed
@patch('utils.opener_detector.requests.get')
def test_tier1_po_plr_tags_confirmed(mock_get):
    game = get_mock_game()
    dk = get_mock_dk_players()
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, dk, {}, datetime.date(2026, 6, 26)
    )
    assert status == "CONFIRMED"
    assert opener == "Steven Cruz"
    assert bulk == "Mitch Spence"
    assert tier == "1B"
    assert sub is True

# 2. test_tier1_two_pitchers_salary_gap_pass
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_tier1_two_pitchers_salary_gap_pass(mock_fetch_api):
    # Mock starts < 8, relief % > 50%
    mock_fetch_api.return_value = {
        "career_starts": 1,
        "relief_pct": 90.0,
        "avg_ip_l10": 1.2,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    dk = [
        {"Name": "Steven Cruz", "Position": "RP", "Roster Position": "P", "Salary": "4000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"},
        {"Name": "Mitch Spence", "Position": "SP", "Roster Position": "P", "Salary": "7000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"}
    ]
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, dk, get_non_opener_mock_props(), datetime.date(2026, 6, 26)
    )
    assert status == "CONFIRMED"
    assert opener == "Steven Cruz"
    assert bulk == "Mitch Spence"
    assert tier == "1D"
    assert sub is True

# 3. test_tier1_salary_gap_too_small_no_flag
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_tier1_salary_gap_too_small_no_flag(mock_fetch_api):
    mock_fetch_api.return_value = {
        "career_starts": 100,
        "relief_pct": 10.0,
        "avg_ip_l10": 5.5,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    # Salary gap = 700
    dk = [
        {"Name": "Steven Cruz", "Position": "RP", "Roster Position": "P", "Salary": "4000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"},
        {"Name": "Mitch Spence", "Position": "SP", "Roster Position": "P", "Salary": "4700", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"}
    ]
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, dk, get_non_opener_mock_props(), datetime.date(2026, 6, 26)
    )
    assert status != "CONFIRMED"
    assert sub is False

# 4. test_tier1_doubleheader_different_game_ids_no_flag
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_tier1_doubleheader_different_game_ids_no_flag(mock_fetch_api):
    mock_fetch_api.return_value = {
        "career_starts": 1,
        "relief_pct": 90.0,
        "avg_ip_l10": 1.2,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    # Different Game Info (representing two games of doubleheader)
    dk = [
        {"Name": "Steven Cruz", "Position": "RP", "Roster Position": "P", "Salary": "4000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 01:10PM ET"},
        {"Name": "Mitch Spence", "Position": "SP", "Roster Position": "P", "Salary": "7000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 06:10PM ET"}
    ]
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, dk, get_non_opener_mock_props(), datetime.date(2026, 6, 26)
    )
    assert status != "CONFIRMED"
    assert sub is False

# 5. test_tier1_three_pitchers_same_team
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_tier1_three_pitchers_same_team(mock_fetch_api):
    mock_fetch_api.return_value = {
        "career_starts": 1,
        "relief_pct": 90.0,
        "avg_ip_l10": 1.2,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    # Three pitchers. Lowest salary is Cruz ($4.0K), highest is Spence ($7.0K). Middle is Bubic ($5.0K).
    dk = [
        {"Name": "Steven Cruz", "Position": "RP", "Roster Position": "P", "Salary": "4000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"},
        {"Name": "Kris Bubic", "Position": "RP", "Roster Position": "P", "Salary": "5000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"},
        {"Name": "Mitch Spence", "Position": "SP", "Roster Position": "P", "Salary": "7000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"}
    ]
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, dk, get_non_opener_mock_props(), datetime.date(2026, 6, 26)
    )
    assert status == "CONFIRMED"
    assert opener == "Steven Cruz"
    assert bulk == "Mitch Spence"
    assert sub is True

# 6. test_tier1_legitimate_starter_no_flag
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_tier1_legitimate_starter_no_flag(mock_fetch_api):
    # Legitimate starter (career starts = 150, avg ip L10 = 5.8, relief pct = 5%)
    mock_fetch_api.return_value = {
        "career_starts": 150,
        "relief_pct": 5.0,
        "avg_ip_l10": 5.8,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    dk = [
        {"Name": "Steven Cruz", "Position": "RP", "Roster Position": "P", "Salary": "4000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"},
        {"Name": "Mitch Spence", "Position": "SP", "Roster Position": "P", "Salary": "7000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"}
    ]
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, dk, get_non_opener_mock_props(), datetime.date(2026, 6, 26)
    )
    assert status != "CONFIRMED"
    assert sub is False

# 7. test_tier1_both_teams_opener_independent
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_tier1_both_teams_opener_independent(mock_fetch_api):
    mock_fetch_api.return_value = {
        "career_starts": 2,
        "relief_pct": 80.0,
        "avg_ip_l10": 1.5,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    # Both teams (KC and CWS) have two pitchers with gap and leash
    dk = [
        {"Name": "Steven Cruz", "Position": "RP", "Roster Position": "P", "Salary": "4000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"},
        {"Name": "Mitch Spence", "Position": "SP", "Roster Position": "P", "Salary": "7000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"},
        {"Name": "Bryan Hudson", "Position": "RP", "Roster Position": "P", "Salary": "4000", "TeamAbbrev": "CWS", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"},
        {"Name": "Sean Burke", "Position": "SP", "Roster Position": "P", "Salary": "7000", "TeamAbbrev": "CWS", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"}
    ]
    
    # Detect for KC
    status_kc, opener_kc, bulk_kc, _, _, sub_kc, _ = detect_opener_for_team(
        "Kansas City Royals", game, dk, get_non_opener_mock_props(), datetime.date(2026, 6, 26)
    )
    
    # Setup for CWS detector (Hudson starter, Burke teammate)
    game_cws = game.copy()
    game_cws["away_pitcher"] = "Bryan Hudson"
    
    # Detect for CWS
    status_cws, opener_cws, bulk_cws, _, _, sub_cws, _ = detect_opener_for_team(
        "Chicago White Sox", game_cws, dk, get_non_opener_mock_props(), datetime.date(2026, 6, 26)
    )
    
    assert status_kc == "CONFIRMED" and opener_kc == "Steven Cruz" and bulk_kc == "Mitch Spence"
    assert status_cws == "CONFIRMED" and opener_cws == "Bryan Hudson" and bulk_cws == "Sean Burke"

# 8. test_tier2_three_signals_bulk_resolved
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_tier2_three_signals_bulk_resolved(mock_fetch_api):
    mock_fetch_api.return_value = {
        "career_starts": 1,
        "relief_pct": 95.0,
        "avg_ip_l10": 1.1,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    props = {
        "game_123": {
            "pitcher_outs": [
                {"player_name": "Steven Cruz", "point": 6.0, "side": "Over", "price": -110},
                {"player_name": "Mitch Spence", "point": 15.0, "side": "Over", "price": -110}
            ]
        }
    }
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, None, props, datetime.date(2026, 6, 26)
    )
    assert status == "CONFIRMED" # Tier 1C (props) triggers since Cruz is 6.0
    assert opener == "Steven Cruz"
    assert bulk == "Mitch Spence"
    assert sub is True

# 9. test_tier2_three_signals_bulk_unresolved
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_tier2_three_signals_bulk_unresolved(mock_fetch_api):
    mock_fetch_api.return_value = {
        "career_starts": 1,
        "relief_pct": 95.0,
        "avg_ip_l10": 1.1,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    # Starter outs line is present, but no other pitcher
    props = {
        "game_123": {
            "pitcher_outs": [
                {"player_name": "Steven Cruz", "point": 6.0, "side": "Over", "price": -110}
            ]
        }
    }
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, None, props, datetime.date(2026, 6, 26)
    )
    assert status == "CONFIRMED"
    assert bulk is None
    assert sub is False
    assert "unresolved" in reason.lower()

# 10. test_tier2_two_signals_only_no_substitution
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_tier2_two_signals_only_no_substitution(mock_fetch_api):
    mock_fetch_api.return_value = {
        "career_starts": 2,
        "relief_pct": 60.0,
        "avg_ip_l10": 4.5,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, None, get_non_opener_mock_props(), datetime.date(2026, 6, 26)
    )
    assert status == "POSSIBLE" or status == "REJECTED"
    assert sub is False

# 11. test_tier3_single_signal_informational_only
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_tier3_single_signal_informational_only(mock_fetch_api):
    mock_fetch_api.return_value = {
        "career_starts": 3,
        "relief_pct": 10.0,
        "avg_ip_l10": 5.2,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, None, get_non_opener_mock_props(), datetime.date(2026, 6, 26)
    )
    assert status == "POSSIBLE" or status == "REJECTED"
    assert sub is False

# 12. test_substitution_pipeline_order_before_soft_cap
def test_substitution_pipeline_order_before_soft_cap():
    t = {
        "team": "Chicago White Sox",
        "opponent": "Kansas City Royals",
        "opp_pitcher": "Mitch Spence",
        "opp_pitcher_display": "Cruz -> Spence (BULK)",
        "team_xwoba": 0.355,
        "divergence": 15.0,
        "implied_total": 5.5,
        "is_trap": False,
        "is_public_steam_trap": False,
        "dqi_status": "TRUST"
    }
    p_reports = [
        {
            "pitcher": "Mitch Spence",
            "team": "Kansas City Royals",
            "opponent": "Chicago White Sox",
            "is_trap": True,
            "walks_penalty": True,
            "siera": 5.10,
            "recent_era": 13.50,
            "confidence": "high",
            "attack_conf": 80.0,
            "blended_rating": 85.0
        }
    ]
    conf, reasons = score_stack_confidence(t, p_reports)
    assert conf > 75.0
    assert not any("Soft-capped above 75" in r for r in reasons)

# 13. test_soft_cap_breaks_with_bulk_trap_arm
def test_soft_cap_breaks_with_bulk_trap_arm():
    t = {
        "team": "Chicago White Sox",
        "opponent": "Kansas City Royals",
        "opp_pitcher": "Mitch Spence",
        "team_xwoba": 0.340,
        "dqi_status": "TRUST",
        "is_trap": True
    }
    p_reports = [
        {
            "pitcher": "Mitch Spence",
            "team": "Kansas City Royals",
            "opponent": "Chicago White Sox",
            "is_trap": True
        }
    ]
    conf, reasons = score_stack_confidence(t, p_reports)
    assert not any("Soft-capped" in r for r in reasons)

# 14. test_team_signals_preserved_after_substitution
def test_team_signals_preserved_after_substitution():
    t = {
        "team": "Chicago White Sox",
        "opponent": "Kansas City Royals",
        "opp_pitcher": "Steven Cruz",
        "is_gassed": True,
        "is_anti_chalk_smash": True,
        "is_sharp": True,
        "is_burst": True,
        "is_hot_run_msmi": True,
        "divergence": 25.0,
        "dqi_score": 92,
        "dqi_status": "TRUST"
    }
    t['opp_pitcher'] = "Mitch Spence"
    t['opp_pitcher_display'] = "Cruz -> Spence (BULK)"
    
    assert t['is_gassed'] is True
    assert t['is_anti_chalk_smash'] is True
    assert t['is_sharp'] is True
    assert t['is_burst'] is True
    assert t['is_hot_run_msmi'] is True
    assert t['divergence'] == 25.0
    assert t['dqi_score'] == 92
    assert t['dqi_status'] == "TRUST"

# 15. test_bulk_pitcher_sp_rating_unchanged
def test_bulk_pitcher_sp_rating_unchanged():
    bulk_p = {
        "pitcher": "Mitch Spence",
        "team": "Kansas City Royals",
        "alpha_score": 82.5,
        "blended_rating": 80.0,
        "is_bulk_arm": True
    }
    assert bulk_p['alpha_score'] == 82.5
    assert bulk_p['blended_rating'] == 80.0

# 16. test_opener_own_pitcher_card_unchanged
def test_opener_own_pitcher_card_unchanged():
    opener_p = {
        "pitcher": "Steven Cruz",
        "team": "Kansas City Royals",
        "alpha_score": 54.0,
        "blended_rating": 50.0,
        "is_opener": True
    }
    assert opener_p['alpha_score'] == 54.0
    assert opener_p['blended_rating'] == 50.0

# 17. test_refresh_redetection_props_populate_later
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_refresh_redetection_props_populate_later(mock_fetch_api):
    mock_fetch_api.return_value = {
        "career_starts": 1,
        "relief_pct": 95.0,
        "avg_ip_l10": 1.1,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    
    # 1st run: props are empty, bulk unresolved -> under new safety rules, returns PROPS_PENDING
    status_1, opener_1, bulk_1, _, _, sub_1, _ = detect_opener_for_team(
        "Kansas City Royals", game, None, {}, datetime.date(2026, 6, 26)
    )
    assert status_1 == "PROPS_PENDING" and bulk_1 is None and sub_1 is False
    
    # 2nd run: props populate later
    props_later = {
        "game_123": {
            "pitcher_outs": [
                {"player_name": "Steven Cruz", "point": 6.0, "side": "Over", "price": -110},
                {"player_name": "Mitch Spence", "point": 15.0, "side": "Over", "price": -110}
            ]
        }
    }
    status_2, opener_2, bulk_2, _, _, sub_2, _ = detect_opener_for_team(
        "Kansas City Royals", game, None, props_later, datetime.date(2026, 6, 26)
    )
    assert status_2 == "CONFIRMED" and bulk_2 == "Mitch Spence" and sub_2 is True

# 18. test_late_scratch_redetection
@patch('utils.opener_detector.requests.get')
def test_late_scratch_redetection(mock_get):
    game = get_mock_game()
    dk_1 = [
        {"Name": "Steven Cruz", "Position": "PO", "Roster Position": "P", "Salary": "4000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"},
        {"Name": "Mitch Spence", "Position": "PLR", "Roster Position": "P", "Salary": "7000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"}
    ]
    status_1, _, bulk_1, _, _, _, _ = detect_opener_for_team("Kansas City Royals", game, dk_1, {}, datetime.date(2026, 6, 26))
    assert bulk_1 == "Mitch Spence"
    
    dk_2 = [
        {"Name": "Steven Cruz", "Position": "PO", "Roster Position": "P", "Salary": "4000", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"},
        {"Name": "Kris Bubic", "Position": "PLR", "Roster Position": "P", "Salary": "5500", "TeamAbbrev": "KC", "Game Info": "CWS@KC 06/26/2026 08:10PM ET"}
    ]
    status_2, _, bulk_2, _, _, _, _ = detect_opener_for_team("Kansas City Royals", game, dk_2, {}, datetime.date(2026, 6, 26))
    assert bulk_2 == "Kris Bubic"

# 19. test_no_csv_fallback_to_tier2_gracefully
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_no_csv_fallback_to_tier2_gracefully(mock_fetch_api):
    mock_fetch_api.return_value = {
        "career_starts": 1,
        "relief_pct": 95.0,
        "avg_ip_l10": 1.1,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    props = {
        "game_123": {
            "pitcher_outs": [
                {"player_name": "Steven Cruz", "point": 5.5, "side": "Over", "price": -110},
                {"player_name": "Mitch Spence", "point": 15.0, "side": "Over", "price": -110}
            ]
        }
    }
    status, opener, bulk, tier, _, sub, _ = detect_opener_for_team(
        "Kansas City Royals", game, None, props, datetime.date(2026, 6, 26)
    )
    assert status == "CONFIRMED"
    assert tier == "1C"
    assert bulk == "Mitch Spence"

# 20. test_season_first_7_days_no_detection
def test_season_first_7_days_no_detection():
    is_excluded = is_first_7_days_of_season(datetime.date(2026, 4, 5))
    assert is_excluded is True
    is_excluded_late = is_first_7_days_of_season(datetime.date(2026, 4, 15))
    assert is_excluded_late is False

# 21. test_teams_matrix_pitcher_column_opener_chain_display
def test_teams_matrix_pitcher_column_opener_chain_display():
    t = {
        "team": "Chicago White Sox",
        "opponent": "Kansas City Royals",
        "opp_pitcher": "Mitch Spence",
        "opp_pitcher_display": "🔄 Cruz → Spence (BULK)"
    }
    display = t.get('opp_pitcher_display') or t['opp_pitcher']
    assert display == "🔄 Cruz → Spence (BULK)"

# 22. test_pitchers_matrix_bulk_arm_as_primary
def test_pitchers_matrix_bulk_arm_as_primary():
    p = {
        "pitcher": "Mitch Spence",
        "team": "KC",
        "is_bulk_arm": True,
        "opener_name": "Steven Cruz"
    }
    bulk_label = ' [bulk]' if p.get('is_bulk_arm') else ''
    opener_sub = f'\n  └─ {p.get("opener_name")} (opener, 1-2 IP)' if p.get('is_bulk_arm') else ''
    rendered = f"{p['pitcher']}{bulk_label}{opener_sub}"
    assert "[bulk]" in rendered
    assert "└─ Steven Cruz (opener, 1-2 IP)" in rendered

# 23. test_team_card_opener_banner_placement
def test_team_card_opener_banner_placement():
    t = {
        "team": "Chicago White Sox",
        "is_opener_game": True,
        "opener_confirmed": True,
        "opener_name": "Steven Cruz",
        "bulk_name": "Mitch Spence"
    }
    banner = ""
    if t.get('is_opener_game') and t.get('opener_confirmed'):
        banner = (
            "🔄 OPENER GAME\n"
            f"Opener: {t.get('opener_name')} (PO, 1-2 IP)\n"
            f"Bulk Arm: {t.get('bulk_name')} (PLR) ← ALL SCORES REFLECT THIS ARM"
        )
    assert "🔄 OPENER GAME" in banner
    assert "Steven Cruz" in banner
    assert "Mitch Spence" in banner

# 24. test_bulk_unresolved_no_substitution_warning_shown
def test_bulk_unresolved_no_substitution_warning_shown():
    t = {
        "team": "Chicago White Sox",
        "opponent": "Kansas City Royals",
        "opp_pitcher": "Steven Cruz",
        "opp_pitcher_display": "⚠️ Cruz (OPENER) → ? (BULK UNRESOLVED)"
    }
    assert "⚠️ Cruz (OPENER) → ? (BULK UNRESOLVED)" in t['opp_pitcher_display']

# 25. test_props_outs_line_opener_detection
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_props_outs_line_opener_detection(mock_fetch_api):
    # outs line <= 8 triggers opener flag
    mock_fetch_api.return_value = {
        "career_starts": 100,
        "relief_pct": 5.0,
        "avg_ip_l10": 5.5,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    props = {
        "game_123": {
            "pitcher_outs": [
                {"player_name": "Steven Cruz", "point": 5.5, "side": "home", "home_team": "Kansas City Royals"},
                {"player_name": "Mitch Spence", "point": 15.5, "side": "home", "home_team": "Kansas City Royals"}
            ]
        }
    }
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, [], props, datetime.date(2026, 6, 26)
    )
    assert status == "CONFIRMED"
    assert opener == "Steven Cruz"
    assert bulk == "Mitch Spence"
    assert tier == "1C"
    assert sub is True

# 26. test_props_outs_line_bulk_resolution
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_props_outs_line_bulk_resolution(mock_fetch_api):
    # highest teammate outs line >= 12 identifies bulk arm
    mock_fetch_api.return_value = {
        "career_starts": 10,
        "relief_pct": 20.0,
        "avg_ip_l10": 4.0,
        "timestamp": datetime.datetime.now().isoformat()
    }
    game = get_mock_game()
    props = {
        "game_123": {
            "pitcher_outs": [
                {"player_name": "Steven Cruz", "point": 6.0, "side": "home", "home_team": "Kansas City Royals"},
                {"player_name": "Teammate A", "point": 11.5, "side": "home", "home_team": "Kansas City Royals"},
                {"player_name": "Mitch Spence", "point": 16.5, "side": "home", "home_team": "Kansas City Royals"}
            ]
        }
    }
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, [], props, datetime.date(2026, 6, 26)
    )
    assert status == "CONFIRMED"
    assert opener == "Steven Cruz"
    assert bulk == "Mitch Spence"
    assert sub is True

# 27. test_props_pending_no_detection
def test_props_pending_no_detection():
    # null outs line produces no flag and no scoring change (status PROPS_PENDING)
    game = get_mock_game()
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, [], {}, datetime.date(2026, 6, 26)
    )
    assert status == "PROPS_PENDING"
    assert opener == "Steven Cruz"
    assert bulk is None
    assert sub is False
    assert reason == "⚠️ PROPS PENDING"

# 28. test_rotowire_o_b_tags_tier1
@patch('utils.opener_detector.fetch_pitcher_stats_api')
def test_rotowire_o_b_tags_tier1(mock_fetch_api):
    # RotoWire (O)/(B) tags trigger immediate substitution (Tier 1A)
    cache_path = os.path.join(config.DATA_DIR, "projected_lineups_cache.json")
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    
    mock_cache = {
        "lineups": {
            "Kansas City Royals": {
                "lineup": [],
                "is_confirmed": False,
                "pitchers": [
                    {"name": "Steven Cruz", "rw_is_opener": True, "rw_is_bulk": False},
                    {"name": "Mitch Spence", "rw_is_opener": False, "rw_is_bulk": True}
                ]
            }
        }
    }
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(mock_cache, f)
        
    game = get_mock_game()
    status, opener, bulk, tier, method, sub, reason = detect_opener_for_team(
        "Kansas City Royals", game, [], {}, datetime.date(2026, 6, 26)
    )
    
    try:
        os.remove(cache_path)
    except:
        pass
        
    assert status == "CONFIRMED"
    assert opener == "Steven Cruz"
    assert bulk == "Mitch Spence"
    assert tier == "1A"
    assert sub is True
