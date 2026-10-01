"""Order pricing module."""

from typing import List, Dict, Any, Optional
from discounts import apply_discount


def calculate_subtotal(items: List[Dict[str, Any]]) -> float:
    """Calculates raw order subtotal from line items."""
    subtotal = 0.0
    for item in items:
        price = float(item.get("price", 0.0))
        quantity = int(item.get("quantity", 1))
        subtotal += price * quantity
    return round(subtotal, 2)


def calculate_price(items: List[Dict[str, Any]], discount: Optional[str] = None) -> float:
    """Calculates final order price after applying any valid discount coupon."""
    subtotal = calculate_subtotal(items)
    if discount:
        # BUG: apply_discount is called, but its return value is not subtracted from subtotal
        apply_discount(subtotal, discount)
    return round(subtotal, 2)
