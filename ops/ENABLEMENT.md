# Owner enablement

Audited 2026-09-26. Only items that this operator cannot finish are listed. Discretionary spend found in the repository: none. Enforced cap until a written authorization exists: $0 of new discretionary spend. A recommendation below is not approval.

## Needed to collect payment

**Stripe merchant connection.** The Stripe tool in this session returned `needsAuth`, and the authentication prompt timed out. Without it, AppSignal cannot charge, refund, or reconcile profit.

- Blocked action: selling the $19 genre brief and recording real cash, fees, and refunds.
- Owner action: complete Stripe authentication for the merchant account whose payout account the owner controls. Narrow scope: read payments and create a Payment Link. After it connects, create one Payment Link for a one-time $19 USD price with a required custom field named `Genre`, then set `ops/payments.json` `payment_link` to the `https://buy.stripe.com/...` or `https://checkout.stripe.com/...` URL and set `status` to `connected`.
- Verification: a Stripe read of the account succeeds, and `brief.html` shows a Pay $19 link only after that URL is present.
- Cost: Stripe's card processing fee on successful charges. No monthly Stripe subscription is required for a single Payment Link. No charge has been made.
- Required now for revenue. Fallback already in use: the free brief stays public, checkout stays visibly closed, and GitHub interest issues record genre names without taking payment.

## Needed for unattended operation

The chart refresh is already an unattended GitHub Actions job. Two gaps remain.

**Stripe webhooks are not set up.** A Payment Link plus the daily summary can support a low volume of manual fulfillment. Unattended fulfillment needs a webhook endpoint and the signing secret in an owner-controlled secret store.

- Blocked action: delivering a brief with no operator session after payment.
- Owner action: none until Stripe is connected. After that, this operator can add a webhook only if the endpoint fits the existing $0 cap (GitHub is not a reliable public webhook receiver).
- Fallback: fulfill from the Stripe payment list on the next operator session, using the runbook.

**No AppSignal mailbox.** The connected Gmail tool is a personal mailbox and is not an AppSignal customer channel. It will not be used to send or read customer mail. `myrmitis.com` mail is on Google (`smtp.google.com`). Cloudflare Email Routing for that domain is misconfigured (`mx.foreign`) and was not changed.

- Blocked action: email delivery and inbound support.
- Owner action, optional for the GitHub-issue path: confirm one mailbox this operator may use for AppSignal, or create `appsignal@` on an existing domain and a sending path that does not replace the Google MX record.
- Verification: a test message to that mailbox is visible from an authorized tool without using the personal Gmail account.
- Cost: $0 if an existing Google mailbox or a free routing address is reused. Required only if customers should not need a GitHub account. Fallback: delivery and support stay on public GitHub issues, and the page says so.

## Optional acceleration

**Vercel team access.** The connected Vercel user is on the Hobby plan. Listing projects on the default team returned 403 (`laqaers-projects`). Not required. The site stays on GitHub Pages. Do not create a new Vercel project under the $0 cap.

**House domain.** `myrmitis.com` is the house site, not this product. No DNS record was changed. A subdomain would be optional distribution later and is not required for the current URL.

**Analytics.** No product analytics is installed. Issue count and, once Stripe exists, payments are the measurements. Do not add a paid analytics vendor under the $0 cap.

## Spending recommendation (not approval)

Keep new discretionary spend at $0. Do not buy ads. After Stripe is connected, treat card-processing fees as a cost of money already collected, not as a budget to spend ahead of revenue. No reinvestment rule was found, so do not spend receipts on growth.
