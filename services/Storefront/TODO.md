# Storefront — TODO

Built: catalog (categories/products/variants), cart, checkout → orders, order
lifecycle, physical-silo routing, initial migration, tests (ruff + mypy strict
+ pytest all green).

Not yet built:
- **Payments** — checkout creates a `pending` order; no payment capture/webhooks.
- **Inventory reservations** — stock is decremented at checkout, not reserved at
  add-to-cart (concurrent checkouts can race; add row-level locking or a
  reservation table).
- **Discounts / promotions / tax / shipping calculation.**
- **Storefront read auth** — reads are tenant-scoped but not gated; wire the
  gateway JWT check for authenticated customer carts/orders.
- **Domain events** — `order.placed` / `order.fulfilled` are configured on the
  `storefront.events` exchange but not yet published.
- **Fulfillment / returns / refunds.**
