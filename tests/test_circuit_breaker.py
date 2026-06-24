import os
import json
import unittest
from unittest.mock import patch, MagicMock
from data.lineup_fetcher import LineupFetcher

class TestCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.fetcher = LineupFetcher()
        # Ensure files are clean
        self.state_file = os.path.join(os.path.dirname(self.fetcher.cache_file), "lineup_fetcher_state.json")
        self.health_file = os.path.join(os.path.dirname(self.fetcher.cache_file), "data_health.json")
        
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
            except Exception:
                pass
                
        # Cache mock content
        with open(self.fetcher.cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': 0,
                'lineups': {"Atlanta Braves": {"lineup": ["Acuña", "Harris"], "is_confirmed": True}}
            }, f)

    def tearDown(self):
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
            except Exception:
                pass

    @patch('requests.get')
    def test_circuit_breaker_triggers_degraded_status_on_three_failures(self, mock_get):
        # Mock requests.get to throw error
        mock_get.side_effect = Exception("HTTP 500 Internal Server Error")
        
        # 1st failure
        self.fetcher.fetch_rotowire_lineups()
        state = self.fetcher._load_state()
        self.assertEqual(state["consecutive_failures"], 1)
        
        # 2nd failure
        self.fetcher.fetch_rotowire_lineups()
        state = self.fetcher._load_state()
        self.assertEqual(state["consecutive_failures"], 2)
        
        # 3rd failure
        res = self.fetcher.fetch_rotowire_lineups()
        state = self.fetcher._load_state()
        self.assertEqual(state["consecutive_failures"], 3)
        
        # Verify cached lineups were served
        self.assertIn("Atlanta Braves", res)
        self.assertEqual(res["Atlanta Braves"]["lineup"], ["Acuña", "Harris"])
        
        # Verify data_health.json has degraded status
        if os.path.exists(self.health_file):
            with open(self.health_file, 'r', encoding='utf-8') as f:
                health = json.load(f)
            self.assertEqual(health["status"], "degraded")
            self.assertTrue(any("failed 3 consecutive times" in w for w in health.get("warnings", [])))

if __name__ == "__main__":
    unittest.main()
