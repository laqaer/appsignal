"""Operating summary decisions. No network."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
import summary

NOW = 1_790_400_000  # 2026-09-26 12:00:00 UTC approximately; tests use deltas, not the calendar date
BASE = {
    "snapshot_ts": NOW - 3600,
    "sample_genre": "Games",
    "sample_app_count": 47,
    "checkout_open": False,
    "price_usd": 19,
    "cash_collected_usd": 0,
    "net_operating_profit_usd": 0,
    "profit_status": "provisional",
    "paying_customers": 0,
    "retained_customers": 0,
    "outstanding_obligations": [],
    "experiment_id": "001-category-brief",
    "next_action": "Connect Stripe.",
}


def run(created_delta_h=1, conclusion="success", status="completed"):
    return {"conclusion": conclusion, "status": status,
            "createdAt": summary.datetime.fromtimestamp(NOW - created_delta_h * 3600, summary.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


class SummaryTest(unittest.TestCase):
    def test_fresh_success_is_healthy(self):
        health = summary.assess(BASE, run(), NOW)
        self.assertFalse(health["unhealthy"])

    def test_failed_refresh_is_unhealthy(self):
        health = summary.assess(BASE, run(conclusion="failure"), NOW)
        self.assertTrue(health["unhealthy"])

    def test_missed_schedule_is_unhealthy(self):
        health = summary.assess(BASE, run(created_delta_h=30), NOW)
        self.assertTrue(any("started" in r for r in health["reasons"]))

    def test_old_snapshot_is_unhealthy(self):
        stale = dict(BASE, snapshot_ts=NOW - 40 * 3600)
        health = summary.assess(stale, run(), NOW)
        self.assertTrue(any("snapshot" in r for r in health["reasons"]))

    def test_decide_posts_once(self):
        fresh = summary.decide("workflow_run", False, BASE, run(), NOW, "2026-09-26")
        self.assertTrue(fresh["post"])
        self.assertIn("<!-- appsignal-summary:2026-09-26 -->", fresh["body"])
        self.assertIn("Provisional", fresh["body"])
        again = summary.decide("workflow_run", True, BASE, run(), NOW, "2026-09-26")
        self.assertFalse(again["post"])
        quiet = summary.decide("schedule", False, BASE, run(), NOW, "2026-09-26")
        self.assertFalse(quiet["post"])
        alarm = summary.decide("schedule", False, BASE, run(conclusion="failure"), NOW, "2026-09-26")
        self.assertTrue(alarm["post"])
        self.assertTrue(alarm["unhealthy"])
        held = summary.decide("schedule", True, BASE, run(conclusion="failure"), NOW, "2026-09-26")
        self.assertFalse(held["post"])
        self.assertTrue(held["unhealthy"])

    def test_next_action_tracks_checkout(self):
        brief = {"latest_ts": 1, "sample_genre": "Games", "price_usd": 19, "checkout_open": False,
                 "brief": {"apps": 4}}
        ledger = {"cash_collected_usd": 0, "net_operating_profit_usd": 0, "profit_status": "provisional",
                  "paying_customers": 0}
        closed = summary.build_summary(brief, ledger)
        self.assertIn("Stripe", closed["next_action"])
        brief["checkout_open"] = True
        opened = summary.build_summary(brief, ledger)
        self.assertIn("fulfill", opened["next_action"])


if __name__ == "__main__":
    unittest.main()
