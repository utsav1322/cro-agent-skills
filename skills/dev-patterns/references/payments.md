# Payments

## Pick

| Market / stack | Default | Notes |
|---|---|---|
| India, Next/custom | Razorpay (Cashfree alt) | UPI/cards/netbanking. International cards must be enabled on the account (verify). |
| India, WordPress | Official gateway plugin or KnitPay/Pronamic | Woo + Razorpay Magic Checkout (1CC) only if client wants it; quirks below. |
| International | Stripe (Checkout / Payment Element); PayPal secondary | Multi-currency settle per Stripe account config. |
| Shopify | Shopify Payments / client's checkout app (GoKwik, FlexyPe) | Don't build. Track purchases server-side. |
| GCC / other | Client's acquirer behind a thin adapter | Only add the adapter when a 2nd provider is real. |

Merchant account, keys, payouts = **client-owned**. Key id + secret + webhook secret travel as one set; test and live never mixed.

## Order state machine

```
PENDING → AWAITING_PAYMENT → PAID → FULFILLED/SHIPPED → DELIVERED
                ↘ FAILED / CANCELLED (timeout sweep releases stock)
PAID → PARTIALLY_REFUNDED → REFUNDED   (refund = own row; status derived)
```

- One transition function: conditional update `WHERE status IN (allowed from)`. Race-safe and idempotent.
- Retry never reuses a FAILED/CANCELLED order.
- Gap-free invoice numbers: assign only on PAID; use a checkout ref (`CHK-…`) before. Send the checkout ref to the gateway.

## Flow

1. Server builds the order from DB prices + tax + shipping + discount → `amountMinor` + `currency`. One breakdown function used by checkout, invoice, emails.
2. Server creates gateway order/session (amount from DB, our ref, idempotency key). Client receives only gateway order id + public key.
3. Return URL = UX only ("processing…", poll our status). Many buyers never return.
4. Truth = signed webhook / server-to-server callback, or server-side status fetch from gateway API.
5. Mark paid: amount + currency match → conditional update → side effects once (stock, email, invoice, analytics) via job/outbox.
6. Unpaid sweep (cron, e.g. 120 min) → FAILED + release stock.
7. Daily reconciliation job: gateway payments for window vs orders. Paid-at-gateway-not-in-DB → fix + alert. Keep a rolling gateway event log.
8. Refunds: gateway refund API with idempotency key → refund row → credit note in accounting.

```ts
// checkout: amount never comes from the client
const order = await createOrderFromCart(user.id);                // amountMinor from DB
const rp = await razorpay.orders.create({ amount: order.amountMinor, currency: order.currency, receipt: order.ref });
await db.order.update({ where: { id: order.id }, data: { gatewayOrderId: rp.id, status: 'AWAITING_PAYMENT' } });
return NextResponse.json({ data: { gatewayOrderId: rp.id } });   // public key via NEXT_PUBLIC_RAZORPAY_KEY_ID

// client callback check: HMAC_SHA256(`${order_id}|${payment_id}`, RAZORPAY_KEY_SECRET) === razorpay_signature
// webhook check:         HMAC_SHA256(rawBody, RAZORPAY_WEBHOOK_SECRET) === X-Razorpay-Signature
// Stripe:                stripe.webhooks.constructEvent(rawBody, sigHeader, STRIPE_WEBHOOK_SECRET)

export async function markPaid(gatewayOrderId: string, paidMinor: number, currency: string) {
  const o = await db.order.findUnique({ where: { gatewayOrderId } });
  if (!o) throw new Error('unknown order');
  if (o.amountMinor !== paidMinor || o.currency !== currency) return flagForReview(o.id, 'amount_mismatch');
  const r = await db.order.updateMany({ where: { id: o.id, status: 'AWAITING_PAYMENT' }, data: { status: 'PAID', paidAt: new Date() } });
  if (r.count === 1) await enqueue('order.paid', { orderId: o.id });  // 0 = already paid → no-op
}
```

WP: same rules. Dedupe side effects with an order meta flag; take amounts from the order row, never `$_POST`.

## India tax basics (all verify with client's CA)

- GST invoice: seller GSTIN, invoice no. unique + sequential per FY (≤16 chars), date, HSN/SAC, place of supply. Intra-state CGST+SGST, inter-state IGST. B2B needs buyer GSTIN.
- Export of services (international clients): zero-rated under LUT, no IGST, currency + INR value, LUT declaration text.
- e-invoicing (IRN) above turnover threshold.
- B2C price display tax-inclusive.
- Recurring on Indian cards → RBI e-mandate / AFA rules; plain card subscriptions fail.
- Invoice identity (GSTIN/PAN/bank) = the client's, never the agency's copied in from a template.

## Gotchas from real projects

- Two key pairs on one box; plugin read the test key from a DB option, live key sat unused in `.env`. Prove live by fingerprint (live-only methods, MID name on a real txn).
- No callback URL registered with the gateway → zero webhooks for weeks. Register + send a test.
- Razorpay Magic Checkout (Woo 1CC): coupon with empty **Description** is hidden → "Something went wrong". 1CC skips classic thank-you hooks → GA4 purchase from our own hook, deduped on order meta.
- GoKwik/FlexyPe bypass Shopify checkout: Buy Now drops line-item properties; orders carry no channel (conversion tile ~0%); purchase events must be server-side (`orders/create` webhook).
- Aggregated `discount` column re-deducted on invoice → short invoices. One breakdown function.
- Wallet (Google Pay) fails: no `gateway_id`/`rrn` on status = never reached the bank → gateway routing issue, not the customer.
- Separate WP payment site: poisoned OPcache 500s while every disk check passes → `opcache_reset()` via web SAPI; watchdog on a different host.
- Server-side GA4/CAPI purchase from `markPaid`, one currency for reporting, same `transaction_id` as browser event.

## Verify

- [ ] Tamper amount/price in the client request → charge still equals DB total.
- [ ] Sandbox payment E2E → PAID, 1 email, 1 invoice, stock decremented once.
- [ ] Same webhook replayed 3× → still one of each. Bad signature → 400, no change.
- [ ] Abandoned payment → sweep marks FAILED, stock back.
- [ ] Partial + full refund → rows, status, gateway refund id, credit note.
- [ ] Reconciliation for one day matches gateway dashboard totals.
- [ ] Go-live: one real low-value txn lands in the client's live account.
