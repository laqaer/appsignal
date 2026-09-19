"""Stdlib checks for estimate helpers. No network."""
import json, sys, os, unittest
sys.path.insert(0, os.path.dirname(__file__))
from estimate import dl_day, keywords

class T(unittest.TestCase):
    def test_dl_curve(self):
        self.assertGreater(dl_day(1), dl_day(50))
        self.assertGreater(dl_day(10), dl_day(40))
    def test_keywords(self):
        k = keywords("Chat GPT App", "Productivity")
        self.assertIn("productivity app", k)
        self.assertLessEqual(len(k), 8)
        self.assertEqual(len(k), len(set(k)))
    def test_shots_parse(self):
        self.assertEqual(json.loads('["https://a"]'), ["https://a"])
        try: json.loads("not-json"); self.fail("expected error")
        except json.JSONDecodeError: pass
    def test_velocity_none_without_prev(self):
        prev, rc, ts = None, 10, 100
        vel = round((rc - prev[0]) / max(1, (ts - prev[1]) / 86400), 1) if prev and rc is not None and prev[0] is not None and ts > prev[1] else None
        self.assertIsNone(vel)

if __name__ == "__main__":
    unittest.main()
