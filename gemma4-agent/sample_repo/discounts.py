"""Discount validation and calculation helpers."""

from typing import Dict

VALID_COUPONS: Dict[str, float] = {
    "SAVE20": 20.0,
    "WELCOME10": 10.0,
    "HALF50": 50.0,
}


def validate_coupon(coupon: str) -> bool:
    """Returns True if the coupon code exists in VALID_COUPONS."""
    if not coupon:
        return False
    return coupon.strip().upper() in VALID_COUPONS


def apply_discount(subtotal: float, coupon: str) -> float:
    """Calculates the discount amount to deduct for a given subtotal and coupon code."""
    if not validate_coupon(coupon):
        return 0.0
    code = coupon.strip().upper()
    discount_amount = VALID_COUPONS[code]
    return min(subtotal, discount_amount)
