# AppSignal operating state

Updated 2026-09-26 by the business-mandate session. Repository `myrmitis/appsignal` at the revision that adds the genre brief. This file is the handoff. Chat history is not required to continue.

## Offer

Primary offer: a one-time **$19 US genre chart brief**. It shows, for one genre, who is on the latest US Top Free, Top Grossing, and Top Paid charts and who entered, left, or changed rank versus the stored snapshot at least 7 days earlier.

Buyer: an indie iOS developer or small studio checking a category before building.

The largest genre is published free at `brief.html`. The existing chart table on `index.html` stays free. Revenue figures are the rank heuristic in `data/METHOD.md` and sit in a labeled appendix.

Checkout is **closed**. `ops/payments.json` has `payment_link: null`. Nothing on the site charges a card.

Experiment: `ops/experiments/001-category-brief.json` (blocked until checkout opens; the free page shipping does not start the 14-day clock).

## Profit

See `ops/ledger.json`. Provisional net operating profit **$0**. Cash collected **$0**. Paying customers **0**. Retained customers **0**. Outstanding customer obligations **none**. No processor is connected, so this is not a reconciled profit figure. Inherited revenue: no evidence in this repository.

New discretionary spend authorized in-repo: **none**. This operator's cap is **$0** of new discretionary spend (ads, new SaaS, contractors, paid APIs).

## What already ran without this session

GitHub Actions workflow `refresh` updates Apple charts daily at 13:00 UTC and pushes to `main`. Successful unattended runs include 2026-09-23, 2026-09-24, and 2026-09-25. Pages deploys `main` to https://myrmitis.github.io/appsignal/. There is no custom domain on that Pages site.

## Runtime after this change

- `refresh` also rebuilds `brief.html`, `data/brief.json`, and `ops/summary.json`, then commits them. Configured when this change is on `main`. Not yet run with the brief step.
- `operating-summary` posts or updates the GitHub issue "AppSignal daily operating summary" after `refresh` completes, and at 18:00 UTC if the refresh looks unhealthy. Configured, not yet unattended-tested.
- Stop the jobs from the GitHub Actions tab on `myrmitis/appsignal`. There is no separate always-on worker.

## Shared systems checked, not adopted

- `laqaer/agent-prompts` registry 1.2 was readable through the `laqaer` GitHub account. Its kit is not installed here. This repository stays the product record.
- `laqaer/junction` at `558986c52729971dfd48c4459477303554a0d1e7` is a local agent/model control plane. It is not the production runtime for this site.
- `laqaer/forge` is a separate product. It was not used.

## Fulfillment

`ops/RUNBOOK.md`. Do not send a brief as if it were paid until a processor payment is reconciled.

## Next action

Connect Stripe for this business, create the $19 Payment Link described in `ops/ENABLEMENT.md`, and set `payment_link`. Then set experiment status to running on the day checkout opens.
