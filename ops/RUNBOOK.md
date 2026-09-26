# Fulfillment and incidents

## Paid genre brief

1. Confirm the payment in the connected Stripe account. Match the amount to `ops/payments.json` and read the genre from the Payment Link custom field. A GitHub interest issue is not a payment.
2. Run `python3 pipeline/brief.py --genre "GENRE" --out /tmp/brief.html`. Exit code 3 means fewer than 3 charted apps: refund, do not treat it as delivered value.
3. Deliver `/tmp/brief.html` on the customer's GitHub issue, or by the business mailbox once one is connected. Do not commit the file. Do not ask for or store card numbers.
4. Append an order to `ops/ledger.json` with the Stripe payment id, amount, fee, genre, and delivery time. Recompute cash collected, fees, and net operating profit from those fields. Do not count owner test charges.
5. Refunds: refund in Stripe within the published 7-day window, or immediately when the genre has fewer than 3 charted apps. Record the refund in the ledger. Customer liability stays at $0 once the refund is issued.

## Data refresh failed

The `operating-summary` workflow exits non-zero and, once per UTC day, comments on the operating-summary issue. The chart site keeps the last successful commit. Re-run the `refresh` workflow from Actions after the Apple feeds respond. Do not invent chart rows.

## Spend

No ad, API, or new-hosting purchase is authorized. Meta Ad Library and YouTube remain empty until a $0 path exists; do not add paid tokens.

## Stop

Disable the `refresh` and `operating-summary` workflows in GitHub Actions. That stops unattended updates and summary posts. The static site remains up until Pages is turned off separately.
