"""Mock remittances service."""

import random
import string
from datetime import datetime, timedelta
from typing import Optional

from app.core.i18n import get_message


def _random_string(length: int = 8) -> str:
    """Generate a random alphanumeric string."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class MockRemittancesService:
    """Mock service for remittance operations."""

    def __init__(self, language: str = "es"):
        self.language = language
        # Store mock data
        self._recipients = {
            "user_demo": [
                {
                    "id": "rec_1",
                    "name": "María García",
                    "relationship": "madre",
                    "location": "Guadalajara, JAL",
                    "bank": "BBVA",
                    "accountLast4": "4521",
                },
                {
                    "id": "rec_2",
                    "name": "José García",
                    "relationship": "padre",
                    "location": "Guadalajara, JAL",
                    "bank": "Banorte",
                    "accountLast4": "7832",
                },
                {
                    "id": "rec_3",
                    "name": "Carlos Hernández",
                    "relationship": "hermano",
                    "location": "México, CDMX",
                    "bank": "Santander",
                    "accountLast4": "1234",
                },
            ]
        }

        self._rates = {
            ("USD", "MXN"): 17.25,
            ("USD", "GTQ"): 7.82,
            ("USD", "COP"): 4150.00,
            ("USD", "HNL"): 24.75,
            ("USD", "SVC"): 8.75,
        }

        self._transfers = {}

    def get_exchange_rate(
        self,
        to_currency: str = "MXN",
        from_currency: str = "USD",
        user_id: Optional[str] = None,
    ) -> dict:
        """Get current exchange rate."""
        rate = self._rates.get((from_currency, to_currency), 17.00)
        return {
            "fromCurrency": from_currency,
            "toCurrency": to_currency,
            "rate": rate,
            "fee": 3.99,
            "validUntil": (datetime.utcnow() + timedelta(minutes=15)).isoformat(),
        }

    def get_recipients(self, user_id: str) -> list:
        """Get user's saved recipients."""
        return self._recipients.get(user_id, self._recipients.get("user_demo", []))

    def get_recipient(self, recipient_id: str, user_id: Optional[str] = None) -> Optional[dict]:
        """Get a specific recipient by ID."""
        recipients = self.get_recipients(user_id or "user_demo")
        for r in recipients:
            if r["id"] == recipient_id:
                return r
        return None

    def calculate_transfer(
        self,
        amount_usd: float,
        to_currency: str = "MXN",
        user_id: Optional[str] = None,
    ) -> dict:
        """Calculate transfer details including fees and exchange."""
        rate_info = self.get_exchange_rate(to_currency)
        rate = rate_info["rate"]
        fee = rate_info["fee"]

        return {
            "amountUsd": amount_usd,
            "amountDestination": round(amount_usd * rate, 2),
            "destinationCurrency": to_currency,
            "exchangeRate": rate,
            "fee": fee,
            "totalCharge": round(amount_usd + fee, 2),
            "estimatedArrival": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "arrivalMessage": "en aproximadamente 2 horas",
        }

    def create_transfer(
        self,
        recipient_id: str,
        amount_usd: float,
        payment_method_id: str = "pm_default",
        user_id: Optional[str] = None,
    ) -> dict:
        """Create a new transfer."""
        recipient = self.get_recipient(recipient_id, user_id)
        if not recipient:
            raise ValueError(f"Recipient not found: {recipient_id}")

        calc = self.calculate_transfer(amount_usd)
        transfer_id = f"TXN{_random_string(8)}"

        transfer = {
            "transferId": transfer_id,
            "status": "processing",
            "amountUsd": amount_usd,
            "amountMxn": calc["amountDestination"],
            "exchangeRate": calc["exchangeRate"],
            "fee": calc["fee"],
            "totalCharged": calc["totalCharge"],
            "estimatedArrival": calc["estimatedArrival"],
            "arrivalMessage": calc["arrivalMessage"],
            "recipient": recipient,
            "paymentMethod": payment_method_id,
            "createdAt": datetime.utcnow().isoformat(),
        }

        message = "✅ " + get_message(
            "remittances.transfer_success",
            self.language,
            recipient_name=recipient["name"],
            amount_usd=f"{amount_usd:.2f}",
            amount_local=f"{calc['amountDestination']:.2f}",
            currency="MXN",
            transfer_id=transfer_id
        )
        transfer["_message"] = message

        self._transfers[transfer_id] = transfer
        return transfer

    def get_transfer_status(
        self, transfer_id: str, user_id: Optional[str] = None
    ) -> dict:
        """Get status of a transfer."""
        if transfer_id in self._transfers:
            return self._transfers[transfer_id]

        # Return mock status for unknown transfers
        return {
            "transferId": transfer_id,
            "status": random.choice(["processing", "completed", "available_for_pickup"]),
            "lastUpdate": datetime.utcnow().isoformat(),
        }

    def get_recent_transfers(
        self, user_id: str, limit: int = 5
    ) -> list:
        """Get recent transfers for a user."""
        # Return mock recent transfers
        return [
            {
                "transferId": f"TXN{_random_string(8)}",
                "recipientName": "María García",
                "amountUsd": 200.00,
                "amountMxn": 3450.00,
                "status": "completed",
                "createdAt": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            },
            {
                "transferId": f"TXN{_random_string(8)}",
                "recipientName": "María García",
                "amountUsd": 300.00,
                "amountMxn": 5175.00,
                "status": "completed",
                "createdAt": (datetime.utcnow() - timedelta(days=14)).isoformat(),
            },
        ][:limit]
