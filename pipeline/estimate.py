"""Rank+velocity estimates from stored snapshots. stdlib only. NOT exact data."""
import json, time, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from db import conn
# ponytail: power-curve heuristic; replace with fitted rank-demand model when you have ground truth.
def dl_day(rank):
    return 20000 * (50.0 / max(1, rank)) ** 0.7
def main():
    db = conn(); now = int(time.time()); out = []
    rows = db.execute("""SELECT a.trackId,a.name,a.seller,a.genre,a.price,a.artwork,
        s.rank,s.chart,s.rating,s.rating_count,s.ts FROM apps a
        JOIN snapshots s ON s.trackId=a.trackId
        WHERE s.ts=(SELECT MAX(ts) FROM snapshots)""").fetchall()
    for tid, name, seller, genre, price, art, rank, chart, rating, rc, ts in rows:
        prev = db.execute("SELECT rating_count,ts FROM snapshots WHERE trackId=? AND chart=? AND ts<? ORDER BY ts DESC LIMIT 1",
            (tid, chart, ts)).fetchone()
        vel = round((rc - prev[0]) / max(1, (ts - prev[1]) / 86400), 1) if prev and rc is not None and prev[0] is not None and ts > prev[1] else None
        d = round(dl_day(rank or 50))
        dl_mo = d * 30
        # paid: price*dl; free: freemium ARPU proxy, 3x if on grossing chart
        rev_mo = round((price or 0) * dl_mo * 0.7) if (price or 0) > 0 else round(dl_mo * (0.12 if chart == "topgrossingapplications" else 0.04))
        out.append({"trackId": tid, "name": name, "seller": seller, "genre": genre, "price": price,
            "artwork": art, "rating": rating, "rating_count": rc, "rank": rank, "chart": chart,
            "rc_velocity": vel, "est_dl_mo": dl_mo, "est_rev_mo": rev_mo, "updated_ts": ts, "method": "rank+velocity v1"})
    # Apps on multiple charts would render twice; keep the grossing row (stronger revenue signal).
    out.sort(key=lambda x: (x["chart"] != "topgrossingapplications", x["rank"] or 99))
    seen, dedup = set(), []
    for x in out:
        if x["trackId"] not in seen:
            seen.add(x["trackId"]); dedup.append(x)
    out = dedup
    live_path = os.path.join(os.path.dirname(__file__), "..", "data", "live.json")
    json.dump(out, open(live_path, "w"))
    md = ("# METHOD (rank+velocity v1)\nInputs: Apple RSS rank per chart + lookup rating/price.\n"
        f"Downloads: dl_day=20000*(50/rank)^0.7, x30 for month. Velocity: rating-count delta/day when 2+ snapshots exist.\n"
        "Revenue: paid=price*dl*0.7; free=grossing?0.12:0.04 USD per dl. Caps: none beyond curve.\n"
        "Limits: US charts only, estimates not exact, first run has no velocity. All UI values prefixed est.\n")
    open(os.path.join(os.path.dirname(__file__), "..", "data", "METHOD.md"), "w").write(md)
    print(f"exported {len(out)} apps -> data/live.json | formula: dl_day=20000*(50/rank)^0.7")
    db.close()
if __name__ == "__main__":
    main()
