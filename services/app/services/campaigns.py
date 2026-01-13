"""
Campaigns Service - Mock service for managing promotions and campaigns
used by the campaigns shadow subagent.
"""
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


class CampaignsService:
    """Service for campaign and promotion management."""

    def __init__(self):
        # Mock campaign data
        self._campaigns = self._initialize_campaigns()
        self._impressions: Dict[str, List[Dict[str, Any]]] = {}

    def _initialize_campaigns(self) -> List[Dict[str, Any]]:
        """Initialize mock campaigns."""
        today = datetime.now()

        return [
            {
                "id": "referral_bonus",
                "type": "referral",
                "start": (today - timedelta(days=15)).strftime("%Y-%m-%d"),
                "end": (today + timedelta(days=45)).strftime("%Y-%m-%d"),
                "status": "active",
                "title": {
                    "en": "Refer a Friend Bonus",
                    "es": "Bono por Referir un Amigo",
                },
                "description": {
                    "en": "Get $10 when your friend makes their first transfer!",
                    "es": "Obtén $10 cuando tu amigo haga su primera transferencia!",
                },
                "terms": {
                    "en": "Friend must complete a transfer of $50 or more.",
                    "es": "El amigo debe completar una transferencia de $50 o más.",
                },
                "reward_amount": 10.00,
                "trigger_contexts": ["transfer_complete", "first_time_user"],
            },
            {
                "id": "new_corridor_mx",
                "type": "promotion",
                "start": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
                "end": (today + timedelta(days=25)).strftime("%Y-%m-%d"),
                "status": "active",
                "title": {
                    "en": "Mexico Transfer Special",
                    "es": "Especial de Transferencias a México",
                },
                "description": {
                    "en": "0% fees on your next 3 transfers to Mexico!",
                    "es": "0% de comisión en tus próximas 3 transferencias a México!",
                },
                "terms": {
                    "en": "Valid for bank deposits only. Max $500 per transfer.",
                    "es": "Válido solo para depósitos bancarios. Máximo $500 por transferencia.",
                },
                "discount_percent": 100,
                "max_uses": 3,
                "trigger_contexts": ["mexico_transfer", "remittances"],
            },
            {
                "id": "wallet_bonus",
                "type": "cashback",
                "start": today.strftime("%Y-%m-%d"),
                "end": (today + timedelta(days=30)).strftime("%Y-%m-%d"),
                "status": "active",
                "title": {
                    "en": "Wallet Top-Up Bonus",
                    "es": "Bono por Recargar Billetera",
                },
                "description": {
                    "en": "Get 2% cashback when you add $100+ to your wallet!",
                    "es": "Obtén 2% de reembolso cuando agregues $100+ a tu billetera!",
                },
                "terms": {
                    "en": "Minimum top-up of $100. Bank transfer only.",
                    "es": "Recarga mínima de $100. Solo transferencia bancaria.",
                },
                "cashback_percent": 2,
                "min_amount": 100,
                "trigger_contexts": ["wallet", "topup"],
            },
            {
                "id": "first_transfer_free",
                "type": "new_user",
                "start": (today - timedelta(days=365)).strftime("%Y-%m-%d"),
                "end": None,  # No end date
                "status": "active",
                "title": {
                    "en": "First Transfer Free",
                    "es": "Primera Transferencia Gratis",
                },
                "description": {
                    "en": "Your first transfer is completely free - no fees!",
                    "es": "Tu primera transferencia es completamente gratis - sin comisiones!",
                },
                "terms": {
                    "en": "For new customers only. Valid for any destination.",
                    "es": "Solo para nuevos clientes. Válido para cualquier destino.",
                },
                "discount_percent": 100,
                "trigger_contexts": ["first_time_user", "remittances"],
            },
        ]

    def get_active_campaigns(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get currently active campaigns, optionally filtered by user eligibility.

        Args:
            user_id: Optional user ID to filter by eligibility

        Returns:
            List of active campaigns
        """
        today = datetime.now().date()
        active = []

        for campaign in self._campaigns:
            # Check dates
            start = datetime.strptime(campaign["start"], "%Y-%m-%d").date()
            end_str = campaign.get("end")
            end = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None

            if today < start:
                continue
            if end and today > end:
                continue
            if campaign.get("status") != "active":
                continue

            # Check user eligibility if user_id provided
            if user_id:
                eligibility = self.check_user_eligibility(user_id, campaign["id"])
                if not eligibility.get("eligible", True):
                    continue

            active.append(campaign)

        return active

    def get_campaign_by_id(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific campaign by ID."""
        for campaign in self._campaigns:
            if campaign["id"] == campaign_id:
                return campaign
        return None

    def check_user_eligibility(self, user_id: str, campaign_id: str) -> Dict[str, Any]:
        """
        Check if a user is eligible for a specific campaign.

        Returns mock eligibility data for development.
        """
        campaign = self.get_campaign_by_id(campaign_id)
        if not campaign:
            return {"eligible": False, "reason": "Campaign not found"}

        # Mock eligibility checks
        # In production, would check user history, usage counts, etc.

        # Check usage count for limited-use campaigns
        max_uses = campaign.get("max_uses")
        if max_uses:
            user_impressions = self._impressions.get(user_id, [])
            campaign_uses = len([
                i for i in user_impressions
                if i.get("campaign_id") == campaign_id and i.get("converted", False)
            ])
            if campaign_uses >= max_uses:
                return {
                    "eligible": False,
                    "reason": "Maximum uses reached",
                    "uses": campaign_uses,
                    "max_uses": max_uses,
                }

        # New user campaigns
        if campaign.get("type") == "new_user":
            # Mock: 30% chance user is not new
            if random.random() < 0.3:
                return {"eligible": False, "reason": "Not a new user"}

        return {
            "eligible": True,
            "campaign": campaign,
            "remaining_uses": max_uses - len([
                i for i in self._impressions.get(user_id, [])
                if i.get("campaign_id") == campaign_id and i.get("converted", False)
            ]) if max_uses else None,
        }

    def record_campaign_impression(
        self,
        user_id: str,
        campaign_id: str,
        context: str,
        converted: bool = False,
    ) -> Dict[str, Any]:
        """
        Record that a campaign was shown to a user.

        Args:
            user_id: User who saw the campaign
            campaign_id: Campaign that was shown
            context: Where/when it was shown (e.g., "shadow_message", "checkout")
            converted: Whether the user took action

        Returns:
            Impression record
        """
        if user_id not in self._impressions:
            self._impressions[user_id] = []

        impression = {
            "campaign_id": campaign_id,
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "converted": converted,
        }

        self._impressions[user_id].append(impression)

        return {
            "recorded": True,
            "impression": impression,
            "total_impressions": len(self._impressions[user_id]),
        }

    def get_campaigns_for_context(
        self,
        context: str,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get campaigns relevant to a specific context.

        Args:
            context: The context to match (e.g., "remittances", "mexico_transfer")
            user_id: Optional user ID for eligibility filtering

        Returns:
            List of relevant campaigns
        """
        active = self.get_active_campaigns(user_id)
        relevant = []

        for campaign in active:
            trigger_contexts = campaign.get("trigger_contexts", [])
            if context in trigger_contexts or not trigger_contexts:
                relevant.append(campaign)

        return relevant

    def get_user_campaign_history(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's campaign interaction history.

        Returns:
            History of campaign impressions and conversions
        """
        impressions = self._impressions.get(user_id, [])

        # Group by campaign
        by_campaign: Dict[str, List[Dict[str, Any]]] = {}
        for impression in impressions:
            campaign_id = impression["campaign_id"]
            if campaign_id not in by_campaign:
                by_campaign[campaign_id] = []
            by_campaign[campaign_id].append(impression)

        return {
            "user_id": user_id,
            "total_impressions": len(impressions),
            "total_conversions": len([i for i in impressions if i.get("converted")]),
            "campaigns": {
                campaign_id: {
                    "impressions": len(records),
                    "conversions": len([r for r in records if r.get("converted")]),
                    "last_seen": max(r["timestamp"] for r in records),
                }
                for campaign_id, records in by_campaign.items()
            },
        }


# Singleton instance
_campaigns_service: Optional[CampaignsService] = None


def get_campaigns_service() -> CampaignsService:
    """Get the singleton campaigns service instance."""
    global _campaigns_service
    if _campaigns_service is None:
        _campaigns_service = CampaignsService()
    return _campaigns_service
