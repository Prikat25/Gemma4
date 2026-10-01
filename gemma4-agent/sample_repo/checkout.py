"""Checkout execution flow module."""

from typing import List, Dict, Any, Optional
from pricing import calculate_price


def validate_cart(items: List[Dict[str, Any]]) -> bool:
    """Validates that the shopping cart is non-empty and items have positive prices."""
    if not items:
        raise ValueError("Cart cannot be empty")
    for item in items:
        if float(item.get("price", 0.0)) < 0 or int(item.get("quantity", 1)) <= 0:
            raise ValueError("Invalid item price or quantity")
    return True


def process_payment(amount: float, customer_email: str) -> Dict[str, Any]:
    """Processes customer payment for the computed final amount."""
    return {
        "charged_amount": round(amount, 2),
        "customer": customer_email,
        "status": "captured",
    }


def send_confirmation(payment_receipt: Dict[str, Any]) -> Dict[str, Any]:
    """Builds order confirmation payload after payment capture."""
    return {
        "confirmed": payment_receipt.get("status") == "captured",
        "charged_amount": payment_receipt["charged_amount"],
        "recipient": payment_receipt["customer"],
    }


def checkout(
    items: List[Dict[str, Any]],
    customer_email: str = "buyer@example.com",
    coupon: Optional[str] = None,
) -> Dict[str, Any]:
    """Primary checkout entry point orchestrating validation, pricing, payment, and confirmation."""
    validate_cart(items)
    final_price = calculate_price(items, discount=coupon)
    receipt = process_payment(final_price, customer_email)
    confirmation = send_confirmation(receipt)
    return confirmation
