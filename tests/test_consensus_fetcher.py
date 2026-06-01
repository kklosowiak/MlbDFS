from data.consensus_fetcher import ConsensusFetcher

def test_is_sharp_consensus_signature_robustness():
    fetcher = ConsensusFetcher()
    splits_data = {
        "NYY": {"ticket": 40, "money": 70},
        "BOS": {"ticket": 50, "money": 30}
    }
    
    # Test with 2 arguments
    assert fetcher.is_sharp_consensus("New York Yankees", splits_data) is True
    assert fetcher.is_sharp_consensus("Boston Red Sox", splits_data) is False
    
    # Test with 3 arguments (ml_move parameter)
    assert fetcher.is_sharp_consensus("New York Yankees", splits_data, -15.0) is True
    assert fetcher.is_sharp_consensus("Boston Red Sox", splits_data, 5.0) is False

def test_is_sharp_consensus_invalid_team():
    fetcher = ConsensusFetcher()
    splits_data = {
        "NYY": {"ticket": 40, "money": 70}
    }
    assert fetcher.is_sharp_consensus("Invalid Team Name", splits_data) is False
