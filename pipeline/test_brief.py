"""Genre brief tests. No network and no writes to the tracked database."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(__file__))
import brief
import sqlite3


def row(tid, name, genre, chart, rank, price=0, seller="Seller", rating=4.5, rating_count=10, velocity=None):
    return {"trackId": tid, "name": name, "seller": seller, "genre": genre, "rank": rank, "chart": chart,
            "rating": rating, "rating_count": rating_count, "price": price, "velocity": velocity}


def snap(latest, comparison=None, latest_ts=1_000_000, comparison_ts=1_000_000 - 8 * 86400):
    return {"latest_ts": latest_ts, "comparison_ts": comparison_ts, "snapshot_count": 2 if comparison_ts else 1,
            "latest": latest, "comparison": comparison or []}


class BriefTest(unittest.TestCase):
    def test_payment_link_allowlist(self):
        self.assertTrue(brief.valid_payment_link("https://buy.stripe.com/test_abc"))
        self.assertTrue(brief.valid_payment_link("https://checkout.stripe.com/c/pay_abc"))
        self.assertFalse(brief.valid_payment_link("https://evil.example/buy.stripe.com/x"))
        self.assertFalse(brief.valid_payment_link("javascript:alert(1)"))
        self.assertFalse(brief.valid_payment_link("https://buy.stripe.com/abc\" onclick=\"x"))
        self.assertFalse(brief.valid_payment_link(None))

    def test_price_bounds(self):
        self.assertEqual(brief.normalized_price(19), 19)
        self.assertEqual(brief.normalized_price("nope"), 19)
        self.assertEqual(brief.normalized_price(0), 19)
        self.assertEqual(brief.normalized_price(100), 19)

    def test_request_url_encodes_genre(self):
        url = brief.request_url("Photo & Video")
        self.assertIn("Photo%20%26%20Video", url)
        self.assertTrue(url.startswith("https://github.com/myrmitis/appsignal/issues/new?template=genre-brief.yml&title="))

    def test_sample_genre_and_movement(self):
        latest = [
            row(1, "Alpha <b>", "Games", "topfreeapplications", 4, velocity=3),
            row(1, "Alpha <b>", "Games", "topgrossingapplications", 8),
            row(2, "Beta", "Games", "toppaidapplications", 2, price=4.99),
            row(3, "Gamma", "Utilities", "topfreeapplications", 9),
        ]
        comparison = [
            row(1, "Alpha <b>", "Games", "topfreeapplications", 10),
            row(4, "Delta", "Games", "topfreeapplications", 7),
            row(2, "Beta", "Games", "toppaidapplications", 2, price=4.99),
        ]
        doc = brief.build_document(snap(latest, comparison), {"price_usd": 19, "payment_link": None, "checkout_open": False}, 1_700_000_000)
        self.assertEqual(doc["sample_genre"], "Games")
        self.assertFalse(doc["checkout_open"])
        self.assertEqual(doc["comparison_age_days"], 8.0)
        games = doc["brief"]
        self.assertEqual(games["apps"], 2)
        self.assertTrue(games["thin"])
        free = games["charts"][0]
        self.assertEqual(free["id"], "topfreeapplications")
        self.assertEqual(free["improved"][0]["name"], "Alpha <b>")
        self.assertEqual(free["improved"][0]["places"], 6)
        self.assertEqual(free["left"][0]["name"], "Delta")
        self.assertEqual(free["unchanged"], 0)
        paid = next(c for c in games["charts"] if c["id"] == "toppaidapplications")
        self.assertEqual(paid["unchanged"], 1)
        html = brief.render_page(doc)
        self.assertLess(html.index('id="observed"'), html.index('id="heuristic"'))
        observed = html.split('id="heuristic"')[0]
        self.assertNotIn("Heuristic", observed)
        self.assertIn("Alpha &lt;b&gt;", html)
        self.assertNotIn("Alpha <b>", html)
        self.assertIn("Card checkout is closed", html)
        self.assertIn("not a subscription", html.lower())
        self.assertIn(brief.FORMULA, html)
        self.assertNotIn("buy.stripe.com", html)

    def test_no_comparison_does_not_mark_everyone_entered(self):
        latest = [row(i, f"App{i}", "Games", "topfreeapplications", i) for i in range(1, 4)]
        doc = brief.build_document(snap(latest, comparison_ts=None), {"price_usd": 19, "payment_link": None, "checkout_open": False}, 1_700_000_000)
        self.assertIsNone(doc["comparison_ts"])
        free = doc["brief"]["charts"][0]
        self.assertEqual(free["entered"], [])
        self.assertIn("no rank movement", brief.render_page(doc))

    def test_checkout_link_renders_only_when_valid(self):
        latest = [row(i, f"App{i}", "Games", "topfreeapplications", i) for i in range(1, 4)]
        pay = {"price_usd": 19, "payment_link": "https://buy.stripe.com/abc123", "checkout_open": True}
        html = brief.render_page(brief.build_document(snap(latest), pay, 1_700_000_000))
        self.assertIn('href="https://buy.stripe.com/abc123"', html)
        self.assertIn("Pay $19", html)
        self.assertNotIn("Card checkout is closed", html)

    def test_chart_that_was_fully_left_still_appears(self):
        latest = [row(1, "Stay", "Games", "topfreeapplications", 3)]
        comparison = [row(2, "Gone", "Games", "toppaidapplications", 4)]
        # need 3 latest apps so sample selection is stable; add fillers in another genre
        latest += [row(3, "U", "Utilities", "topfreeapplications", 1), row(4, "U2", "Utilities", "topgrossingapplications", 1)]
        doc = brief.build_document(snap(latest, comparison), {"price_usd": 19, "payment_link": None, "checkout_open": False}, 1_700_000_000)
        self.assertEqual(doc["sample_genre"], "Utilities")
        games = brief.build_genre(snap(latest, comparison), "Games")
        paid = next(c for c in games["charts"] if c["id"] == "toppaidapplications")
        self.assertEqual(paid["current_count"], 0)
        self.assertEqual(paid["left"][0]["name"], "Gone")

    def test_load_snapshot_roundtrip(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            db = sqlite3.connect(path)
            db.execute("CREATE TABLE apps(trackId INTEGER PRIMARY KEY, name TEXT, seller TEXT, genre TEXT, price REAL)")
            db.execute("""CREATE TABLE snapshots(trackId INTEGER, ts INTEGER, rank INTEGER, chart TEXT,
                          rating REAL, rating_count INTEGER, price REAL, PRIMARY KEY(trackId, ts, chart))""")
            latest, prior = 2_000_000, 2_000_000 - 8 * 86400
            db.execute("INSERT INTO apps VALUES (1,'Mover','Co','Games',0)")
            db.execute("INSERT INTO snapshots VALUES (1,?,?,?,?,?,?)", (prior, 10, "topfreeapplications", 4, 100, 0))
            db.execute("INSERT INTO snapshots VALUES (1,?,?,?,?,?,?)", (latest, 4, "topfreeapplications", 4.2, 110, 0))
            db.commit()
            db.close()
            snap = brief.load_snapshot(path)
            self.assertEqual(snap["latest_ts"], latest)
            self.assertEqual(snap["comparison_ts"], prior)
            self.assertEqual(snap["latest"][0]["velocity"], 1.2)
            report = brief.build_genre(snap, "Games")
            self.assertEqual(report["charts"][0]["improved"][0]["places"], 6)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
