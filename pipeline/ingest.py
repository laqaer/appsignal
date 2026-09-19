"""Pull Apple RSS top charts + lookup details into sqlite. stdlib only."""
import json, time, urllib.request, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from db import conn
UA = {"User-Agent": "AppSignal-demo/1.0"}
CHARTS = ["topfreeapplications", "topgrossingapplications", "toppaidapplications"]
def get(url):
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            if attempt: raise
            time.sleep(1)
def main(limit=50):
    db = conn()
    ts = int(time.time())
    total_snaps = 0
    ids = set()
    for chart in CHARTS:
        try:
            feed = get(f"https://itunes.apple.com/us/rss/{chart}/limit={limit}/json")
        except Exception as e:
            print(f"FAIL chart {chart}: {e}"); sys.exit(1)
        entries = feed.get("feed", {}).get("entry", [])
        if len(entries) < 40:
            print(f"FAIL chart {chart}: only {len(entries)} entries"); sys.exit(1)
        for rank, e in enumerate(entries, 1):
            try: tid = int(e["id"]["attributes"]["im:id"])
            except (KeyError, ValueError): continue
            ids.add(tid)
            db.execute("INSERT OR IGNORE INTO apps(trackId,name,seller,genre,price) VALUES(?,?,?,?,?)",
                (tid, e.get("im:name", {}).get("label", ""), e.get("im:artist", {}).get("label", ""),
                 e.get("category", {}).get("attributes", {}).get("label", ""),
                 float(e.get("im:price", {}).get("attributes", {}).get("amount", 0) or 0)))
            db.execute("INSERT OR REPLACE INTO snapshots VALUES(?,?,?,?,?,?,?)",
                (tid, ts, rank, chart, None, None, None))
            total_snaps += 1
        time.sleep(1)
    # enrich with lookup details (batch 100)
    ids = sorted(ids)
    for i in range(0, len(ids), 100):
        try:
            res = get("https://itunes.apple.com/lookup?id=" + ",".join(map(str, ids[i:i+100])))
        except Exception as e:
            print(f"WARN lookup: {e}"); continue
        for x in res.get("results", []):
            if x.get("wrapperType") != "software": continue
            shots = x.get("screenshotUrls") or x.get("ipadScreenshotUrls") or []
            db.execute("UPDATE apps SET name=?,seller=?,genre=?,price=?,artwork=?,screenshots=?,description=? WHERE trackId=?",
                (x.get("trackName"), x.get("sellerName"), x.get("primaryGenreName"),
                 x.get("price", 0), x.get("artworkUrl100"), json.dumps(shots),
                 x.get("description", ""), x["trackId"]))
            db.execute("UPDATE snapshots SET rating=?,rating_count=?,price=? WHERE trackId=? AND ts=?",
                (x.get("averageUserRating"), x.get("userRatingCount"), x.get("price", 0), x["trackId"], ts))
        time.sleep(1)
    db.commit()
    n_apps = db.execute("SELECT COUNT(*) FROM apps").fetchone()[0]
    print(f"apps={n_apps} snapshots_this_run={total_snaps} ts={ts}")
    db.close()
if __name__ == "__main__":
    main()
