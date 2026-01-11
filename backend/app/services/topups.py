"""Mock top-ups service."""

import random
import string
from datetime import datetime
from typing import Optional

from app.core.i18n import get_message


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

        # Format user-friendly message
        country_name = get_message(f"topups.country_name.{country.upper()}", self.language)
        carrier_list = "\n".join([f"{i}. {c['name']}" for i, c in enumerate(carriers, 1)])
        message = "📡 " + get_message(
            "topups.carriers_list",
            self.language,
            country=country_name,
            carrier_list=carrier_list
        )

        return {
            "carriers": carriers,
            "_message": message,
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

        # Format a user-friendly message
        if numbers:
            number_list = "\n".join([
                f"{i}. {num['nickname']}: {num['phoneNumber']} ({num['carrier'].capitalize()})"
                for i, num in enumerate(numbers, 1)
            ])
            message = "📱 " + get_message(
                "topups.frequent_numbers",
                self.language,
                number_list=number_list
            )
        else:
            message = get_message("topups.no_frequent_numbers", self.language)

        return {
            "numbers": numbers,
            "_message": message
        }

    def detect_carrier(self, phone_number: str) -> dict:
        """Detect carrier from phone number (mock)."""
        # Clean phone number
        clean_number = phone_number.replace(" ", "").replace("-", "")

        # Simple mock detection based on prefix
        if clean_number.startswith("+52") or clean_number.startswith("52"):
            carrier = self.get_carrier("telcel", "MX")
            plans = carrier.get("plans", []) if carrier else []
            country_name = get_message("topups.country_name.MX", self.language)
            plan_list = "\n".join([f"  • ${p['amount']} MXN - {p['description']}" for p in plans])

            message = "📡 " + get_message(
                "topups.carrier_detected",
                self.language,
                phone_number=phone_number,
                carrier_name="Telcel",
                country=country_name,
                plan_list=plan_list
            )

            return {
                "carrier": "telcel",
                "carrierName": "Telcel",
                "country": "MX",
                "currency": "MXN",
                "valid": True,
                "phoneNumber": phone_number,
                "plans": plans,
                "_message": message,
            }
        elif clean_number.startswith("+502") or clean_number.startswith("502"):
            carrier = self.get_carrier("claro_gt", "GT")
            plans = carrier.get("plans", []) if carrier else []
            country_name = get_message("topups.country_name.GT", self.language)
            plan_list = "\n".join([f"  • Q{p['amount']} - {p['description']}" for p in plans])

            message = "📡 " + get_message(
                "topups.carrier_detected",
                self.language,
                phone_number=phone_number,
                carrier_name="Claro Guatemala",
                country=country_name,
                plan_list=plan_list
            )

            return {
                "carrier": "claro_gt",
                "carrierName": "Claro Guatemala",
                "country": "GT",
                "currency": "GTQ",
                "valid": True,
                "phoneNumber": phone_number,
                "plans": plans,
                "_message": message,
            }

        error_message = get_message("topups.detection_failed", self.language)
        return {
            "carrier": None,
            "carrierName": None,
            "country": None,
            "valid": False,
            "error": error_message,
            "_message": "❌ " + error_message,
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

        # Format user-friendly message
        currency_symbol = "$" if currency == "MXN" else "Q"
        message = "💰 " + get_message(
            "topups.price_summary",
            self.language,
            currency_symbol=currency_symbol,
            amount=f"{amount:.0f}",
            currency=currency,
            usd_amount=f"{usd_amount:.2f}",
            fee=f"{fee:.2f}",
            total_usd=f"{total_usd:.2f}"
        )

        return {
            "localAmount": amount,
            "localCurrency": currency,
            "usdAmount": usd_amount,
            "fee": fee,
            "totalUsd": total_usd,
            "_message": message,
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

        # Format success message
        message = "✅ " + get_message(
            "topups.topup_success",
            self.language,
            phone_number=phone_number,
            carrier=carrier_id.capitalize(),
            amount=f"{amount:.0f}",
            currency=pricing["localCurrency"],
            usd_charged=f"{pricing['totalUsd']:.2f}",
            topup_id=topup_id
        )

        return {
            "topupId": topup_id,
            "phoneNumber": phone_number,
            "carrier": carrier_id,
            "localAmount": amount,
            "localCurrency": pricing["localCurrency"],
            "usdCharged": pricing["totalUsd"],
            "status": "completed",
            "processedAt": datetime.utcnow().isoformat(),
            "_message": message,
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
