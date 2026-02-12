"""Mock remittances service supporting all 7 destination countries."""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


def _random_string(length: int = 8) -> str:
    """Generate a random alphanumeric string."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _random_id(prefix: str = "id") -> str:
    """Generate a random ID with prefix."""
    return f"{prefix}_{_random_string(8)}"


# Country corridor configuration
CORRIDORS = {
    "MX": {
        "name": "Mexico",
        "currency": "MXN",
        "delivery_methods": ["BANK", "CASH", "DEBIT", "WALLET"],
        "typical_rate": 17.25,
    },
    "GT": {
        "name": "Guatemala",
        "currency": "GTQ",
        "delivery_methods": ["BANK", "CASH"],
        "typical_rate": 7.82,
    },
    "HN": {
        "name": "Honduras",
        "currency": "HNL",
        "delivery_methods": ["BANK", "CASH"],
        "typical_rate": 24.75,
    },
    "CO": {
        "name": "Colombia",
        "currency": "COP",
        "delivery_methods": ["BANK", "WALLET"],
        "typical_rate": 4150.00,
        "currency_precision": 0,
    },
    "DO": {
        "name": "Dominican Republic",
        "currency": "DOP",
        "delivery_methods": ["BANK", "CASH"],
        "typical_rate": 57.50,
    },
    "SV": {
        "name": "El Salvador",
        "currency": "USD",
        "delivery_methods": ["BANK"],
        "typical_rate": 1.00,
        "note": "Dollarized economy",
    },
    "NI": {
        "name": "Nicaragua",
        "currency": "NIO",
        "delivery_methods": ["BANK", "CASH"],
        "typical_rate": 36.75,
    },
}

# Wallet types by country
WALLET_TYPES = {
    "MX": [
        {"id": "MERCADO_PAGO", "name": "Mercado Pago", "requires": ["wallet_account"]},
    ],
    "CO": [
        {"id": "NEQUI", "name": "Nequi", "requires": ["phone_number"]},
        {"id": "DAVIPLATA", "name": "Daviplata", "requires": ["phone_number"]},
        {"id": "ZIGI", "name": "Zigi", "requires": ["phone_number"]},
    ],
}

# Delivery method configurations
DELIVERY_METHODS = {
    "BANK": {
        "name": "Bank Deposit",
        "delivery_time": "Within 24 hours",
        "delivery_hours": 24,
    },
    "CASH": {
        "name": "Cash Pickup",
        "delivery_time": "Within 1 hour",
        "delivery_hours": 1,
        "requires_location": True,
        "additional_fee": 5.00,
    },
    "DEBIT": {
        "name": "Debit Card",
        "delivery_time": "Within 30 minutes",
        "delivery_hours": 0.5,
    },
    "WALLET": {
        "name": "Digital Wallet",
        "delivery_time": "Instant",
        "delivery_hours": 0,
    },
}

# KYC limits by level
KYC_LIMITS = {
    "KYC_LITE": {
        "display_name": "Basic",
        "per_transaction": 500,
        "daily": 500,
        "monthly": 1000,
        "semiannual": 3000,
    },
    "SENDER_KYC_L2": {
        "display_name": "ID Verified",
        "per_transaction": 2999,
        "daily": 2999,
        "monthly": 10000,
        "semiannual": 30000,
    },
    "SENDER_KYC_L3": {
        "display_name": "Fully Verified",
        "per_transaction": 5000,
        "daily": 5000,
        "monthly": 25000,
        "semiannual": 75000,
    },
}

# Fee tiers by amount
FEE_TIERS = [
    {"min": 0, "max": 100, "fee": 3.99},
    {"min": 100.01, "max": 300, "fee": 4.99},
    {"min": 300.01, "max": 500, "fee": 5.99},
    {"min": 500.01, "max": 999999, "fee": 6.99},
]

# Transfer states
TRANSFER_STATES = {
    "CREATED": {"cancellable": True, "display": "Created"},
    "PROCESSING": {"cancellable": True, "display": "Processing"},
    "IN_PROGRESS": {"cancellable": False, "display": "In Progress"},
    "COMPLETED": {"cancellable": False, "display": "Completed"},
    "FAILED": {"cancellable": False, "display": "Failed"},
    "CANCELLED": {"cancellable": False, "display": "Cancelled"},
}


class MockRemittancesService:
    """Mock service for remittance operations supporting all 7 countries."""

    def __init__(self, language: str = "es"):
        self.language = language
        self._init_mock_data()

    def _init_mock_data(self):
        """Initialize mock data for demo user."""
        self._user_kyc = {
            "user_demo": "SENDER_KYC_L2",
        }

        self._user_usage = {
            "user_demo": {"daily": 500.00, "monthly": 1500.00, "semiannual": 5000.00},
        }

        self._recipients = {
            "user_demo": [
                {
                    "id": "rec_maria",
                    "name": {
                        "first_name": "María",
                        "last_name": "García",
                        "display_name": "María García",
                    },
                    "country": "MX",
                    "location": {"city": "Guadalajara", "state": "Jalisco"},
                    "delivery_methods": [
                        {
                            "id": "dm_maria_bank",
                            "type": "BANK",
                            "display_name": "BBVA ****4521",
                            "bank_name": "BBVA",
                            "account_last4": "4521",
                            "clabe": "012345678901234521",
                            "is_default": True,
                        },
                        {
                            "id": "dm_maria_cash",
                            "type": "CASH",
                            "display_name": "Cash - Guadalajara",
                            "is_default": False,
                        },
                    ],
                    "created_at": "2025-06-15T10:30:00Z",
                    "last_transfer_at": "2026-01-05T16:45:00Z",
                },
                {
                    "id": "rec_jose",
                    "name": {
                        "first_name": "José",
                        "last_name": "García",
                        "display_name": "José García",
                    },
                    "country": "MX",
                    "location": {"city": "Guadalajara", "state": "Jalisco"},
                    "delivery_methods": [
                        {
                            "id": "dm_jose_bank",
                            "type": "BANK",
                            "display_name": "Banorte ****7832",
                            "bank_name": "Banorte",
                            "account_last4": "7832",
                            "clabe": "072345678901237832",
                            "is_default": True,
                        },
                    ],
                    "created_at": "2025-07-20T14:00:00Z",
                    "last_transfer_at": "2025-12-20T11:30:00Z",
                },
                {
                    "id": "rec_carlos",
                    "name": {
                        "first_name": "Carlos",
                        "last_name": "Hernández",
                        "display_name": "Carlos Hernández",
                    },
                    "country": "CO",
                    "location": {"city": "Bogotá", "state": "Cundinamarca"},
                    "delivery_methods": [
                        {
                            "id": "dm_carlos_nequi",
                            "type": "WALLET",
                            "display_name": "Nequi ****7890",
                            "wallet_type": "NEQUI",
                            "phone_last4": "7890",
                            "is_default": True,
                        },
                    ],
                    "created_at": "2025-09-10T09:00:00Z",
                    "last_transfer_at": "2025-11-15T14:20:00Z",
                },
                {
                    "id": "rec_ana",
                    "name": {
                        "first_name": "Ana",
                        "last_name": "López",
                        "display_name": "Ana López",
                    },
                    "country": "GT",
                    "location": {"city": "Guatemala City", "state": "Guatemala"},
                    "delivery_methods": [
                        {
                            "id": "dm_ana_bank",
                            "type": "BANK",
                            "display_name": "Banrural ****5678",
                            "bank_name": "Banrural",
                            "account_last4": "5678",
                            "is_default": True,
                        },
                    ],
                    "created_at": "2025-08-05T11:00:00Z",
                    "last_transfer_at": None,
                },
            ]
        }

        self._transfers = {}

        # Pre-populate some recent transfers
        self._recent_transfers = {
            "user_demo": [
                {
                    "id": "txn_RECENT01",
                    "recipient_id": "rec_maria",
                    "recipient_name": "María García",
                    "country": "MX",
                    "amount_usd": 200.00,
                    "amount_dest": 3450.00,
                    "currency": "MXN",
                    "rate": 17.25,
                    "fee": 4.99,
                    "delivery_method_id": "dm_maria_bank",
                    "delivery_method_type": "BANK",
                    "delivery_method_display": "BBVA ****4521",
                    "status": "COMPLETED",
                    "created_at": "2026-01-05T16:45:00Z",
                },
                {
                    "id": "txn_RECENT02",
                    "recipient_id": "rec_maria",
                    "recipient_name": "María García",
                    "country": "MX",
                    "amount_usd": 300.00,
                    "amount_dest": 5175.00,
                    "currency": "MXN",
                    "rate": 17.25,
                    "fee": 5.99,
                    "delivery_method_id": "dm_maria_bank",
                    "delivery_method_type": "BANK",
                    "delivery_method_display": "BBVA ****4521",
                    "status": "COMPLETED",
                    "created_at": "2025-12-28T10:30:00Z",
                },
                {
                    "id": "txn_RECENT03",
                    "recipient_id": "rec_carlos",
                    "recipient_name": "Carlos Hernández",
                    "country": "CO",
                    "amount_usd": 150.00,
                    "amount_dest": 622500,
                    "currency": "COP",
                    "rate": 4150.00,
                    "fee": 4.99,
                    "delivery_method_id": "dm_carlos_nequi",
                    "delivery_method_type": "WALLET",
                    "delivery_method_display": "Nequi ****7890",
                    "status": "COMPLETED",
                    "created_at": "2025-11-15T14:20:00Z",
                },
            ]
        }

    def _get_fee(self, amount_usd: float, delivery_type: str = "BANK") -> float:
        """Calculate fee for amount and delivery type."""
        base_fee = 3.99
        for tier in FEE_TIERS:
            if tier["min"] <= amount_usd <= tier["max"]:
                base_fee = tier["fee"]
                break

        # Add cash pickup fee if applicable
        if delivery_type == "CASH":
            base_fee += DELIVERY_METHODS["CASH"].get("additional_fee", 0)

        return base_fee

    # ==================== CORRIDOR & RATE TOOLS ====================

    def get_corridors(self, user_id: Optional[str] = None) -> dict:
        """Get all supported country corridors."""
        corridors = []
        for code, config in CORRIDORS.items():
            corridors.append({
                "country_code": code,
                "country_name": config["name"],
                "currency": config["currency"],
                "delivery_methods": config["delivery_methods"],
            })

        return {
            "corridors": corridors,
        }

    def get_exchange_rate(
        self,
        country: str = "MX",
        to_currency: Optional[str] = None,
        from_currency: str = "USD",
        user_id: Optional[str] = None,
    ) -> dict:
        """Get current exchange rate for a corridor."""
        corridor = CORRIDORS.get(country)
        if not corridor:
            return {
                "error": "COUNTRY_NOT_SUPPORTED",
            }

        currency = to_currency or corridor["currency"]
        rate = corridor["typical_rate"]
        # Add small random variation
        rate = round(rate * (1 + random.uniform(-0.005, 0.005)), 4)

        return {
            "from_currency": from_currency,
            "to_currency": currency,
            "country": country,
            "rate": rate,
            "fee": 3.99,
            "valid_until": (datetime.utcnow() + timedelta(minutes=15)).isoformat(),
        }

    def create_quote(
        self,
        amount_usd: float,
        country: str = "MX",
        delivery_type: str = "BANK",
        user_id: Optional[str] = None,
    ) -> dict:
        """Create a full quote with fees and conversion."""
        corridor = CORRIDORS.get(country)
        if not corridor:
            return {
                "error": "COUNTRY_NOT_SUPPORTED",
            }

        rate = corridor["typical_rate"]
        rate = round(rate * (1 + random.uniform(-0.005, 0.005)), 4)

        fee = self._get_fee(amount_usd, delivery_type)

        # Calculate destination amount with proper precision
        precision = corridor.get("currency_precision", 2)
        amount_dest = round(amount_usd * rate, precision)

        total_charge = round(amount_usd + fee, 2)

        delivery_config = DELIVERY_METHODS.get(delivery_type, {})
        eta = delivery_config.get("delivery_time", "24 hours")

        return {
            "quote_id": _random_id("qt"),
            "amount_usd": amount_usd,
            "amount_dest": amount_dest,
            "currency": corridor["currency"],
            "country": country,
            "rate": rate,
            "fee": fee,
            "total_charge": total_charge,
            "delivery_type": delivery_type,
            "eta": eta,
            "valid_until": (datetime.utcnow() + timedelta(minutes=15)).isoformat(),
        }

    # ==================== RECIPIENT TOOLS ====================

    def list_recipients(
        self,
        country: Optional[str] = None,
        user_id: str = "user_demo",
    ) -> dict:
        """List user's saved recipients."""
        recipients = self._recipients.get(user_id, [])

        if country:
            recipients = [r for r in recipients if r["country"] == country]

        formatted = []
        for r in recipients:
            country_name = CORRIDORS.get(r["country"], {}).get("name", "")
            default_method = next(
                (dm for dm in r.get("delivery_methods", []) if dm.get("is_default")),
                r.get("delivery_methods", [{}])[0] if r.get("delivery_methods") else {}
            )
            formatted.append({
                "id": r["id"],
                "name": r["name"]["display_name"],
                "country": r["country"],
                "country_name": country_name,
                "default_delivery_method": default_method.get("display_name", ""),
                "last_transfer": r.get("last_transfer_at"),
            })

        # Return raw data only - formatting handled by response template
        return {
            "recipients": formatted,
            "count": len(formatted)
        }

    def get_recipient(
        self,
        recipient_id: str,
        user_id: str = "user_demo",
    ) -> dict:
        """Get a specific recipient's details."""
        recipients = self._recipients.get(user_id, [])
        recipient = next((r for r in recipients if r["id"] == recipient_id), None)

        if not recipient:
            return {
                "error": "RECIPIENT_NOT_FOUND",
            }

        country_config = CORRIDORS.get(recipient["country"], {})

        return {
            "id": recipient["id"],
            "name": recipient["name"],
            "country": recipient["country"],
            "country_name": country_config.get("name", ""),
            "currency": country_config.get("currency", "USD"),
            "location": recipient.get("location"),
            "delivery_methods": recipient.get("delivery_methods", []),
            "created_at": recipient.get("created_at"),
            "last_transfer_at": recipient.get("last_transfer_at"),
        }

    def add_recipient(
        self,
        first_name: str,
        last_name: str,
        country: str,
        delivery_type: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        bank_name: Optional[str] = None,
        account_number: Optional[str] = None,
        clabe: Optional[str] = None,
        account_type: Optional[str] = None,
        card_number: Optional[str] = None,
        wallet_type: Optional[str] = None,
        phone_number: Optional[str] = None,
        middle_name: Optional[str] = None,
        user_id: str = "user_demo",
    ) -> dict:
        """Add a new recipient with delivery method."""
        corridor = CORRIDORS.get(country)
        if not corridor:
            return {
                "error": "COUNTRY_NOT_SUPPORTED",
            }

        if delivery_type not in corridor["delivery_methods"]:
            return {
                "error": "DELIVERY_METHOD_NOT_AVAILABLE",
            }

        # Build display name
        display_name = f"{first_name} {last_name}"
        if middle_name:
            display_name = f"{first_name} {middle_name} {last_name}"

        # Build delivery method
        dm_id = _random_id("dm")
        delivery_method = {
            "id": dm_id,
            "type": delivery_type,
            "is_default": True,
        }

        if delivery_type == "BANK":
            last4 = (clabe or account_number or "0000")[-4:]
            delivery_method["display_name"] = f"{bank_name or 'Bank'} ****{last4}"
            delivery_method["bank_name"] = bank_name
            delivery_method["account_last4"] = last4
            if clabe:
                delivery_method["clabe"] = clabe
            if account_type:
                delivery_method["account_type"] = account_type
        elif delivery_type == "DEBIT":
            last4 = (card_number or "0000")[-4:]
            delivery_method["display_name"] = f"Card ****{last4}"
            delivery_method["card_last4"] = last4
        elif delivery_type == "WALLET":
            last4 = (phone_number or "0000")[-4:]
            delivery_method["display_name"] = f"{wallet_type} ****{last4}"
            delivery_method["wallet_type"] = wallet_type
            delivery_method["phone_last4"] = last4
        elif delivery_type == "CASH":
            delivery_method["display_name"] = f"Cash - {city or 'Location TBD'}"

        # Create recipient
        recipient_id = _random_id("rec")
        recipient = {
            "id": recipient_id,
            "name": {
                "first_name": first_name,
                "middle_name": middle_name,
                "last_name": last_name,
                "display_name": display_name,
            },
            "country": country,
            "location": {"city": city, "state": state} if city else None,
            "delivery_methods": [delivery_method],
            "created_at": datetime.utcnow().isoformat(),
            "last_transfer_at": None,
        }

        # Store recipient
        if user_id not in self._recipients:
            self._recipients[user_id] = []
        self._recipients[user_id].append(recipient)

        return {
            "recipient_id": recipient_id,
            "name": display_name,
            "country": country,
            "country_name": corridor["name"],
            "delivery_method_id": dm_id,
            "delivery_method": delivery_method["display_name"],
        }

    def save_recipient(
        self,
        first_name: str,
        last_name: str,
        country: str,
        delivery_type: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        bank_name: Optional[str] = None,
        account_number: Optional[str] = None,
        clabe: Optional[str] = None,
        account_type: Optional[str] = None,
        card_number: Optional[str] = None,
        wallet_type: Optional[str] = None,
        phone_number: Optional[str] = None,
        middle_name: Optional[str] = None,
        user_id: str = "user_demo",
    ) -> dict:
        """Alias for add_recipient (used by flow)."""
        return self.add_recipient(
            first_name=first_name,
            last_name=last_name,
            country=country,
            delivery_type=delivery_type,
            city=city,
            state=state,
            bank_name=bank_name,
            account_number=account_number,
            clabe=clabe,
            account_type=account_type,
            card_number=card_number,
            wallet_type=wallet_type,
            phone_number=phone_number,
            middle_name=middle_name,
            user_id=user_id,
        )

    def add_delivery_method(
        self,
        recipient_id: str,
        delivery_type: str,
        bank_name: Optional[str] = None,
        account_number: Optional[str] = None,
        clabe: Optional[str] = None,
        account_type: Optional[str] = None,
        card_number: Optional[str] = None,
        wallet_type: Optional[str] = None,
        phone_number: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        user_id: str = "user_demo",
    ) -> dict:
        """Add a new delivery method to an existing recipient."""
        recipients = self._recipients.get(user_id, [])
        recipient = next((r for r in recipients if r["id"] == recipient_id), None)

        if not recipient:
            return {
                "error": "RECIPIENT_NOT_FOUND",
            }

        corridor = CORRIDORS.get(recipient["country"])
        if delivery_type not in corridor["delivery_methods"]:
            return {
                "error": "DELIVERY_METHOD_NOT_AVAILABLE",
            }

        # Build delivery method
        dm_id = _random_id("dm")
        delivery_method = {
            "id": dm_id,
            "type": delivery_type,
            "is_default": False,
        }

        if delivery_type == "BANK":
            last4 = (clabe or account_number or "0000")[-4:]
            delivery_method["display_name"] = f"{bank_name or 'Bank'} ****{last4}"
            delivery_method["bank_name"] = bank_name
            delivery_method["account_last4"] = last4
            if clabe:
                delivery_method["clabe"] = clabe
            if account_type:
                delivery_method["account_type"] = account_type
        elif delivery_type == "DEBIT":
            last4 = (card_number or "0000")[-4:]
            delivery_method["display_name"] = f"Card ****{last4}"
            delivery_method["card_last4"] = last4
        elif delivery_type == "WALLET":
            last4 = (phone_number or "0000")[-4:]
            delivery_method["display_name"] = f"{wallet_type} ****{last4}"
            delivery_method["wallet_type"] = wallet_type
            delivery_method["phone_last4"] = last4
        elif delivery_type == "CASH":
            delivery_method["display_name"] = f"Cash - {city or 'Location TBD'}"
            if city:
                recipient["location"] = {"city": city, "state": state}

        recipient["delivery_methods"].append(delivery_method)

        return {
            "delivery_method_id": dm_id,
            "delivery_method": delivery_method["display_name"],
            "recipient_id": recipient_id,
            "recipient_name": recipient["name"]["display_name"],
        }

    def save_delivery_method(
        self,
        recipient_id: str,
        delivery_type: str,
        bank_name: Optional[str] = None,
        account_number: Optional[str] = None,
        clabe: Optional[str] = None,
        account_type: Optional[str] = None,
        card_number: Optional[str] = None,
        wallet_type: Optional[str] = None,
        phone_number: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        user_id: str = "user_demo",
    ) -> dict:
        """Alias for add_delivery_method (used by flow)."""
        return self.add_delivery_method(
            recipient_id=recipient_id,
            delivery_type=delivery_type,
            bank_name=bank_name,
            account_number=account_number,
            clabe=clabe,
            account_type=account_type,
            card_number=card_number,
            wallet_type=wallet_type,
            phone_number=phone_number,
            city=city,
            state=state,
            user_id=user_id,
        )

    def delete_recipient(
        self,
        recipient_id: str,
        user_id: str = "user_demo",
    ) -> dict:
        """Delete a recipient (soft delete)."""
        recipients = self._recipients.get(user_id, [])
        recipient = next((r for r in recipients if r["id"] == recipient_id), None)

        if not recipient:
            return {
                "error": "RECIPIENT_NOT_FOUND",
            }

        # Remove from list
        self._recipients[user_id] = [r for r in recipients if r["id"] != recipient_id]

        return {
            "success": True,
            "recipient_id": recipient_id,
        }

    # ==================== DELIVERY METHOD TOOLS ====================

    def get_delivery_methods(
        self,
        country: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """Get available delivery methods for a country."""
        corridor = CORRIDORS.get(country)
        if not corridor:
            return {
                "error": "COUNTRY_NOT_SUPPORTED",
            }

        methods = []
        for method_type in corridor["delivery_methods"]:
            config = DELIVERY_METHODS.get(method_type, {})
            method = {
                "type": method_type,
                "name": config.get("name", ""),
                "delivery_time": config.get("delivery_time", ""),
                "requires_location": config.get("requires_location", False),
            }

            # Add wallet types if applicable
            if method_type == "WALLET" and country in WALLET_TYPES:
                method["wallet_types"] = WALLET_TYPES[country]

            # Add additional fee if applicable
            if config.get("additional_fee"):
                method["additional_fee"] = config["additional_fee"]

            methods.append(method)

        return {
            "country": country,
            "country_name": corridor["name"],
            "currency": corridor["currency"],
            "delivery_methods": methods,
        }

    # ==================== LIMITS TOOLS ====================

    def get_user_limits(
        self,
        user_id: str = "user_demo",
    ) -> dict:
        """Get user's KYC level and limits."""
        kyc_level = self._user_kyc.get(user_id, "KYC_LITE")
        limits_config = KYC_LIMITS.get(kyc_level, KYC_LIMITS["KYC_LITE"])
        usage = self._user_usage.get(user_id, {"daily": 0, "monthly": 0, "semiannual": 0})

        return {
            "kyc_level": kyc_level,
            "kyc_level_name": limits_config["display_name"],
            "limits": {
                "per_transaction": limits_config["per_transaction"],
                "daily": {
                    "limit": limits_config["daily"],
                    "used": usage.get("daily", 0),
                    "available": max(0, limits_config["daily"] - usage.get("daily", 0)),
                },
                "monthly": {
                    "limit": limits_config["monthly"],
                    "used": usage.get("monthly", 0),
                    "available": max(0, limits_config["monthly"] - usage.get("monthly", 0)),
                },
                "semiannual": {
                    "limit": limits_config["semiannual"],
                    "used": usage.get("semiannual", 0),
                    "available": max(0, limits_config["semiannual"] - usage.get("semiannual", 0)),
                },
            },
            "can_upgrade": kyc_level != "SENDER_KYC_L3",
        }

    # ==================== TRANSFER TOOLS ====================

    def create_transfer(
        self,
        recipient_id: str,
        amount_usd: float,
        delivery_method_id: Optional[str] = None,
        payment_method_id: str = "pm_default",
        user_id: str = "user_demo",
    ) -> dict:
        """Create and execute a remittance transfer."""
        # Get recipient
        recipients = self._recipients.get(user_id, [])
        recipient = next((r for r in recipients if r["id"] == recipient_id), None)

        if not recipient:
            return {
                "error": "RECIPIENT_NOT_FOUND",
            }

        # Get delivery method
        if delivery_method_id:
            delivery_method = next(
                (dm for dm in recipient.get("delivery_methods", []) if dm["id"] == delivery_method_id),
                None
            )
        else:
            delivery_method = next(
                (dm for dm in recipient.get("delivery_methods", []) if dm.get("is_default")),
                recipient.get("delivery_methods", [{}])[0] if recipient.get("delivery_methods") else None
            )

        if not delivery_method:
            return {
                "error": "DELIVERY_METHOD_NOT_FOUND",
            }

        # Check limits
        limits = self.get_user_limits(user_id)
        if amount_usd > limits["limits"]["daily"]["available"]:
            return {
                "error": "LIMIT_EXCEEDED",
                "limit_type": "daily",
                "available": limits["limits"]["daily"]["available"],
                "requested": amount_usd,
            }

        # Create quote
        quote = self.create_quote(
            amount_usd=amount_usd,
            country=recipient["country"],
            delivery_type=delivery_method["type"],
            user_id=user_id,
        )

        # Create transfer
        transfer_id = f"TXN{_random_string(8)}"
        transfer = {
            "id": transfer_id,
            "recipient_id": recipient_id,
            "recipient_name": recipient["name"]["display_name"],
            "country": recipient["country"],
            "amount_usd": amount_usd,
            "amount_dest": quote["amount_dest"],
            "currency": quote["currency"],
            "rate": quote["rate"],
            "fee": quote["fee"],
            "total_charged": quote["total_charge"],
            "delivery_method_id": delivery_method["id"],
            "delivery_method_type": delivery_method["type"],
            "delivery_method_display": delivery_method["display_name"],
            "eta": quote["eta"],
            "status": "PROCESSING",
            "payment_method": payment_method_id,
            "created_at": datetime.utcnow().isoformat(),
        }

        self._transfers[transfer_id] = transfer

        # Update usage
        if user_id not in self._user_usage:
            self._user_usage[user_id] = {"daily": 0, "monthly": 0, "semiannual": 0}
        self._user_usage[user_id]["daily"] += amount_usd
        self._user_usage[user_id]["monthly"] += amount_usd
        self._user_usage[user_id]["semiannual"] += amount_usd

        # Update recipient last_transfer_at
        recipient["last_transfer_at"] = transfer["created_at"]

        # Add to recent transfers
        if user_id not in self._recent_transfers:
            self._recent_transfers[user_id] = []
        self._recent_transfers[user_id].insert(0, transfer.copy())

        return {
            "transfer_id": transfer_id,
            "recipient_name": recipient["name"]["display_name"],
            "amount_usd": amount_usd,
            "amount_dest": quote["amount_dest"],
            "currency": quote["currency"],
            "rate": quote["rate"],
            "fee": quote["fee"],
            "total_charged": quote["total_charge"],
            "delivery_method": delivery_method["display_name"],
            "eta": quote["eta"],
            "status": "PROCESSING",
            "transaction_id": transfer_id,
            "reference": transfer_id,
            "amount": amount_usd,
            "source_currency": "USD",
            "timestamp": transfer["created_at"],
        }

    def get_transfer_status(
        self,
        transfer_id: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """Get status of a specific transfer."""
        transfer = self._transfers.get(transfer_id)

        if not transfer:
            # Check recent transfers
            for user_transfers in self._recent_transfers.values():
                transfer = next((t for t in user_transfers if t["id"] == transfer_id), None)
                if transfer:
                    break

        if not transfer:
            return {
                "error": "TRANSFER_NOT_FOUND",
            }

        status_config = TRANSFER_STATES.get(transfer["status"], {})

        return {
            "transfer_id": transfer_id,
            "status": transfer["status"],
            "status_display": status_config.get("display", ""),
            "recipient_name": transfer.get("recipient_name"),
            "amount_usd": transfer.get("amount_usd"),
            "amount_dest": transfer.get("amount_dest"),
            "currency": transfer.get("currency"),
            "delivery_method": transfer.get("delivery_method_display"),
            "eta": transfer.get("eta"),
            "can_cancel": status_config.get("cancellable", False),
            "created_at": transfer.get("created_at"),
        }

    def list_transfers(
        self,
        limit: int = 5,
        status: Optional[str] = None,
        user_id: str = "user_demo",
    ) -> dict:
        """Get user's recent transfers."""
        transfers = self._recent_transfers.get(user_id, [])

        if status:
            transfers = [t for t in transfers if t["status"] == status]

        transfers = transfers[:limit]

        formatted = []
        for t in transfers:
            status_config = TRANSFER_STATES.get(t["status"], {})
            formatted.append({
                "id": t["id"],
                "recipient_name": t.get("recipient_name"),
                "amount_usd": t.get("amount_usd"),
                "amount_dest": t.get("amount_dest"),
                "currency": t.get("currency"),
                "status": t["status"],
                "status_display": status_config.get("display", ""),
                "created_at": t.get("created_at"),
            })

        return {
            "transfers": formatted,
            "count": len(formatted),
        }

    def cancel_transfer(
        self,
        transfer_id: str,
        user_id: str = "user_demo",
    ) -> dict:
        """Cancel a pending transfer."""
        transfer = self._transfers.get(transfer_id)

        if not transfer:
            return {
                "error": "TRANSFER_NOT_FOUND",
            }

        status_config = TRANSFER_STATES.get(transfer["status"], {})

        if not status_config.get("cancellable", False):
            reason = "ya está en progreso" if transfer["status"] == "IN_PROGRESS" else "ya fue completado"
            return {
                "error": "NOT_CANCELLABLE",
                "status": transfer["status"],
            }

        # Cancel the transfer
        transfer["status"] = "CANCELLED"
        transfer["cancelled_at"] = datetime.utcnow().isoformat()

        # Refund usage
        if user_id in self._user_usage:
            amount = transfer.get("amount_usd", 0)
            self._user_usage[user_id]["daily"] = max(0, self._user_usage[user_id]["daily"] - amount)
            self._user_usage[user_id]["monthly"] = max(0, self._user_usage[user_id]["monthly"] - amount)
            self._user_usage[user_id]["semiannual"] = max(0, self._user_usage[user_id]["semiannual"] - amount)

        return {
            "success": True,
            "transfer_id": transfer_id,
            "amount_usd": transfer.get("amount_usd"),
            "refund_eta": "3-5 business days",
            "status": "CANCELLED",
            "transaction_id": transfer_id,
            "reference": transfer_id,
            "amount": transfer.get("amount_usd"),
            "currency": "USD",
            "timestamp": transfer.get("cancelled_at"),
        }

    def create_snpl_transfer(
        self,
        snpl_loan_id: str,
        recipient_id: str,
        amount_usd: float,
        delivery_method_id: Optional[str] = None,
        user_id: str = "user_demo",
    ) -> dict:
        """Create a remittance transfer funded by SNPL credit.

        This is similar to create_transfer but:
        - Payment method is 'SNPL Credit'
        - No additional fees (already included in SNPL loan)
        - Links transfer to the SNPL loan ID
        """
        # Get recipient
        recipients = self._recipients.get(user_id, [])
        recipient = next((r for r in recipients if r["id"] == recipient_id), None)

        if not recipient:
            return {
                "error": "RECIPIENT_NOT_FOUND",
            }

        # Get delivery method
        if delivery_method_id:
            delivery_method = next(
                (dm for dm in recipient.get("delivery_methods", []) if dm["id"] == delivery_method_id),
                None
            )
        else:
            delivery_method = next(
                (dm for dm in recipient.get("delivery_methods", []) if dm.get("is_default")),
                recipient.get("delivery_methods", [{}])[0] if recipient.get("delivery_methods") else None
            )

        if not delivery_method:
            return {
                "error": "DELIVERY_METHOD_NOT_FOUND",
            }

        # Get corridor info for exchange rate
        corridor = CORRIDORS.get(recipient["country"], CORRIDORS["MX"])
        rate = corridor["typical_rate"]
        rate = round(rate * (1 + random.uniform(-0.005, 0.005)), 4)

        # Calculate destination amount
        precision = corridor.get("currency_precision", 2)
        amount_dest = round(amount_usd * rate, precision)

        # Get delivery time
        delivery_config = DELIVERY_METHODS.get(delivery_method["type"], {})
        eta = delivery_config.get("delivery_time", "24 hours")

        # Create transfer
        transfer_id = f"TXN{_random_string(8)}"
        transfer = {
            "id": transfer_id,
            "recipient_id": recipient_id,
            "recipient_name": recipient["name"]["display_name"],
            "country": recipient["country"],
            "amount_usd": amount_usd,
            "amount_dest": amount_dest,
            "currency": corridor["currency"],
            "rate": rate,
            "fee": 0,  # No fee for SNPL transfers (included in loan)
            "total_charged": amount_usd,  # Just the principal amount
            "delivery_method_id": delivery_method["id"],
            "delivery_method_type": delivery_method["type"],
            "delivery_method_display": delivery_method["display_name"],
            "eta": eta,
            "status": "PROCESSING",
            "payment_method": f"SNPL Credit ({snpl_loan_id})",
            "snpl_loan_id": snpl_loan_id,
            "created_at": datetime.utcnow().isoformat(),
        }

        self._transfers[transfer_id] = transfer

        # Update usage (SNPL transfers still count toward limits)
        if user_id not in self._user_usage:
            self._user_usage[user_id] = {"daily": 0, "monthly": 0, "semiannual": 0}
        self._user_usage[user_id]["daily"] += amount_usd
        self._user_usage[user_id]["monthly"] += amount_usd
        self._user_usage[user_id]["semiannual"] += amount_usd

        # Update recipient last_transfer_at
        recipient["last_transfer_at"] = transfer["created_at"]

        # Add to recent transfers
        if user_id not in self._recent_transfers:
            self._recent_transfers[user_id] = []
        self._recent_transfers[user_id].insert(0, transfer.copy())

        return {
            "transfer_id": transfer_id,
            "recipient_name": recipient["name"]["display_name"],
            "amount_usd": amount_usd,
            "amount_dest": amount_dest,
            "currency": corridor["currency"],
            "rate": rate,
            "fee": 0,
            "total_charged": amount_usd,
            "delivery_method": delivery_method["display_name"],
            "eta": eta,
            "status": "PROCESSING",
            "snpl_loan_id": snpl_loan_id,
            "transaction_id": transfer_id,
            "reference": transfer_id,
            "amount": amount_usd,
            "source_currency": "USD",
            "timestamp": transfer["created_at"],
        }

    # ==================== QUICK SEND TOOLS ====================

    def get_quick_send_options(
        self,
        user_id: str = "user_demo",
        limit: int = 5,
    ) -> dict:
        """Get recent transfers that can be quickly repeated."""
        transfers = self._recent_transfers.get(user_id, [])

        # Filter to completed transfers only
        completed = [t for t in transfers if t["status"] == "COMPLETED"][:limit]

        options = []
        for t in completed:
            options.append({
                "id": t["id"],
                "recipient_id": t.get("recipient_id"),
                "recipient_name": t.get("recipient_name"),
                "country": t.get("country"),
                "amount_usd": t.get("amount_usd"),
                "amount_dest": t.get("amount_dest"),
                "currency": t.get("currency"),
                "delivery_method_id": t.get("delivery_method_id"),
                "delivery_method_display": t.get("delivery_method_display"),
                "created_at": t.get("created_at"),
            })

        return {
            "options": options,
            "count": len(options),
        }

    # ==================== LEGACY COMPATIBILITY ====================

    def get_recipients(self, user_id: str = "user_demo") -> list:
        """Legacy method - returns just the list for backward compatibility."""
        result = self.list_recipients(user_id=user_id)
        return result.get("recipients", [])

    def calculate_transfer(
        self,
        amount_usd: float,
        to_currency: str = "MXN",
        user_id: Optional[str] = None,
    ) -> dict:
        """Legacy method - maps to create_quote."""
        # Find country by currency
        country = "MX"
        for code, config in CORRIDORS.items():
            if config["currency"] == to_currency:
                country = code
                break

        return self.create_quote(
            amount_usd=amount_usd,
            country=country,
            user_id=user_id,
        )

    def get_recent_transfers(
        self,
        user_id: str = "user_demo",
        limit: int = 5,
    ) -> list:
        """Legacy method - returns just the list for backward compatibility."""
        result = self.list_transfers(user_id=user_id, limit=limit)
        return result.get("transfers", [])
