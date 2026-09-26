"""Genre chart brief from stored Apple chart snapshots. Stdlib only. No network.

The brief reports observed ranks. It does not repeat the uncalibrated revenue curve.
"""
import argparse, json, os, pathlib, sqlite3, sys, urllib.parse
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
CHARTS = (
    ("topfreeapplications", "Top Free"),
    ("topgrossingapplications", "Top Grossing"),
    ("toppaidapplications", "Top Paid"),
)
LABELS = dict(CHARTS)
ORDER = {cid: i for i, (cid, _) in enumerate(CHARTS)}
WEEK = 7 * 86400
MOVER_LIMIT = 5
LIST_LIMIT = 15
REPO_ISSUE = "https://github.com/myrmitis/appsignal/issues/new?template=genre-brief.yml&title="
FORMULA = "dl_day=20000*(50/rank)^0.7"


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def esc(s):
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def valid_payment_link(url):
    if not isinstance(url, str) or not url:
        return False
    if any(c in url for c in " \t\r\n\"'<>"):
        return False
    return url.startswith("https://buy.stripe.com/") or url.startswith("https://checkout.stripe.com/")


def normalized_price(value):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 19
    if n != int(n) or not 1 <= int(n) <= 99:
        return 19
    return int(n)


def load_payments(path):
    price, link = 19, None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        price = normalized_price(data.get("price_usd", 19))
        raw = data.get("payment_link")
        if valid_payment_link(raw):
            link = raw
    except (OSError, json.JSONDecodeError):
        pass
    return {"price_usd": price, "payment_link": link, "checkout_open": link is not None}


def request_url(genre):
    return REPO_ISSUE + urllib.parse.quote(f"Genre brief request: {genre}", safe="")


def _rows(db, ts):
    out = []
    for r in db.execute(
        """SELECT a.trackId, a.name, a.seller, a.genre, s.rank, s.chart,
                  s.rating, s.rating_count, s.price
           FROM snapshots s JOIN apps a ON a.trackId=s.trackId WHERE s.ts=?""", (ts,)):
        prev = db.execute(
            """SELECT rating_count, ts FROM snapshots
               WHERE trackId=? AND chart=? AND ts<? ORDER BY ts DESC LIMIT 1""",
            (r[0], r[5], ts)).fetchone()
        vel = None
        if prev and r[7] is not None and prev[0] is not None and ts > prev[1]:
            vel = round((r[7] - prev[0]) / max(1, (ts - prev[1]) / 86400), 1)
        out.append({
            "trackId": r[0], "name": r[1] or "Unknown", "seller": r[2] or "Unknown",
            "genre": r[3] or "Unknown", "rank": r[4], "chart": r[5],
            "rating": r[6], "rating_count": r[7], "price": r[8] or 0, "velocity": vel,
        })
    return out


def load_snapshot(db_path):
    uri = pathlib.Path(db_path).resolve().as_uri() + "?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    try:
        latest = db.execute("SELECT MAX(ts) FROM snapshots").fetchone()[0]
        if latest is None:
            raise ValueError("no snapshots")
        count = db.execute("SELECT COUNT(DISTINCT ts) FROM snapshots").fetchone()[0]
        prior = db.execute("SELECT MAX(ts) FROM snapshots WHERE ts<=?", (latest - WEEK,)).fetchone()[0]
        return {
            "latest_ts": latest,
            "comparison_ts": prior,
            "snapshot_count": count,
            "latest": _rows(db, latest),
            "comparison": _rows(db, prior) if prior else [],
        }
    finally:
        db.close()


def catalog(rows):
    genres = {}
    for r in rows:
        g = genres.setdefault(r["genre"], {"genre": r["genre"], "ids": set(), "charts": {c: set() for c, _ in CHARTS}})
        g["ids"].add(r["trackId"])
        g["charts"].setdefault(r["chart"], set()).add(r["trackId"])
    out = []
    for g in genres.values():
        out.append({
            "genre": g["genre"],
            "apps": len(g["ids"]),
            "top_free": len(g["charts"].get("topfreeapplications", ())),
            "top_grossing": len(g["charts"].get("topgrossingapplications", ())),
            "top_paid": len(g["charts"].get("toppaidapplications", ())),
            "request_url": request_url(g["genre"]),
        })
    out.sort(key=lambda x: (-x["apps"], x["genre"]))
    return out


def _clip(items, limit):
    items = list(items)
    return items[:limit], max(0, len(items) - limit)


def chart_report(latest_rows, prior_rows, genre, chart, movement):
    cur = [r for r in latest_rows if r["genre"] == genre and r["chart"] == chart]
    old = [r for r in prior_rows if r["genre"] == genre and r["chart"] == chart] if movement else []
    cur_by = {r["trackId"]: r for r in cur}
    old_by = {r["trackId"]: r for r in old}
    entered = sorted((cur_by[i] for i in cur_by if i not in old_by), key=lambda r: r["rank"] or 99) if movement else []
    left = sorted((old_by[i] for i in old_by if i not in cur_by), key=lambda r: r["rank"] or 99)
    improved, declined, unchanged = [], [], 0
    for i, r in cur_by.items():
        if i not in old_by:
            continue
        delta = (old_by[i]["rank"] or 99) - (r["rank"] or 99)
        item = {"name": r["name"], "seller": r["seller"], "from_rank": old_by[i]["rank"], "to_rank": r["rank"], "places": abs(delta)}
        if delta > 0:
            improved.append(item)
        elif delta < 0:
            declined.append(item)
        else:
            unchanged += 1
    improved.sort(key=lambda x: -x["places"])
    declined.sort(key=lambda x: -x["places"])
    ent, ent_more = _clip(entered, LIST_LIMIT)
    lef, lef_more = _clip(left, LIST_LIMIT)
    roster = sorted(cur, key=lambda r: r["rank"] or 99)
    return {
        "id": chart,
        "label": LABELS.get(chart, chart),
        "current_count": len(cur),
        "entered": [_public_app(r) for r in ent],
        "entered_more": ent_more,
        "left": [_public_app(r) for r in lef],
        "left_more": lef_more,
        "improved": improved[:MOVER_LIMIT],
        "declined": declined[:MOVER_LIMIT],
        "unchanged": unchanged,
        "roster": [_roster_app(r) for r in roster],
    }


def _public_app(r):
    return {"name": r["name"], "seller": r["seller"], "rank": r["rank"]}


def _roster_app(r):
    return {"name": r["name"], "seller": r["seller"], "rank": r["rank"], "price": r["price"],
            "rating": r["rating"], "rating_count": r["rating_count"], "velocity": r["velocity"]}


def build_genre(snapshot, genre):
    charts = []
    ids = set()
    movement = snapshot["comparison_ts"] is not None
    pool = snapshot["latest"] + (snapshot["comparison"] if movement else [])
    present = {r["chart"] for r in pool if r["genre"] == genre}
    # Always show the three US charts, including a zero, so a missing chart is visible.
    known = [c for c, _ in CHARTS]
    extra = sorted(c for c in present if c not in ORDER)
    for chart in known + extra:
        rep = chart_report(snapshot["latest"], snapshot["comparison"], genre, chart, movement)
        charts.append(rep)
        for r in snapshot["latest"]:
            if r["genre"] == genre and r["chart"] == chart:
                ids.add(r["trackId"])
    apps = len(ids)
    return {
        "genre": genre,
        "apps": apps,
        "thin": apps < 3,
        "charts": charts,
    }


def build_document(snapshot, payments, generated_at):
    cat = catalog(snapshot["latest"])
    if not cat:
        raise ValueError("no charted apps")
    sample = cat[0]["genre"]
    age = None
    if snapshot["comparison_ts"]:
        age = round((snapshot["latest_ts"] - snapshot["comparison_ts"]) / 86400, 1)
    return {
        "generated_at": iso(generated_at),
        "latest_ts": snapshot["latest_ts"],
        "latest_iso": iso(snapshot["latest_ts"]),
        "comparison_ts": snapshot["comparison_ts"],
        "comparison_iso": iso(snapshot["comparison_ts"]) if snapshot["comparison_ts"] else None,
        "comparison_age_days": age,
        "snapshot_count": snapshot["snapshot_count"],
        "price_usd": payments["price_usd"],
        "checkout_open": payments["checkout_open"],
        "payment_link": payments["payment_link"],
        "sample_genre": sample,
        "catalog": cat,
        "brief": build_genre(snapshot, sample),
    }


def price_text(price):
    if not price:
        return "Free"
    return f"${price:.2f}"


def rating_text(rating, count):
    if rating is None:
        return "—"
    return f"{rating:.1f} ({int(count or 0):,} ratings)"


def vel_text(v):
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}/day"


def _apps_html(items, more, rank_label):
    if not items and not more:
        return "<p class=\"mut\">None.</p>"
    rows = "".join(
        f"<tr><td>{esc(a['name'])}<br><span class=\"mut\">{esc(a['seller'])}</span></td><td>{rank_label}{a['rank']}</td></tr>"
        for a in items)
    extra = f"<p class=\"mut\">{more} more not shown.</p>" if more else ""
    return f"<div class=\"tablewrap\"><table><thead><tr><th>App</th><th>Rank</th></tr></thead><tbody>{rows}</tbody></table></div>{extra}"


def _movers_html(items, verb):
    if not items:
        return "<p class=\"mut\">None.</p>"
    lis = "".join(
        f"<li>{esc(a['name'])} ({esc(a['seller'])}) {verb} from #{a['from_rank']} to #{a['to_rank']} ({a['places']} {'place' if a['places']==1 else 'places'}).</li>"
        for a in items)
    return f"<ul>{lis}</ul>"


def render_report(brief, doc):
    movement = doc["comparison_ts"] is not None
    if movement:
        intro = (f"Compared with the snapshot from {esc(doc['comparison_iso'])} "
                 f"({doc['comparison_age_days']} days earlier). "
                 "Entered means the app was not in that chart's top 50 then. "
                 "Left means it was in the top 50 then and is not in the latest top 50. "
                 "Neither means the app launched or was removed from the store.")
    else:
        intro = "No snapshot at least 7 days older is stored yet, so this brief has no rank movement."
    parts = [f"<section id=\"observed\"><h2>{esc(brief['genre'])}</h2>",
             f"<p>{brief['apps']} distinct apps in this genre are on the latest US top charts. "
             "An app on more than one chart is counted once. Genre is the current iTunes lookup genre.</p>",
             f"<p class=\"mut\">{intro}</p>"]
    if brief["thin"]:
        parts.append("<p class=\"warn\">Fewer than 3 charted apps. A paid brief for this genre qualifies for a refund under the policy below.</p>")
    for ch in brief["charts"]:
        parts.append(f"<h3>{esc(ch['label'])} · {ch['current_count']} apps</h3>")
        if ch["current_count"] == 0 and not ch["entered"] and not ch["left"] and not ch["improved"] and not ch["declined"]:
            parts.append("<p>No apps in this genre are in this top 50, including the comparison snapshot.</p>")
            continue
        if movement:
            parts.append("<h4>Entered the top 50</h4>" + _apps_html(ch["entered"], ch["entered_more"], "#"))
            parts.append("<h4>Left the top 50</h4>" + _apps_html(ch["left"], ch["left_more"], "was #"))
            parts.append(f"<p>{ch['unchanged']} apps stayed in the top 50 at the same rank.</p>")
            parts.append("<h4>Moved up</h4>" + _movers_html(ch["improved"], "moved up"))
            parts.append("<h4>Moved down</h4>" + _movers_html(ch["declined"], "moved down"))
        roster = "".join(
            "<tr>"
            f"<td>#{r['rank']}</td><td>{esc(r['name'])}<br><span class=\"mut\">{esc(r['seller'])}</span></td>"
            f"<td>{price_text(r['price'])}</td><td>{esc(rating_text(r['rating'], r['rating_count']))}</td>"
            f"<td>{esc(vel_text(r['velocity']))}</td></tr>"
            for r in ch["roster"])
        if ch["current_count"] == 0:
            parts.append("<p>No apps in this genre are in this top 50.</p>")
        parts.append("<h4>Latest roster</h4>"
                     "<div class=\"tablewrap\"><table><thead><tr><th>Rank</th><th>App</th><th>Price</th><th>Rating</th><th>Rating-count change</th></tr></thead>"
                     f"<tbody>{roster}</tbody></table></div>"
                     "<p class=\"mut\">Rating-count change is the daily change in Apple's public rating count since the previous snapshot for that chart. It is not downloads. The divisor is at least 1 day.</p>")
    parts.append("</section>")
    parts.append(
        f"<section class=\"card\" id=\"heuristic\"><h2>Estimates are not this product</h2>"
        f"<p>The free chart table publishes a rank heuristic ({esc(FORMULA)}). "
        "That curve is not calibrated to store data. On the paid chart it can overstate downloads by a large factor. "
        "Those dollar figures are not included in this brief and are not something you are paying for. "
        "Do not use them for a forecast, a valuation, or a store payout.</p></section>")
    return "".join(parts)


def render_page(doc, standalone=False):
    price = doc["price_usd"]
    if doc["checkout_open"]:
        pay = (f"<a class=\"btn\" href=\"{esc(doc['payment_link'])}\" rel=\"noopener noreferrer\">Pay ${price}</a>"
               "<p class=\"mut\">On the payment page, enter the genre name from the table. "
               "One payment buys one brief. This is not a subscription.</p>")
    else:
        pay = ("<p class=\"warn\">Card checkout is closed. No card payment is collected on this page.</p>"
               "<p class=\"mut\">A GitHub request records the genre you want. The request is public. "
               "Do not include card numbers.</p>")
    if standalone:
        catalog_html = ""
        request_html = ""
    else:
        rows = "".join(
            f"<tr><td>{esc(g['genre'])}</td><td>{g['apps']}</td><td>{g['top_free']}</td><td>{g['top_grossing']}</td><td>{g['top_paid']}</td>"
            f"<td><a href=\"{esc(g['request_url'])}\">Register interest</a></td></tr>"
            for g in doc["catalog"])
        catalog_html = (
            "<section class=\"card\" id=\"catalog\"><h2>Genres in this snapshot</h2>"
            "<p class=\"mut\">Counts are distinct apps. Choosing a genre with fewer than 3 apps qualifies for a refund once checkout is open.</p>"
            "<div class=\"tablewrap\"><table><thead><tr><th>Genre</th><th>Apps</th><th>Top Free</th><th>Top Grossing</th><th>Top Paid</th><th></th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div></section>")
        sample_url = request_url(doc["sample_genre"])
        if doc["checkout_open"]:
            request_html = "<p class=\"mut\">Type one genre name from the table into the payment form.</p>"
        else:
            request_html = (f"<p><a class=\"btn\" id=\"request\" href=\"{esc(sample_url)}\">Register interest in {esc(doc['sample_genre'])}</a></p>"
                            "<label class=\"mut\" for=\"genre\">Or pick another genre</label> "
                            "<select id=\"genre\" aria-label=\"Genre to register\">"
                            + "".join(f"<option value=\"{esc(g['request_url'])}\">{esc(g['genre'])}</option>" for g in doc["catalog"])
                            + "</select>")
    policy = (
        "<section class=\"card\" id=\"policy\"><h2>What you are buying</h2>"
        f"<p>${price} once, when checkout is open, for one genre named at payment. "
        "You receive this same report: observed US Top Free, Top Grossing, and Top Paid placements, "
        "rank movement against the stored snapshot from at least 7 days earlier when that snapshot exists. "
        "The largest genre is published free on this site. The rank-curve dollar estimates on the home page are not included.</p>"
        "<p>This is not a subscription. Ranks, prices, sellers, and ratings come from Apple's public RSS feeds and iTunes lookup. "
        "AppSignal is not affiliated with Apple.</p>"
        "<p>Refunds: ask within 7 days of payment for a full refund. A genre with fewer than 3 charted apps is refunded even after 7 days "
        "if that was the genre named on the order. Support is a GitHub issue on myrmitis/appsignal. "
        "Do not send card numbers.</p></section>")
    script = """<script>
document.getElementById("genre") && document.getElementById("genre").addEventListener("change", function () {
  var link = document.getElementById("request");
  if (!link) return;
  link.href = this.value;
  link.textContent = "Register interest in " + this.options[this.selectedIndex].text;
});
</script>"""
    title_genre = doc["brief"]["genre"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AppSignal {esc(title_genre)} chart brief — ${price}</title>
<meta name="description" content="Which US App Store apps in one genre entered, left, or moved on the Top Free, Top Grossing, and Top Paid charts.">
<link rel="canonical" href="https://myrmitis.github.io/appsignal/brief.html">
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header class="hero">
  <span class="badge">Observed chart ranks · not affiliated with Apple</span>
  <h1>{esc(title_genre)} chart movement</h1>
  <p class="mut">Snapshot {esc(doc['latest_iso'])}. ${price} once for another genre. The free chart table stays on the <a href="./">home page</a>.</p>
</header>
<main>
<section class="card" id="offer">
  <h2>${price} genre brief</h2>
  <p>Indie developers can already see one chart at a time. This brief puts Top Free, Top Grossing, and Top Paid for a single genre on one page and shows who moved since the earlier stored snapshot.</p>
  {pay}
  {request_html}
</section>
{catalog_html}
{render_report(doc["brief"], doc)}
{policy}
</main>
<footer><p class="mut">AppSignal · {esc(doc['generated_at'])} · formula {esc(FORMULA)} · not affiliated with Apple or appkittie.</p></footer>
{"" if standalone else script}
</body>
</html>
"""


def atomic_write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def main(argv=None):
    p = argparse.ArgumentParser(description="Build the AppSignal genre chart brief")
    p.add_argument("--db", default=os.path.join(ROOT, "data", "appintel.db"))
    p.add_argument("--payments", default=os.path.join(ROOT, "ops", "payments.json"))
    p.add_argument("--genre")
    p.add_argument("--out")
    p.add_argument("--now", type=int)
    args = p.parse_args(argv)
    try:
        snapshot = load_snapshot(args.db)
    except (sqlite3.Error, ValueError) as e:
        print(f"FAIL brief: {e}", file=sys.stderr)
        return 1
    payments = load_payments(args.payments)
    now = args.now or int(datetime.now(timezone.utc).timestamp())
    doc = build_document(snapshot, payments, now)
    if args.genre:
        if not args.out:
            print("FAIL brief: --out is required with --genre", file=sys.stderr)
            return 2
        known = {g["genre"] for g in doc["catalog"]}
        if args.genre not in known:
            print(f"FAIL brief: unknown genre {args.genre}", file=sys.stderr)
            return 2
        one = dict(doc)
        one["brief"] = build_genre(snapshot, args.genre)
        one["sample_genre"] = args.genre
        atomic_write(args.out, render_page(one, standalone=True))
        print(f"wrote {args.out} genre={args.genre} apps={one['brief']['apps']} thin={one['brief']['thin']}")
        return 3 if one["brief"]["thin"] else 0
    atomic_write(os.path.join(ROOT, "data", "brief.json"), json.dumps(doc, indent=2) + "\n")
    atomic_write(os.path.join(ROOT, "brief.html"), render_page(doc, standalone=False))
    print(f"wrote brief.html sample={doc['sample_genre']} apps={doc['brief']['apps']} checkout={doc['checkout_open']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
