"""Mock top-ups service."""

import random
import string
from datetime import datetime
from typing import Optional


def _random_string(length: int = 8) -> str:
    """Generate a random alphanumeric string."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class MockTopUpsService:
    """Mock service for phone top-up operations."""

    def __init__(self, language: str = "es"):
        self.language = language
        self._carriers = {
            "MX": [
                {
                    "id": "telcel",
                    "name": "Telcel",
                    "logo": "telcel.png",
                    "currency": "MXN",
                    "plans": [
                        {"amount": 50, "description": "Amigo Sin Límite 50 - 500MB + 50 min", "data": "500MB", "minutes": 50},
                        {"amount": 100, "description": "Amigo Sin Límite 100 - 1.5GB + 100 min", "data": "1.5GB", "minutes": 100},
                        {"amount": 200, "description": "Amigo Sin Límite 200 - 3GB + ilimitados", "data": "3GB", "minutes": "ilimitados"},
                        {"amount": 500, "description": "Amigo Sin Límite 500 - 8GB + ilimitados + Redes Sociales", "data": "8GB", "minutes": "ilimitados"},
                    ],
                },
                {
                    "id": "movistar",
                    "name": "Movistar",
                    "logo": "movistar.png",
                    "currency": "MXN",
                    "plans": [
                        {"amount": 50, "description": "Movistar 50 - 300MB + 30 min", "data": "300MB", "minutes": 30},
                        {"amount": 100, "description": "Movistar 100 - 1GB + 60 min", "data": "1GB", "minutes": 60},
                        {"amount": 200, "description": "Movistar 200 - 2.5GB + ilimitados", "data": "2.5GB", "minutes": "ilimitados"},
                    ],
                },
                {
                    "id": "att_mx",
                    "name": "AT&T México",
                    "logo": "att.png",
                    "currency": "MXN",
                    "plans": [
                        {"amount": 50, "description": "AT&T Prepago 50 - 400MB", "data": "400MB", "minutes": 40},
                        {"amount": 100, "description": "AT&T Prepago 100 - 1GB", "data": "1GB", "minutes": 80},
                        {"amount": 200, "description": "AT&T Prepago 200 - 2GB", "data": "2GB", "minutes": "ilimitados"},
                        {"amount": 300, "description": "AT&T Prepago 300 - 4GB", "data": "4GB", "minutes": "ilimitados"},
                    ],
                },
                {
                    "id": "unefon",
                    "name": "Unefon",
                    "logo": "unefon.png",
                    "currency": "MXN",
                    "plans": [
                        {"amount": 50, "description": "Unefon 50 - 500MB ilimitados", "data": "500MB", "minutes": "ilimitados"},
                        {"amount": 100, "description": "Unefon 100 - 1.5GB ilimitados", "data": "1.5GB", "minutes": "ilimitados"},
                        {"amount": 150, "description": "Unefon 150 - 2GB ilimitados", "data": "2GB", "minutes": "ilimitados"},
                    ],
                },
            ],
            "GT": [
                {
                    "id": "claro_gt",
                    "name": "Claro Guatemala",
                    "currency": "GTQ",
                    "plans": [
                        {"amount": 25, "description": "Claro 25 - 200MB", "data": "200MB", "minutes": 20},
                        {"amount": 50, "description": "Claro 50 - 500MB", "data": "500MB", "minutes": 50},
                        {"amount": 100, "description": "Claro 100 - 1GB", "data": "1GB", "minutes": 100},
                    ],
                },
                {
                    "id": "tigo_gt",
                    "name": "Tigo Guatemala",
                    "currency": "GTQ",
                    "plans": [
                        {"amount": 25, "description": "Tigo 25 - 200MB", "data": "200MB", "minutes": 25},
                        {"amount": 50, "description": "Tigo 50 - 500MB", "data": "500MB", "minutes": 50},
                        {"amount": 100, "description": "Tigo 100 - 1.5GB", "data": "1.5GB", "minutes": 100},
                    ],
                },
            ],
        }

        self._frequent_numbers = {
            "user_demo": [
                {
                    "phoneNumber": "+52 55 5402 7545",
                    "carrier": "telcel",
                    "nickname": "Mamá",
                    "lastTopup": "2025-01-01",
                },
                {
                    "phoneNumber": "+52 55 3399 7293",
                    "carrier": "telcel",
                    "nickname": "Hermano",
                    "lastTopup": "2024-12-15",
                },
            ]
        }

    def get_carriers(self, country: str = "MX") -> dict:
        """Get available carriers for a country."""
        carriers = self._carriers.get(country.upper(), [])

        return {
            "carriers": carriers,
            "country": country.upper(),
        }

    def get_carrier(self, carrier_id: str, country: str = "MX") -> Optional[dict]:
        """Get a specific carrier."""
        carriers_data = self.get_carriers(country)
        carriers = carriers_data.get("carriers", []) if isinstance(carriers_data, dict) else carriers_data
        carrier_id_lower = carrier_id.lower()
        for c in carriers:
            # Match by ID or name (case-insensitive)
            if c["id"].lower() == carrier_id_lower or c["name"].lower() == carrier_id_lower:
                return c
        return None

    def get_frequent_numbers(self, user_id: str) -> dict:
        """Get user's frequently topped-up numbers."""
        numbers = self._frequent_numbers.get(
            user_id, self._frequent_numbers.get("user_demo", [])
        )

        return {
            "numbers": numbers,
            "count": len(numbers),
        }

    def detect_carrier(self, phone_number: str) -> dict:
        """Detect carrier from phone number (mock)."""
        # Clean phone number
        clean_number = phone_number.replace(" ", "").replace("-", "")

        # Simple mock detection based on prefix
        if clean_number.startswith("+52") or clean_number.startswith("52"):
            carrier = self.get_carrier("telcel", "MX")
            plans = carrier.get("plans", []) if carrier else []

            return {
                "carrier": "telcel",
                "carrierName": "Telcel",
                "country": "MX",
                "currency": "MXN",
                "valid": True,
                "phoneNumber": phone_number,
                "plans": plans,
            }
        elif clean_number.startswith("+502") or clean_number.startswith("502"):
            carrier = self.get_carrier("claro_gt", "GT")
            plans = carrier.get("plans", []) if carrier else []

            return {
                "carrier": "claro_gt",
                "carrierName": "Claro Guatemala",
                "country": "GT",
                "currency": "GTQ",
                "valid": True,
                "phoneNumber": phone_number,
                "plans": plans,
            }

        return {
            "carrier": None,
            "carrierName": None,
            "country": None,
            "valid": False,
            "error": "DETECTION_FAILED",
        }

    def get_carrier_plans(self, carrier_id: str, country: str = "MX") -> list:
        """Get available plans for a carrier."""
        carrier = self.get_carrier(carrier_id, country)
        if carrier:
            return carrier.get("plans", [])
        return []

    def get_topup_price(
        self,
        carrier_id: str,
        amount: float,
        country: str = "MX",
    ) -> dict:
        """Get the USD price for a top-up."""
        carrier = self.get_carrier(carrier_id, country)
        if not carrier:
            raise ValueError(f"Carrier not found: {carrier_id}")

        # Mock exchange rate
        rates = {"MXN": 17.25, "GTQ": 7.82}
        currency = carrier.get("currency", "MXN")
        rate = rates.get(currency, 17.00)

        usd_amount = round(amount / rate, 2)
        fee = 0.99
        total_usd = round(usd_amount + fee, 2)

        return {
            "localAmount": amount,
            "localCurrency": currency,
            "usdAmount": usd_amount,
            "fee": fee,
            "totalUsd": total_usd,
            "exchangeRate": rate,
        }

    def send_topup(
        self,
        phone_number: str,
        carrier_id: str,
        amount: float,
        payment_method_id: str = "pm_default",
        user_id: Optional[str] = None,
    ) -> dict:
        """Send a top-up."""
        pricing = self.get_topup_price(carrier_id, amount)
        topup_id = f"TOP{_random_string(8)}"

        return {
            "topupId": topup_id,
            "phoneNumber": phone_number,
            "carrier": carrier_id,
            "localAmount": amount,
            "localCurrency": pricing["localCurrency"],
            "usdCharged": pricing["totalUsd"],
            "status": "completed",
            "processedAt": datetime.utcnow().isoformat(),
        }

    def get_topup_history(self, user_id: str, limit: int = 5) -> list:
        """Get top-up history."""
        return [
            {
                "topupId": f"TOP{_random_string(6)}",
                "phoneNumber": "+52 33 1234 5678",
                "carrier": "Telcel",
                "amount": 100,
                "currency": "MXN",
                "status": "completed",
                "date": "2025-01-01T10:30:00Z",
            },
            {
                "topupId": f"TOP{_random_string(6)}",
                "phoneNumber": "+52 55 8765 4321",
                "carrier": "Movistar",
                "amount": 50,
                "currency": "MXN",
                "status": "completed",
                "date": "2024-12-15T14:20:00Z",
            },
        ][:limit]
