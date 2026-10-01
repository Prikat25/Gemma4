# Repository Knowledge Summary

- **Modules Indexed**: 5
- **Functions Summarized**: 8
- **Classes Summarized**: 1
- **Tests Indexed**: 3

## Modules
- `checkout.py` (45 lines) — functions: validate_cart, process_payment, send_confirmation, checkout
- `discounts.py` (25 lines) — functions: validate_coupon, apply_discount
- `pricing.py` (23 lines) — functions: calculate_subtotal, calculate_price
- `tests/__init__.py` (1 lines) — functions: none
- `tests/test_checkout.py` (38 lines) — functions: none

## Functions
- `checkout.py::validate_cart(items) -> bool`: Validates that the shopping cart is non-empty and items have positive prices. (calls: get)
- `checkout.py::process_payment(amount, customer_email) -> Dict[str, Any]`: Processes customer payment for the computed final amount. (calls: none)
- `checkout.py::send_confirmation(payment_receipt) -> Dict[str, Any]`: Builds order confirmation payload after payment capture. (calls: get)
- `checkout.py::checkout(items, customer_email, coupon) -> Dict[str, Any]`: Primary checkout entry point orchestrating validation, pricing, payment, and confirmation. (calls: validate_cart, calculate_price, process_payment, send_confirmation)
- `discounts.py::validate_coupon(coupon) -> bool`: Returns True if the coupon code exists in VALID_COUPONS. (calls: upper, strip)
- `discounts.py::apply_discount(subtotal, coupon) -> float`: Calculates the discount amount to deduct for a given subtotal and coupon code. (calls: upper, validate_coupon, strip)
- `pricing.py::calculate_subtotal(items) -> float`: Calculates raw order subtotal from line items. (calls: get)
- `pricing.py::calculate_price(items, discount) -> float`: Calculates final order price after applying any valid discount coupon. (calls: calculate_subtotal, apply_discount)
