from utils.market_utils import calculate_ml_move
from utils.opening_lines import _pair_key, find_earliest_lines_from_snapshots


def test_ml_move_underdog_to_favorite():
    assert calculate_ml_move(105, -120) == -25.0


def test_ml_move_underdog_steam():
    assert calculate_ml_move(155, 119) == -36.0


def test_pair_key_stable():
    assert _pair_key("A", "B") == "A|B"
