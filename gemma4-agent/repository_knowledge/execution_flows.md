# Behavioral Execution Flows

Generated during `UNDERSTAND` phase for repository memory.

## Entry Point: `checkout()`
```text
REQUEST
  ↓
checkout()  [checkout.py]
    ↓
  validate_cart()  [checkout.py]
    ↓
  calculate_price()  [pricing.py]
      ↓
    calculate_subtotal()  [pricing.py]
      ↓
    apply_discount()  [discounts.py]
        ↓
      validate_coupon()  [discounts.py]
    ↓
  process_payment()  [checkout.py]
    ↓
  send_confirmation()  [checkout.py]
```

## Detected Flow Divergences / Anomalies
- **`pricing.py::calculate_price`**: if discount: calls apply_discount(subtotal, discount) as standalone statement (RETURN VALUE IGNORED) — In `calculate_price()`, a downstream function in the execution flow is invoked as a bare statement without capturing or returning its result.
