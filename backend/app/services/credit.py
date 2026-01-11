"""Mock credit service."""

import random
import string
from datetime import datetime, timedelta
from typing import Optional

from app.core.i18n import get_message


def _random_string(length: int = 8) -> str:
    """Generate a random alphanumeric string."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class MockCreditService:
    """Mock service for credit operations."""

    def __init__(self, language: str = "es"):
        self.language = language
        self._credit_status = {
            "user_demo": {
                "hasActiveLine": True,
                "creditLimit": 500.00,
                "availableCredit": 350.00,
                "currentBalance": 150.00,
                "minimumPayment": 25.00,
                "dueDate": (datetime.utcnow() + timedelta(days=15)).strftime("%Y-%m-%d"),
                "apr": 35.99,
                "lastPaymentDate": (datetime.utcnow() - timedelta(days=20)).strftime("%Y-%m-%d"),
                "lastPaymentAmount": 50.00,
            }
        }

    def get_credit_status(self, user_id: str) -> dict:
        """Get user's credit status."""
        return self._credit_status.get(user_id, self._credit_status.get("user_demo"))

    def get_offers(self, user_id: str) -> list:
        """Get available credit offers."""
        return [
            {
                "offerId": "off_1",
                "type": "limit_increase",
                "newLimit": 750.00,
                "description": "Aumenta tu límite a $750",
                "expiresAt": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            },
            {
                "offerId": "off_2",
                "type": "promotional_rate",
                "rate": 24.99,
                "description": "Tasa promocional del 24.99% APR por 6 meses",
                "expiresAt": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            },
        ]

    def make_payment(
        self,
        amount: float,
        payment_method_id: str = "pm_default",
        user_id: Optional[str] = None,
    ) -> dict:
        """Make a credit payment."""
        status = self.get_credit_status(user_id or "user_demo")
        new_balance = max(0, status["currentBalance"] - amount)
        new_available = status["creditLimit"] - new_balance

        message = "✅ " + get_message(
            "credit.payment_success",
            self.language,
            amount=f"{amount:.2f}",
            new_balance=f"{new_balance:.2f}"
        )

        return {
            "paymentId": f"PAY{_random_string(8)}",
            "amount": amount,
            "previousBalance": status["currentBalance"],
            "newBalance": new_balance,
            "newAvailableCredit": new_available,
            "status": "completed",
            "processedAt": datetime.utcnow().isoformat(),
            "_message": message,
        }

    def get_transactions(self, user_id: str, limit: int = 10) -> list:
        """Get credit transaction history."""
        return [
            {
                "transactionId": f"CTX{_random_string(6)}",
                "type": "purchase",
                "description": "Remesa a María García",
                "amount": -75.00,
                "date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
            },
            {
                "transactionId": f"CTX{_random_string(6)}",
                "type": "payment",
                "description": "Pago recibido",
                "amount": 50.00,
                "date": (datetime.utcnow() - timedelta(days=20)).isoformat(),
            },
            {
                "transactionId": f"CTX{_random_string(6)}",
                "type": "purchase",
                "description": "Recarga Telcel",
                "amount": -25.00,
                "date": (datetime.utcnow() - timedelta(days=25)).isoformat(),
            },
        ][:limit]

    def accept_offer(self, offer_id: str, user_id: Optional[str] = None) -> dict:
        """Accept a credit offer."""
        message = "✅ " + get_message("credit.offer_accepted", self.language)
        return {
            "offerId": offer_id,
            "status": "accepted",
            "effectiveDate": datetime.utcnow().isoformat(),
            "_message": message,
        }
