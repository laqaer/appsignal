"""Operating summary from the committed brief and ledger. No network."""
import argparse, json, os, sys
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
REFRESH_MAX_AGE_H = 28
SNAPSHOT_MAX_AGE_H = 36


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def money(n):
    return f"${n:,.2f}" if isinstance(n, float) and not float(n).is_integer() else f"${int(n):,}"


def assess(summary, refresh_run, now):
    reasons = []
    age_h = (now - summary["snapshot_ts"]) / 3600
    if age_h > SNAPSHOT_MAX_AGE_H:
        reasons.append(f"chart snapshot is {age_h:.1f}h old")
    if not refresh_run:
        reasons.append("no refresh run found")
    else:
        status = refresh_run.get("status")
        conclusion = refresh_run.get("conclusion")
        if status == "completed" and conclusion != "success":
            reasons.append(f"refresh conclusion is {conclusion}")
        created = refresh_run.get("createdAt")
        if created:
            started = datetime.fromisoformat(created.replace("Z", "+00:00"))
            run_age = (datetime.fromtimestamp(now, timezone.utc) - started).total_seconds() / 3600
            if run_age > REFRESH_MAX_AGE_H and status != "in_progress":
                reasons.append(f"latest refresh started {run_age:.1f}h ago")
        elif status != "in_progress":
            reasons.append("refresh run has no start time")
    return {"unhealthy": bool(reasons), "reasons": reasons, "snapshot_age_hours": round(age_h, 1)}


def render_body(summary, day, health):
    obligations = summary.get("outstanding_obligations") or []
    obligation_text = "none" if not obligations else "; ".join(str(x) for x in obligations)
    health_text = "ok" if not health["unhealthy"] else "attention: " + "; ".join(health["reasons"])
    checkout = "open" if summary["checkout_open"] else "closed"
    return "\n".join([
        f"<!-- appsignal-summary:{day} -->",
        "",
        f"## AppSignal operating summary {day}",
        "",
        f"- Cash collected: {money(summary['cash_collected_usd'])}",
        f"- Provisional net operating profit: {money(summary['net_operating_profit_usd'])} ({summary['profit_status']})",
        f"- Paying customers: {summary['paying_customers']}",
        f"- Retained customers: {summary['retained_customers']}",
        f"- Outstanding obligations: {obligation_text}",
        f"- Checkout: {checkout} at {money(summary['price_usd'])} once",
        f"- Free sample: {summary['sample_genre']} ({summary['sample_app_count']} charted apps)",
        f"- Chart snapshot: {iso(summary['snapshot_ts'])} ({health['snapshot_age_hours']}h before this note)",
        f"- Experiment: {summary['experiment_id']}",
        f"- Next action: {summary['next_action']}",
        f"- Health: {health_text}",
        "",
        "Profit is provisional until a payment processor is connected and reconciled. "
        "This note has no card numbers and no customer secrets.",
        "",
    ])


def build_summary(brief, ledger):
    checkout_open = bool(brief.get("checkout_open"))
    if checkout_open:
        nxt = "Reconcile Stripe payments, fulfill paid genre briefs, and record cash, fees, and refunds in ops/ledger.json."
    else:
        nxt = ("Connect the owner Stripe account, create a $19 Payment Link with a required Genre field, "
               "and set ops/payments.json payment_link to that https://buy.stripe.com/ or https://checkout.stripe.com/ URL.")
    return {
        "snapshot_ts": brief["latest_ts"],
        "sample_genre": brief["sample_genre"],
        "sample_app_count": brief["brief"]["apps"],
        "checkout_open": checkout_open,
        "price_usd": brief["price_usd"],
        "cash_collected_usd": ledger.get("cash_collected_usd", 0),
        "net_operating_profit_usd": ledger.get("net_operating_profit_usd", 0),
        "profit_status": ledger.get("profit_status", "provisional"),
        "paying_customers": ledger.get("paying_customers", 0),
        "retained_customers": ledger.get("retained_customers", 0),
        "outstanding_obligations": ledger.get("outstanding_obligations") or [],
        "experiment_id": "001-category-brief",
        "next_action": nxt,
    }


def decide(event, already, summary, refresh_run, now, day):
    health = assess(summary, refresh_run, now)
    post = False
    if not already:
        if event in ("workflow_run", "workflow_dispatch"):
            post = True
        elif event == "schedule" and health["unhealthy"]:
            post = True
    return {"post": post, "unhealthy": health["unhealthy"], "reasons": health["reasons"],
            "body": render_body(summary, day, health)}


def write_summary(brief_path, ledger_path, out_path):
    summary = build_summary(load_json(brief_path), load_json(ledger_path))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")
    os.replace(tmp, out_path)
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description="Write or render the AppSignal operating summary")
    p.add_argument("--brief", default=os.path.join(ROOT, "data", "brief.json"))
    p.add_argument("--ledger", default=os.path.join(ROOT, "ops", "ledger.json"))
    p.add_argument("--out", default=os.path.join(ROOT, "ops", "summary.json"))
    p.add_argument("--decide", action="store_true")
    p.add_argument("--day", default="")
    p.add_argument("--event", default="")
    p.add_argument("--already", action="store_true")
    p.add_argument("--refresh-json", default="")
    p.add_argument("--now", type=int)
    args = p.parse_args(argv)
    summary = build_summary(load_json(args.brief), load_json(args.ledger))
    if not args.decide:
        write_summary(args.brief, args.ledger, args.out)
        print(f"wrote {args.out}")
        return 0
    now = args.now or int(datetime.now(timezone.utc).timestamp())
    day = args.day or datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
    refresh_run = None
    if args.refresh_json:
        with open(args.refresh_json, encoding="utf-8") as f:
            raw = f.read().strip()
        if raw:
            parsed = json.loads(raw)
            refresh_run = parsed[0] if isinstance(parsed, list) else parsed
            if refresh_run == {}:
                refresh_run = None
    decision = decide(args.event, args.already, summary, refresh_run, now, day)
    json.dump(decision, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
