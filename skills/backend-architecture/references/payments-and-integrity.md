# payments-and-integrity — state machine, reconciliation, duplicates, refunds

Reference for the payment/order lifecycle. The goal is exactly-once BUSINESS EFFECT, auditability, and a recovery path for every partial failure. Original checklist; verify each gateway's behaviour against its current official docs and mark `(verify)`.

## State machine

- Write the explicit states and the ALLOWED transitions before code: e.g. `pending -> awaiting_payment -> paid -> fulfilled`, plus `failed`, `cancelled`, `refunded`, `partially_refunded`. Reject any transition not on the list.
- Each transition names the ONE place its side effects run (stock, email, points, invoice). Do not scatter the same effect across several callers — that is how a status moves without its effects, or an effect fires twice.
- Idempotent effects: entering `paid` twice credits points/stock once. Enforce with a dedupe key (gateway txn id) and a `UNIQUE` ledger row.

## Source of truth

- The SERVER-TO-SERVER callback (or a re-read of the gateway's status API) is authoritative — NOT the browser return URL. A shopper who closes the tab after paying must still get a paid order; a shopper who forges the return URL must not.
- Recompute the amount server-side from the cart. Never trust an amount posted back by the client or embedded in a redirect.

## Duplicate events

- Payment webhooks arrive more than once and out of order. Dedupe on the gateway's transaction/event id. Process the latest authoritative state; do not let an older "pending" overwrite a newer "paid".

## Abandoned / unpaid

- An unpaid attempt parks as `awaiting_payment` and holds nothing permanently. A cron sweep releases reserved stock and marks it `failed` after a timeout `(verify the window with the client)`. Otherwise stock leaks and the catalogue lies.

## Refunds

- Treat refunds as ASYNC. A gateway can answer "accepted" and then fail the actual refund in the background with NO callback, while its status API still reads `settled`. Do not mark the order `refunded` on "accepted".
- Insert the refund as `pending`, then POLL the gateway on a backoff schedule; only run the effects (status, customer email, points reversal, stock, accounting credit note) once the returned/settled amount actually covers it. Fail the refund after a bounded window only when the gateway is readable; never fail it on an unreadable gateway.

## Reconciliation

- Periodically compare YOUR records against the gateway and the accounting system. Mismatches are normal and must be surfaced, not assumed away.
- Guard the test-vs-live boundary hard. A sync pointed at a TEST org/MID while the store takes live cards strands real invoices and real charges in the wrong place. Diff the stored credential/org id against the live one; near-identical ids are a classic misread. Each gateway key pairs with its OWN signing secret — never swap the key alone.
- Watch for a downstream importer reading the wrong field (e.g. an order marked paid landing as COD in another portal) — reconcile on amount + status, not on one field.

## Platform conversion/analytics integrity

- A third-party checkout (GoKwik, FlexyPe and similar) runs its own flow and bypasses the platform's native checkout. Consequences: the platform's conversion-rate tile and native funnel read near-zero because those orders carry no sales channel, and no `checkout_started/completed` events fire. Compute conversion yourself (real orders / sessions) and fire purchase server-side from an `orders/create` webhook with the real order id. Never report the native tile as-is.
- Such checkouts often drop line-item properties — anything that must reach the order goes through the normal cart, not the express button.

## Auditability

- Append-only ledger for money movements (signed amounts, balance = sum), with provenance and actor columns. Every manual adjustment is logged with who and why. This is what answers "why was this customer charged/refunded this".
