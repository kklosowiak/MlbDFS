from data.statcast_bridge import StatcastBridge


def test_name_from_expected_stats_row():
    row = {"last_name, first_name": "Judge, Aaron"}
    assert StatcastBridge._name_from_expected_stats_row(row, "last_name, first_name") == "Aaron Judge"
