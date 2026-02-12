"""Mock Send Now Pay Later (SNPL) service for Felix."""

import random
import string
from datetime import datetime, timedelta
from typing import Optional


# Eligibility tiers based on user history/KYC
ELIGIBILITY_TIERS = {
    "new_user": {
        "min": 200,
        "max": 300,
        "base_apr": 35.99
    },
    "good_standing": {
        "min": 200,
        "max": 600,
        "base_apr": 29.99
    },
    "excellent": {
        "min": 200,
        "max": 1000,
        "base_apr": 24.99
    },
    "not_eligible": {
        "min": 0,
        "max": 0,
        "base_apr": 0
    }
}

# Available term options (weeks)
TERM_OPTIONS = [4, 8, 12, 16, 20, 26]


def _generate_loan_id() -> str:
    """Generate a unique loan ID."""
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=6))
    return f"SNPL-{suffix}"


def _generate_payment_id() -> str:
    """Generate a unique payment ID."""
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=8))
    return f"PAY-{suffix}"


class MockSNPLService:
    """Mock service for Send Now Pay Later functionality."""

    def __init__(self, language: str = "es"):
        self.language = language
        self._init_demo_data()

    def _init_demo_data(self):
        """Initialize demo data for user_demo."""
        # User eligibility mapping
        self._user_eligibility = {
            "user_demo": "good_standing",
            "user_new": "new_user",
            "user_premium": "excellent",
            "user_blocked": "not_eligible"
        }

        # Active and historical loans
        self._loans = {
            "user_demo": [
                {
                    "loan_id": "SNPL-DEMO01",
                    "user_id": "user_demo",
                    "status": "ACTIVE",
                    "amount": 500.00,
                    "term_weeks": 12,
                    "apr": 29.99,
                    "weekly_payment": 46.25,
                    "total_repayment": 555.00,
                    "total_interest": 55.00,
                    "balance_remaining": 277.50,
                    "payments_made": 6,
                    "payments_remaining": 6,
                    "created_at": "2025-12-01T10:00:00Z",
                    "first_payment_date": "2025-12-08",
                    "next_payment_date": "2026-01-19",
                    "next_payment_amount": 46.25,
                    "final_payment_date": "2026-02-23",
                    "remittance": {
                        "transfer_id": "TXN-ABC789",
                        "recipient_name": "María García",
                        "amount_usd": 500.00,
                        "country": "MX"
                    }
                },
                {
                    "loan_id": "SNPL-DEMO02",
                    "user_id": "user_demo",
                    "status": "PAID_OFF",
                    "amount": 300.00,
                    "term_weeks": 8,
                    "apr": 29.99,
                    "weekly_payment": 40.38,
                    "total_repayment": 323.00,
                    "total_interest": 23.00,
                    "balance_remaining": 0.00,
                    "payments_made": 8,
                    "payments_remaining": 0,
                    "created_at": "2025-09-01T10:00:00Z",
                    "first_payment_date": "2025-09-08",
                    "next_payment_date": None,
                    "next_payment_amount": 0,
                    "final_payment_date": "2025-10-27",
                    "paid_off_date": "2025-10-27",
                    "remittance": {
                        "transfer_id": "TXN-XYZ456",
                        "recipient_name": "Carlos López",
                        "amount_usd": 300.00,
                        "country": "GT"
                    }
                }
            ]
        }

        # Payment history
        self._payments = {
            "SNPL-DEMO01": [
                {"payment_id": "PAY-D01P001", "amount": 46.25, "date": "2025-12-08", "status": "COMPLETED"},
                {"payment_id": "PAY-D01P002", "amount": 46.25, "date": "2025-12-15", "status": "COMPLETED"},
                {"payment_id": "PAY-D01P003", "amount": 46.25, "date": "2025-12-22", "status": "COMPLETED"},
                {"payment_id": "PAY-D01P004", "amount": 46.25, "date": "2025-12-29", "status": "COMPLETED"},
                {"payment_id": "PAY-D01P005", "amount": 46.25, "date": "2026-01-05", "status": "COMPLETED"},
                {"payment_id": "PAY-D01P006", "amount": 46.25, "date": "2026-01-12", "status": "COMPLETED"},
            ],
            "SNPL-DEMO02": [
                {"payment_id": "PAY-D02P001", "amount": 40.38, "date": "2025-09-08", "status": "COMPLETED"},
                {"payment_id": "PAY-D02P002", "amount": 40.38, "date": "2025-09-15", "status": "COMPLETED"},
                {"payment_id": "PAY-D02P003", "amount": 40.38, "date": "2025-09-22", "status": "COMPLETED"},
                {"payment_id": "PAY-D02P004", "amount": 40.38, "date": "2025-09-29", "status": "COMPLETED"},
                {"payment_id": "PAY-D02P005", "amount": 40.38, "date": "2025-10-06", "status": "COMPLETED"},
                {"payment_id": "PAY-D02P006", "amount": 40.38, "date": "2025-10-13", "status": "COMPLETED"},
                {"payment_id": "PAY-D02P007", "amount": 40.38, "date": "2025-10-20", "status": "COMPLETED"},
                {"payment_id": "PAY-D02P008", "amount": 40.38, "date": "2025-10-27", "status": "COMPLETED"},
            ]
        }

    # ==================== ELIGIBILITY ====================

    def get_snpl_eligibility(self, user_id: str = "user_demo") -> dict:
        """Check user's SNPL eligibility and pre-approved amount."""
        tier_key = self._user_eligibility.get(user_id, "new_user")
        tier = ELIGIBILITY_TIERS[tier_key]

        if tier_key == "not_eligible":
            return {
                "eligible": False,
                "tier": tier_key,
                "reason": "insufficient_payment_history"
            }

        return {
            "eligible": True,
            "tier": tier_key,
            "min_amount": tier["min"],
            "max_amount": tier["max"],
            "base_apr": tier["base_apr"],
            "term_options": TERM_OPTIONS
        }

    # ==================== TERMS CALCULATION ====================

    def calculate_terms(self, amount: float, weeks: int, user_id: str = "user_demo") -> dict:
        """Calculate loan terms for given amount and duration."""
        # Validate amount
        if amount < 200 or amount > 1000:
            return {
                "error": "INVALID_AMOUNT"
            }

        # Validate weeks
        if weeks not in TERM_OPTIONS:
            return {
                "error": "INVALID_TERM"
            }

        # Get user's APR based on tier
        tier_key = self._user_eligibility.get(user_id, "new_user")
        tier = ELIGIBILITY_TIERS.get(tier_key, ELIGIBILITY_TIERS["new_user"])
        base_apr = tier["base_apr"]

        # Simple interest calculation
        period_rate = base_apr / 100 * (weeks / 52)
        total_interest = amount * period_rate
        total_repayment = amount + total_interest
        weekly_payment = total_repayment / weeks

        # Calculate first payment date (next week from today)
        first_payment = datetime.now() + timedelta(days=7)
        final_payment = first_payment + timedelta(weeks=weeks - 1)

        return {
            "amount": amount,
            "term_weeks": weeks,
            "apr": base_apr,
            "weekly_payment": round(weekly_payment, 2),
            "total_interest": round(total_interest, 2),
            "total_repayment": round(total_repayment, 2),
            "first_payment_date": first_payment.strftime("%Y-%m-%d"),
            "final_payment_date": final_payment.strftime("%Y-%m-%d")
        }

    # ==================== APPLICATION ====================

    def submit_snpl_application(self, amount: float, term_weeks: int, user_id: str = "user_demo") -> dict:
        """Submit SNPL application and get instant decision."""
        # Check eligibility first
        eligibility = self.get_snpl_eligibility(user_id)
        if not eligibility.get("eligible"):
            return {
                "approved": False,
                "error": "NOT_ELIGIBLE",
                "reason": eligibility.get("reason", "not_eligible")
            }

        # Check amount against eligibility
        if amount > eligibility["max_amount"]:
            return {
                "approved": False,
                "error": "AMOUNT_EXCEEDS_LIMIT",
                "max_amount": eligibility["max_amount"]
            }

        if amount < eligibility["min_amount"]:
            return {
                "approved": False,
                "error": "AMOUNT_BELOW_MINIMUM",
                "min_amount": eligibility["min_amount"]
            }

        # Calculate terms
        terms = self.calculate_terms(amount, term_weeks, user_id)
        if "error" in terms:
            return {
                "approved": False,
                "error": terms["error"]
            }

        # Simulate approval (95% success rate)
        if random.random() < 0.05:
            return {
                "approved": False,
                "error": "APPLICATION_DENIED"
            }

        # Create new loan
        loan_id = _generate_loan_id()
        now = datetime.now()
        first_payment = now + timedelta(days=7)
        final_payment = first_payment + timedelta(weeks=term_weeks - 1)

        new_loan = {
            "loan_id": loan_id,
            "user_id": user_id,
            "status": "ACTIVE",
            "amount": amount,
            "term_weeks": term_weeks,
            "apr": terms["apr"],
            "weekly_payment": terms["weekly_payment"],
            "total_repayment": terms["total_repayment"],
            "total_interest": terms["total_interest"],
            "balance_remaining": terms["total_repayment"],
            "payments_made": 0,
            "payments_remaining": term_weeks,
            "created_at": now.isoformat(),
            "first_payment_date": first_payment.strftime("%Y-%m-%d"),
            "next_payment_date": first_payment.strftime("%Y-%m-%d"),
            "next_payment_amount": terms["weekly_payment"],
            "final_payment_date": final_payment.strftime("%Y-%m-%d"),
            "remittance": None  # Will be set when used for remittance
        }

        # Store the loan
        if user_id not in self._loans:
            self._loans[user_id] = []
        self._loans[user_id].append(new_loan)

        # Initialize payment history
        self._payments[loan_id] = []

        return {
            "approved": True,
            "loan_id": loan_id,
            "amount": amount,
            "term_weeks": term_weeks,
            "apr": terms["apr"],
            "weekly_payment": terms["weekly_payment"],
            "total_repayment": terms["total_repayment"],
            "first_payment_date": first_payment.strftime("%Y-%m-%d"),
            "final_payment_date": final_payment.strftime("%Y-%m-%d"),
            "status": "approved",
            "transaction_id": loan_id,
            "reference": loan_id,
            "currency": "USD",
            "timestamp": now.isoformat(),
        }

    # ==================== LOAN OVERVIEW & DETAILS ====================

    def get_snpl_overview(self, user_id: str = "user_demo") -> dict:
        """Get overview of user's SNPL status."""
        user_loans = self._loans.get(user_id, [])
        active_loans = [l for l in user_loans if l["status"] == "ACTIVE"]

        if not active_loans:
            return {
                "active_count": 0,
                "total_balance": 0,
                "has_loans": len(user_loans) > 0
            }

        total_balance = sum(l["balance_remaining"] for l in active_loans)

        # Find next payment
        next_payment_loan = min(active_loans, key=lambda l: l["next_payment_date"])
        next_payment_date = next_payment_loan["next_payment_date"]
        next_payment_amount = next_payment_loan["next_payment_amount"]

        return {
            "active_count": len(active_loans),
            "total_balance": round(total_balance, 2),
            "next_payment_date": next_payment_date,
            "next_payment_amount": next_payment_amount,
            "loans": [
                {
                    "loan_id": l["loan_id"],
                    "amount": l["amount"],
                    "balance_remaining": l["balance_remaining"],
                    "next_payment_date": l["next_payment_date"]
                }
                for l in active_loans
            ]
        }

    def get_loan_details(self, loan_id: str, user_id: str = "user_demo") -> dict:
        """Get full details of a specific loan."""
        user_loans = self._loans.get(user_id, [])
        loan = next((l for l in user_loans if l["loan_id"] == loan_id), None)

        if not loan:
            return {
                "error": "LOAN_NOT_FOUND"
            }

        return {
            **loan
        }

    def list_loans(self, user_id: str = "user_demo", status: Optional[str] = None) -> dict:
        """List all loans for a user, optionally filtered by status."""
        user_loans = self._loans.get(user_id, [])

        if status:
            user_loans = [l for l in user_loans if l["status"] == status.upper()]

        loans_summary = []
        for loan in user_loans:
            loans_summary.append({
                "loan_id": loan["loan_id"],
                "amount": loan["amount"],
                "balance_remaining": loan["balance_remaining"],
                "status": loan["status"],
                "created_at": loan["created_at"],
                "recipient_name": loan["remittance"]["recipient_name"] if loan.get("remittance") else None
            })

        if not loans_summary:
            return {
                "loans": [],
                "count": 0
            }

        return {
            "loans": loans_summary,
            "count": len(loans_summary)
        }

    # ==================== PAYMENT SCHEDULE & HISTORY ====================

    def get_payment_schedule(self, loan_id: str, user_id: str = "user_demo") -> dict:
        """Get payment schedule for a loan."""
        user_loans = self._loans.get(user_id, [])
        loan = next((l for l in user_loans if l["loan_id"] == loan_id), None)

        if not loan:
            return {
                "error": "LOAN_NOT_FOUND"
            }

        # Generate schedule
        schedule = []
        completed_payments = self._payments.get(loan_id, [])
        completed_count = len(completed_payments)

        # Parse first payment date
        first_payment = datetime.strptime(loan["first_payment_date"], "%Y-%m-%d")

        for i in range(loan["term_weeks"]):
            payment_date = first_payment + timedelta(weeks=i)
            if i < completed_count:
                status = "COMPLETED"
            elif i == completed_count:
                status = "PENDING"
            else:
                status = "SCHEDULED"

            schedule.append({
                "payment_number": i + 1,
                "date": payment_date.strftime("%Y-%m-%d"),
                "amount": loan["weekly_payment"],
                "status": status
            })

        return {
            "loan_id": loan_id,
            "schedule": schedule,
            "total_payments": loan["term_weeks"],
            "completed_payments": completed_count,
            "remaining_payments": loan["payments_remaining"]
        }

    def get_payment_history(self, loan_id: Optional[str] = None, user_id: str = "user_demo", limit: int = 10) -> dict:
        """Get payment history for a loan or all loans."""
        all_payments = []

        if loan_id:
            # Verify loan belongs to user
            user_loans = self._loans.get(user_id, [])
            loan = next((l for l in user_loans if l["loan_id"] == loan_id), None)
            if not loan:
                return {
                    "error": "LOAN_NOT_FOUND"
                }
            payments = self._payments.get(loan_id, [])
            all_payments = [{"loan_id": loan_id, **p} for p in payments]
        else:
            # Get payments from all user's loans
            user_loans = self._loans.get(user_id, [])
            for loan in user_loans:
                payments = self._payments.get(loan["loan_id"], [])
                all_payments.extend([{"loan_id": loan["loan_id"], **p} for p in payments])

        # Sort by date descending and limit
        all_payments.sort(key=lambda p: p["date"], reverse=True)
        all_payments = all_payments[:limit]

        if not all_payments:
            return {
                "payments": [],
                "count": 0
            }

        return {
            "payments": all_payments,
            "count": len(all_payments)
        }

    # ==================== MAKE PAYMENT ====================

    def make_snpl_payment(
        self,
        loan_id: str,
        amount: float,
        payment_method_id: Optional[str] = None,
        user_id: str = "user_demo"
    ) -> dict:
        """Make a payment on an SNPL loan."""
        user_loans = self._loans.get(user_id, [])
        loan_idx = next((i for i, l in enumerate(user_loans) if l["loan_id"] == loan_id), None)

        if loan_idx is None:
            return {
                "error": "LOAN_NOT_FOUND"
            }

        loan = user_loans[loan_idx]

        if loan["status"] != "ACTIVE":
            return {
                "error": "LOAN_NOT_ACTIVE"
            }

        if amount <= 0:
            return {
                "error": "INVALID_AMOUNT"
            }

        if amount > loan["balance_remaining"]:
            return {
                "error": "AMOUNT_EXCEEDS_BALANCE"
            }

        # Process payment
        payment_id = _generate_payment_id()
        now = datetime.now()

        new_balance = round(loan["balance_remaining"] - amount, 2)

        # Determine how many payments this covers
        payments_covered = int(amount / loan["weekly_payment"])
        if payments_covered < 1:
            payments_covered = 1  # At least one payment

        # Update loan
        loan["balance_remaining"] = new_balance
        loan["payments_made"] += payments_covered
        loan["payments_remaining"] = max(0, loan["payments_remaining"] - payments_covered)

        # Check if loan is paid off
        if new_balance <= 0:
            loan["status"] = "PAID_OFF"
            loan["balance_remaining"] = 0
            loan["next_payment_date"] = None
            loan["next_payment_amount"] = 0
            loan["paid_off_date"] = now.strftime("%Y-%m-%d")
        else:
            # Update next payment date
            next_payment = datetime.strptime(loan["next_payment_date"], "%Y-%m-%d") + timedelta(weeks=payments_covered)
            loan["next_payment_date"] = next_payment.strftime("%Y-%m-%d")

        # Record payment
        payment_record = {
            "payment_id": payment_id,
            "amount": amount,
            "date": now.strftime("%Y-%m-%d"),
            "status": "COMPLETED"
        }
        if loan_id not in self._payments:
            self._payments[loan_id] = []
        self._payments[loan_id].append(payment_record)

        return {
            "success": True,
            "payment_id": payment_id,
            "amount_paid": amount,
            "loan_id": loan_id,
            "new_balance": new_balance,
            "loan_status": loan["status"],
            "payments_remaining": loan["payments_remaining"],
            "status": "completed",
            "transaction_id": payment_id,
            "reference": payment_id,
            "amount": amount,
            "currency": "USD",
            "timestamp": now.isoformat(),
        }

    # ==================== USE FOR REMITTANCE ====================

    def use_credit_for_remittance(
        self,
        loan_id: str,
        transfer_id: str,
        recipient_name: str,
        amount_usd: float,
        country: str,
        user_id: str = "user_demo"
    ) -> dict:
        """Link an SNPL loan to a remittance transfer."""
        user_loans = self._loans.get(user_id, [])
        loan_idx = next((i for i, l in enumerate(user_loans) if l["loan_id"] == loan_id), None)

        if loan_idx is None:
            return {
                "error": "LOAN_NOT_FOUND"
            }

        loan = user_loans[loan_idx]

        if loan.get("remittance"):
            return {
                "error": "LOAN_ALREADY_USED"
            }

        # Link remittance to loan
        loan["remittance"] = {
            "transfer_id": transfer_id,
            "recipient_name": recipient_name,
            "amount_usd": amount_usd,
            "country": country
        }

        return {
            "success": True,
            "loan_id": loan_id,
            "transfer_id": transfer_id,
            "status": "linked",
            "transaction_id": transfer_id,
            "reference": transfer_id,
            "amount": amount_usd,
            "currency": "USD",
            "timestamp": datetime.now().isoformat(),
        }

    # ==================== ALIAS METHODS (for tool name matching) ====================

    def get_eligibility(self, user_id: str = "user_demo") -> dict:
        """Alias for get_snpl_eligibility."""
        return self.get_snpl_eligibility(user_id)

    def get_overview(self, user_id: str = "user_demo") -> dict:
        """Alias for get_snpl_overview."""
        return self.get_snpl_overview(user_id)

    def apply_for_snpl(self, amount: float, term_weeks: int, user_id: str = "user_demo") -> dict:
        """Alias for submit_snpl_application."""
        return self.submit_snpl_application(amount, term_weeks, user_id)

    def make_payment(self, loan_id: str, amount: float, payment_method_id: Optional[str] = None, user_id: str = "user_demo") -> dict:
        """Alias for make_snpl_payment."""
        return self.make_snpl_payment(loan_id, amount, payment_method_id, user_id)
