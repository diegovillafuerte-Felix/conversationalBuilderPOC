"""Mock wallet service."""

import random
import string
from datetime import datetime, timedelta
from typing import Optional


def _random_string(length: int = 8) -> str:
    """Generate a random alphanumeric string."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class MockWalletService:
    """Mock service for wallet operations."""

    def __init__(self, language: str = "es"):
        self.language = language
        self._balances = {
            "user_demo": 45.50,
        }
        self._payment_methods = {
            "user_demo": [
                {
                    "id": "pm_1",
                    "type": "debit_card",
                    "last4": "4242",
                    "brand": "Visa",
                    "isDefault": True,
                },
                {
                    "id": "pm_2",
                    "type": "bank_account",
                    "last4": "6789",
                    "bankName": "Chase",
                    "isDefault": False,
                },
            ]
        }

    def get_balance(self, user_id: str) -> dict:
        """Get wallet balance."""
        balance = self._balances.get(user_id, self._balances.get("user_demo", 0))
        return {
            "balance": balance,
            "currency": "USD",
            "lastUpdated": datetime.utcnow().isoformat(),
        }

    def get_payment_methods(self, user_id: str) -> list:
        """Get linked payment methods."""
        return self._payment_methods.get(
            user_id, self._payment_methods.get("user_demo", [])
        )

    def add_funds(
        self,
        amount: float,
        payment_method_id: str = "pm_1",
        user_id: Optional[str] = None,
    ) -> dict:
        """Add funds to wallet."""
        user = user_id or "user_demo"
        current_balance = self._balances.get(user, 45.50)
        new_balance = current_balance + amount
        self._balances[user] = new_balance
        transaction_id = f"WAL{_random_string(8)}"
        processed_at = datetime.utcnow().isoformat()

        return {
            "transactionId": transaction_id,
            "amount": amount,
            "previousBalance": current_balance,
            "newBalance": new_balance,
            "status": "completed",
            "processedAt": processed_at,
            "transaction_id": transaction_id,
            "reference": transaction_id,
            "currency": "USD",
            "timestamp": processed_at,
        }

    def get_transactions(self, user_id: str, limit: int = 10) -> list:
        """Get wallet transaction history."""
        return [
            {
                "transactionId": f"WAL{_random_string(6)}",
                "type": "deposit",
                "description": "Fondos agregados",
                "amount": 50.00,
                "date": (datetime.utcnow() - timedelta(days=3)).isoformat(),
            },
            {
                "transactionId": f"WAL{_random_string(6)}",
                "type": "payment",
                "description": "Pago de remesa",
                "amount": -203.99,
                "date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            },
        ][:limit]

    def add_payment_method(
        self,
        method_type: str,
        token: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """Add a new payment method."""
        new_method = {
            "id": f"pm_{_random_string(4)}",
            "type": method_type,
            "last4": _random_string(4),
            "brand": "Visa" if method_type == "debit_card" else None,
            "bankName": "New Bank" if method_type == "bank_account" else None,
            "isDefault": False,
        }
        return {
            "paymentMethod": new_method,
            "status": "added",
        }

    def remove_payment_method(
        self, payment_method_id: str, user_id: Optional[str] = None
    ) -> dict:
        """Remove a payment method."""
        return {
            "paymentMethodId": payment_method_id,
            "status": "removed",
        }
