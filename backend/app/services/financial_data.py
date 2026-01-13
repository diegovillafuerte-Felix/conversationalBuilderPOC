"""
Financial Data Service - Mock service for external financial data
used by the financial advisor shadow subagent.
"""
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


class FinancialDataService:
    """Service for external financial data (rates, patterns, tips)."""

    def __init__(self):
        # Mock exchange rate data
        self._rate_history = self._generate_rate_history()

    def _generate_rate_history(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate mock rate history for common corridors."""
        corridors = ["USD_MXN", "USD_GTM", "USD_HND", "USD_COL"]
        history = {}

        for corridor in corridors:
            base_rate = {
                "USD_MXN": 17.5,
                "USD_GTM": 7.8,
                "USD_HND": 24.6,
                "USD_COL": 4000,
            }.get(corridor, 1.0)

            rates = []
            for i in range(30):
                date = datetime.now() - timedelta(days=29 - i)
                # Add some randomness
                rate = base_rate * (1 + random.uniform(-0.02, 0.02))
                rates.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "rate": round(rate, 4),
                })
            history[corridor] = rates

        return history

    def get_user_financial_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of user's financial activity.

        Returns mock data for development.
        """
        # In production, this would query the database
        return {
            "user_id": user_id,
            "wallet_balance": round(random.uniform(50, 500), 2),
            "total_sent_30_days": round(random.uniform(200, 2000), 2),
            "transaction_count_30_days": random.randint(1, 10),
            "avg_transfer_amount": round(random.uniform(100, 400), 2),
            "most_used_corridor": "USD_MXN",
            "preferred_delivery_method": "bank_deposit",
            "kyc_level": random.choice([1, 2, 3]),
            "remaining_monthly_limit": round(random.uniform(500, 5000), 2),
            "loyalty_points": random.randint(0, 1000),
        }

    def get_rate_trends(self, corridor: str, days: int = 30) -> Dict[str, Any]:
        """
        Get exchange rate trends for a corridor.

        Args:
            corridor: Currency pair (e.g., "USD_MXN")
            days: Number of days of history

        Returns:
            Rate trend analysis
        """
        history = self._rate_history.get(corridor, [])
        if not history:
            return {"error": f"Unknown corridor: {corridor}"}

        recent = history[-min(days, len(history)):]
        rates = [r["rate"] for r in recent]

        return {
            "corridor": corridor,
            "current_rate": rates[-1] if rates else 0,
            "avg_rate": sum(rates) / len(rates) if rates else 0,
            "min_rate": min(rates) if rates else 0,
            "max_rate": max(rates) if rates else 0,
            "trend": "up" if rates[-1] > rates[0] else "down" if rates[-1] < rates[0] else "stable",
            "percent_change": ((rates[-1] - rates[0]) / rates[0] * 100) if rates and rates[0] else 0,
            "history": recent,
        }

    def get_fee_optimization_tips(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get personalized fee optimization tips based on user's transaction patterns.

        Returns mock tips for development.
        """
        tips = [
            {
                "id": "recurring_transfers",
                "priority": "high",
                "potential_savings": 12.00,
                "title": {
                    "en": "Set up recurring transfers",
                    "es": "Configura transferencias recurrentes",
                },
                "description": {
                    "en": "Based on your transfer pattern, you could save $12/month by setting up weekly recurring transfers instead of multiple individual ones.",
                    "es": "Basado en tu patron de transferencias, podrias ahorrar $12/mes configurando transferencias semanales recurrentes.",
                },
            },
            {
                "id": "wallet_funding",
                "priority": "medium",
                "potential_savings": 5.00,
                "title": {
                    "en": "Pre-fund your wallet",
                    "es": "Pre-carga tu billetera",
                },
                "description": {
                    "en": "Loading your wallet via bank transfer is free. Debit card deposits have a small fee.",
                    "es": "Cargar tu billetera via transferencia bancaria es gratis. Los depositos con tarjeta tienen una pequena comision.",
                },
            },
            {
                "id": "delivery_method",
                "priority": "low",
                "potential_savings": 3.00,
                "title": {
                    "en": "Consider bank deposit",
                    "es": "Considera deposito bancario",
                },
                "description": {
                    "en": "Bank deposits are often cheaper than cash pickup. Your recipient can access funds instantly.",
                    "es": "Los depositos bancarios suelen ser mas baratos que retiro en efectivo. Tu destinatario puede acceder a los fondos al instante.",
                },
            },
        ]

        # Randomly select 1-2 tips
        return random.sample(tips, min(random.randint(1, 2), len(tips)))

    def get_spending_analysis(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze user's spending patterns.

        Returns mock analysis for development.
        """
        return {
            "user_id": user_id,
            "period": "last_30_days",
            "total_spent": round(random.uniform(200, 2000), 2),
            "categories": {
                "remittances": round(random.uniform(100, 1000), 2),
                "topups": round(random.uniform(20, 100), 2),
                "bill_payments": round(random.uniform(50, 200), 2),
            },
            "compared_to_average": random.choice(["above", "below", "average"]),
            "busiest_day": random.choice(["Monday", "Friday", "Saturday"]),
            "recommended_budget": round(random.uniform(500, 1500), 2),
        }

    def get_savings_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get personalized savings recommendations.

        Returns mock recommendations for development.
        """
        return [
            {
                "id": "rate_alert",
                "type": "rate_monitoring",
                "title": {
                    "en": "Set up rate alerts",
                    "es": "Configura alertas de tipo de cambio",
                },
                "description": {
                    "en": "Get notified when the exchange rate reaches your target. Send when rates are favorable.",
                    "es": "Recibe notificaciones cuando el tipo de cambio alcance tu objetivo. Envia cuando las tasas sean favorables.",
                },
            },
            {
                "id": "batch_transfers",
                "type": "consolidation",
                "title": {
                    "en": "Consolidate small transfers",
                    "es": "Consolida transferencias pequenas",
                },
                "description": {
                    "en": "Sending one larger transfer is often cheaper than multiple small ones due to fixed fees.",
                    "es": "Enviar una transferencia mas grande suele ser mas barato que varias pequenas debido a comisiones fijas.",
                },
            },
        ]


# Singleton instance
_financial_data_service: Optional[FinancialDataService] = None


def get_financial_data_service() -> FinancialDataService:
    """Get the singleton financial data service instance."""
    global _financial_data_service
    if _financial_data_service is None:
        _financial_data_service = FinancialDataService()
    return _financial_data_service
