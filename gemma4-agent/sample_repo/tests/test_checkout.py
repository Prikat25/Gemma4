"""Unit tests for the checkout and pricing flow."""

import unittest
from checkout import checkout
from pricing import calculate_price


class TestCheckoutFlow(unittest.TestCase):
    def test_checkout_without_coupon(self):
        items = [
            {"name": "Keyboard", "price": 80.0, "quantity": 1},
            {"name": "Mouse", "price": 40.0, "quantity": 1},
        ]
        result = checkout(items, customer_email="alice@example.com", coupon=None)
        self.assertTrue(result["confirmed"])
        self.assertEqual(result["charged_amount"], 120.0)

    def test_checkout_applies_coupon(self):
        items = [
            {"name": "Keyboard", "price": 80.0, "quantity": 1},
            {"name": "Mouse", "price": 40.0, "quantity": 1},
        ]
        result = checkout(items, customer_email="bob@example.com", coupon="SAVE20")
        self.assertTrue(result["confirmed"])
        self.assertEqual(
            result["charged_amount"],
            100.0,
            f"Expected: 100.0, Received: {result['charged_amount']}",
        )

    def test_checkout_invalid_coupon_charges_subtotal(self):
        items = [{"name": "Monitor", "price": 120.0, "quantity": 1}]
        price = calculate_price(items, discount="EXPIRED99")
        self.assertEqual(price, 120.0)


if __name__ == "__main__":
    unittest.main()
