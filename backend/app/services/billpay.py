"""Mock bill payment service."""

import random
import string
from datetime import datetime, timedelta
from typing import Optional

from app.core.i18n import get_message


def _random_string(length: int = 8) -> str:
    """Generate a random alphanumeric string."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class MockBillPayService:
    """Mock service for bill payment operations."""

    def __init__(self, language: str = "es"):
        self.language = language
        self._billers = [
            {
                "id": "cfe",
                "name": "CFE (Luz)",
                "category": "utilities",
                "requiresAccountNumber": True,
                "accountNumberFormat": "12 dígitos",
                "logo": "cfe.png",
            },
            {
                "id": "telmex",
                "name": "Telmex",
                "category": "telecom",
                "requiresAccountNumber": True,
                "accountNumberFormat": "10 dígitos",
                "logo": "telmex.png",
            },
            {
                "id": "izzi",
                "name": "Izzi",
                "category": "telecom",
                "requiresAccountNumber": True,
                "accountNumberFormat": "Número de cuenta",
                "logo": "izzi.png",
            },
            {
                "id": "totalplay",
                "name": "Totalplay",
                "category": "telecom",
                "requiresAccountNumber": True,
                "accountNumberFormat": "Número de cliente",
                "logo": "totalplay.png",
            },
            {
                "id": "agua_gdl",
                "name": "SIAPA Guadalajara",
                "category": "utilities",
                "requiresAccountNumber": True,
                "accountNumberFormat": "NIS",
                "logo": "siapa.png",
            },
        ]

        self._saved_billers = {
            "user_demo": [
                {
                    "id": "saved_1",
                    "billerId": "cfe",
                    "billerName": "CFE (Luz)",
                    "accountNumber": "123456789012",
                    "nickname": "Casa mamá",
                },
                {
                    "id": "saved_2",
                    "billerId": "telmex",
                    "billerName": "Telmex",
                    "accountNumber": "3312345678",
                    "nickname": "Teléfono mamá",
                },
            ]
        }

    def get_billers(self, category: Optional[str] = None) -> list:
        """Get available billers, optionally filtered by category."""
        if category:
            return [b for b in self._billers if b["category"] == category]
        return self._billers

    def get_biller(self, biller_id: str) -> Optional[dict]:
        """Get a specific biller."""
        for b in self._billers:
            if b["id"] == biller_id:
                return b
        return None

    def get_saved_billers(self, user_id: str) -> list:
        """Get user's saved billers."""
        return self._saved_billers.get(user_id, self._saved_billers.get("user_demo", []))

    def get_bill_details(
        self,
        biller_id: str,
        account_number: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """Get bill details for an account."""
        biller = self.get_biller(biller_id)
        if not biller:
            raise ValueError(f"Biller not found: {biller_id}")

        # Generate mock bill details
        amount_mxn = random.uniform(300, 1500)

        return {
            "billerId": biller_id,
            "billerName": biller["name"],
            "accountNumber": account_number,
            "accountHolder": "María García López",
            "amountDue": round(amount_mxn, 2),
            "currency": "MXN",
            "dueDate": (datetime.utcnow() + timedelta(days=random.randint(5, 20))).strftime("%Y-%m-%d"),
            "lastPaymentDate": (datetime.utcnow() - timedelta(days=random.randint(25, 35))).strftime("%Y-%m-%d"),
            "lastPaymentAmount": round(random.uniform(300, 1200), 2),
        }

    def calculate_payment(
        self,
        biller_id: str,
        amount_mxn: float,
    ) -> dict:
        """Calculate USD amount for a bill payment."""
        rate = 17.25
        usd_amount = round(amount_mxn / rate, 2)
        fee = 1.99

        return {
            "amountMxn": amount_mxn,
            "exchangeRate": rate,
            "amountUsd": usd_amount,
            "fee": fee,
            "totalUsd": round(usd_amount + fee, 2),
        }

    def pay_bill(
        self,
        biller_id: str,
        account_number: str,
        amount: float,
        payment_method_id: str = "pm_default",
        user_id: Optional[str] = None,
    ) -> dict:
        """Pay a bill."""
        biller = self.get_biller(biller_id)
        if not biller:
            raise ValueError(f"Biller not found: {biller_id}")

        pricing = self.calculate_payment(biller_id, amount)
        confirmation_id = _random_string(12).upper()

        message = "✅ " + get_message(
            "billpay.payment_success",
            self.language,
            biller_name=biller["name"],
            account_number=account_number,
            amount=f"{amount:.2f}",
            currency="MXN",
            confirmation_id=confirmation_id
        )

        return {
            "paymentId": f"BILL{_random_string(8)}",
            "biller": biller_id,
            "billerName": biller["name"],
            "accountNumber": account_number,
            "amountPaid": amount,
            "currency": "MXN",
            "usdCharged": pricing["totalUsd"],
            "status": "completed",
            "confirmationNumber": confirmation_id,
            "processedAt": datetime.utcnow().isoformat(),
            "_message": message,
        }

    def save_biller(
        self,
        biller_id: str,
        account_number: str,
        nickname: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """Save a biller for quick access."""
        biller = self.get_biller(biller_id)
        if not biller:
            raise ValueError(f"Biller not found: {biller_id}")

        message = "✅ " + get_message("billpay.biller_saved", self.language)
        return {
            "id": f"saved_{_random_string(4)}",
            "billerId": biller_id,
            "billerName": biller["name"],
            "accountNumber": account_number,
            "nickname": nickname,
            "status": "saved",
            "_message": message,
        }

    def get_payment_history(self, user_id: str, limit: int = 5) -> list:
        """Get bill payment history."""
        return [
            {
                "paymentId": f"BILL{_random_string(6)}",
                "billerName": "CFE (Luz)",
                "accountNumber": "123456789012",
                "amount": 850.00,
                "currency": "MXN",
                "status": "completed",
                "date": "2025-01-05T16:45:00Z",
            },
            {
                "paymentId": f"BILL{_random_string(6)}",
                "billerName": "Telmex",
                "accountNumber": "3312345678",
                "amount": 450.00,
                "currency": "MXN",
                "status": "completed",
                "date": "2024-12-20T11:30:00Z",
            },
        ][:limit]
