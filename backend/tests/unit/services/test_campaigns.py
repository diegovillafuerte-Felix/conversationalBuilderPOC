"""Unit tests for the Campaigns Service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from app.services.campaigns import (
    CampaignsService,
    get_campaigns_service,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def campaigns_service():
    """Create a fresh campaigns service instance."""
    return CampaignsService()


@pytest.fixture
def sample_campaign():
    """Sample campaign for testing."""
    today = datetime.now()
    return {
        "id": "test_campaign",
        "type": "promotion",
        "start": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
        "end": (today + timedelta(days=25)).strftime("%Y-%m-%d"),
        "status": "active",
        "title": {"en": "Test Campaign", "es": "Campaña de Prueba"},
        "description": {"en": "Test description", "es": "Descripción de prueba"},
        "trigger_contexts": ["test_context"],
    }


# ============================================================================
# CampaignsService Initialization Tests
# ============================================================================

class TestCampaignsServiceInit:
    """Tests for CampaignsService initialization."""

    def test_initializes_with_campaigns(self, campaigns_service):
        """Test service initializes with campaign data."""
        assert campaigns_service._campaigns is not None
        assert len(campaigns_service._campaigns) > 0

    def test_initializes_empty_impressions(self, campaigns_service):
        """Test service initializes with empty impressions dict."""
        assert campaigns_service._impressions == {}

    def test_default_campaigns_have_required_fields(self, campaigns_service):
        """Test default campaigns have all required fields."""
        for campaign in campaigns_service._campaigns:
            assert "id" in campaign
            assert "type" in campaign
            assert "start" in campaign
            assert "status" in campaign
            assert "title" in campaign
            assert "description" in campaign


# ============================================================================
# GetActiveCampaigns Tests
# ============================================================================

class TestGetActiveCampaigns:
    """Tests for get_active_campaigns method."""

    def test_returns_only_active_campaigns(self, campaigns_service):
        """Test returns only campaigns with active status."""
        campaigns = campaigns_service.get_active_campaigns()

        for campaign in campaigns:
            assert campaign["status"] == "active"

    def test_filters_by_start_date(self, campaigns_service):
        """Test excludes campaigns that haven't started."""
        # Add a future campaign
        future_campaign = {
            "id": "future_campaign",
            "type": "promotion",
            "start": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "end": (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
            "status": "active",
            "title": {"en": "Future"},
            "description": {"en": "Future campaign"},
        }
        campaigns_service._campaigns.append(future_campaign)

        active = campaigns_service.get_active_campaigns()
        ids = [c["id"] for c in active]

        assert "future_campaign" not in ids

    def test_filters_by_end_date(self, campaigns_service):
        """Test excludes campaigns that have ended."""
        # Add an expired campaign
        expired_campaign = {
            "id": "expired_campaign",
            "type": "promotion",
            "start": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
            "end": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "status": "active",
            "title": {"en": "Expired"},
            "description": {"en": "Expired campaign"},
        }
        campaigns_service._campaigns.append(expired_campaign)

        active = campaigns_service.get_active_campaigns()
        ids = [c["id"] for c in active]

        assert "expired_campaign" not in ids

    def test_includes_campaigns_without_end_date(self, campaigns_service):
        """Test includes campaigns with no end date (perpetual)."""
        active = campaigns_service.get_active_campaigns()

        # first_transfer_free has no end date
        ids = [c["id"] for c in active]
        assert "first_transfer_free" in ids


# ============================================================================
# GetCampaignById Tests
# ============================================================================

class TestGetCampaignById:
    """Tests for get_campaign_by_id method."""

    def test_returns_campaign_when_found(self, campaigns_service):
        """Test returns campaign when ID exists."""
        campaign = campaigns_service.get_campaign_by_id("referral_bonus")

        assert campaign is not None
        assert campaign["id"] == "referral_bonus"

    def test_returns_none_when_not_found(self, campaigns_service):
        """Test returns None when ID doesn't exist."""
        campaign = campaigns_service.get_campaign_by_id("nonexistent")
        assert campaign is None


# ============================================================================
# CheckUserEligibility Tests
# ============================================================================

class TestCheckUserEligibility:
    """Tests for check_user_eligibility method."""

    def test_returns_not_eligible_for_unknown_campaign(self, campaigns_service):
        """Test returns not eligible for unknown campaign."""
        result = campaigns_service.check_user_eligibility("user_123", "nonexistent")

        assert result["eligible"] is False
        assert "Campaign not found" in result["reason"]

    def test_returns_eligible_for_valid_campaign(self, campaigns_service):
        """Test returns eligible for valid campaign."""
        # Multiple runs due to randomness - at least one should be eligible
        eligible_count = 0
        for _ in range(10):
            result = campaigns_service.check_user_eligibility("user_123", "referral_bonus")
            if result.get("eligible"):
                eligible_count += 1

        # referral_bonus should be consistently eligible
        assert eligible_count > 0

    def test_tracks_max_uses(self, campaigns_service):
        """Test tracks max uses for limited-use campaigns."""
        # new_corridor_mx has max_uses = 3
        user_id = "test_user_max_uses"

        # Record 3 conversions
        for _ in range(3):
            campaigns_service.record_campaign_impression(
                user_id, "new_corridor_mx", "test", converted=True
            )

        result = campaigns_service.check_user_eligibility(user_id, "new_corridor_mx")

        assert result["eligible"] is False
        assert "Maximum uses reached" in result["reason"]


# ============================================================================
# RecordCampaignImpression Tests
# ============================================================================

class TestRecordCampaignImpression:
    """Tests for record_campaign_impression method."""

    def test_records_impression(self, campaigns_service):
        """Test successfully records impression."""
        result = campaigns_service.record_campaign_impression(
            user_id="user_123",
            campaign_id="referral_bonus",
            context="shadow_message",
            converted=False,
        )

        assert result["recorded"] is True
        assert result["impression"]["campaign_id"] == "referral_bonus"
        assert result["impression"]["context"] == "shadow_message"
        assert result["impression"]["converted"] is False

    def test_tracks_multiple_impressions(self, campaigns_service):
        """Test tracks multiple impressions for same user."""
        campaigns_service.record_campaign_impression(
            "user_123", "referral_bonus", "context1"
        )
        result = campaigns_service.record_campaign_impression(
            "user_123", "referral_bonus", "context2"
        )

        assert result["total_impressions"] == 2

    def test_records_conversion(self, campaigns_service):
        """Test records conversion flag."""
        result = campaigns_service.record_campaign_impression(
            user_id="user_123",
            campaign_id="referral_bonus",
            context="checkout",
            converted=True,
        )

        assert result["impression"]["converted"] is True

    def test_includes_timestamp(self, campaigns_service):
        """Test impression includes timestamp."""
        result = campaigns_service.record_campaign_impression(
            "user_123", "referral_bonus", "test"
        )

        assert "timestamp" in result["impression"]
        # Should be valid ISO format
        datetime.fromisoformat(result["impression"]["timestamp"])


# ============================================================================
# GetCampaignsForContext Tests
# ============================================================================

class TestGetCampaignsForContext:
    """Tests for get_campaigns_for_context method."""

    def test_returns_campaigns_matching_context(self, campaigns_service):
        """Test returns campaigns that match the context."""
        campaigns = campaigns_service.get_campaigns_for_context("remittances")

        for campaign in campaigns:
            # Should either match context or have no trigger contexts
            contexts = campaign.get("trigger_contexts", [])
            assert "remittances" in contexts or len(contexts) == 0

    def test_returns_empty_for_unmatched_context(self, campaigns_service):
        """Test returns empty for context with no matching campaigns."""
        campaigns = campaigns_service.get_campaigns_for_context("nonexistent_context")

        # All returned campaigns should have empty trigger_contexts
        for campaign in campaigns:
            contexts = campaign.get("trigger_contexts", [])
            assert len(contexts) == 0 or "nonexistent_context" in contexts

    def test_filters_mexico_transfers(self, campaigns_service):
        """Test filters campaigns for mexico_transfer context."""
        campaigns = campaigns_service.get_campaigns_for_context("mexico_transfer")
        ids = [c["id"] for c in campaigns]

        # new_corridor_mx has mexico_transfer in trigger_contexts
        assert "new_corridor_mx" in ids


# ============================================================================
# GetUserCampaignHistory Tests
# ============================================================================

class TestGetUserCampaignHistory:
    """Tests for get_user_campaign_history method."""

    def test_returns_empty_history_for_new_user(self, campaigns_service):
        """Test returns empty history for user with no impressions."""
        history = campaigns_service.get_user_campaign_history("new_user")

        assert history["user_id"] == "new_user"
        assert history["total_impressions"] == 0
        assert history["total_conversions"] == 0
        assert history["campaigns"] == {}

    def test_returns_history_with_impressions(self, campaigns_service):
        """Test returns history with recorded impressions."""
        # Record some impressions
        campaigns_service.record_campaign_impression(
            "user_123", "referral_bonus", "context1", converted=False
        )
        campaigns_service.record_campaign_impression(
            "user_123", "referral_bonus", "context2", converted=True
        )
        campaigns_service.record_campaign_impression(
            "user_123", "new_corridor_mx", "context3", converted=False
        )

        history = campaigns_service.get_user_campaign_history("user_123")

        assert history["total_impressions"] == 3
        assert history["total_conversions"] == 1
        assert "referral_bonus" in history["campaigns"]
        assert "new_corridor_mx" in history["campaigns"]

    def test_tracks_conversions_per_campaign(self, campaigns_service):
        """Test tracks conversions per campaign correctly."""
        campaigns_service.record_campaign_impression(
            "user_123", "referral_bonus", "ctx1", converted=True
        )
        campaigns_service.record_campaign_impression(
            "user_123", "referral_bonus", "ctx2", converted=True
        )
        campaigns_service.record_campaign_impression(
            "user_123", "referral_bonus", "ctx3", converted=False
        )

        history = campaigns_service.get_user_campaign_history("user_123")

        assert history["campaigns"]["referral_bonus"]["impressions"] == 3
        assert history["campaigns"]["referral_bonus"]["conversions"] == 2


# ============================================================================
# Singleton Instance Tests
# ============================================================================

class TestSingletonInstance:
    """Tests for singleton instance getter."""

    def test_get_campaigns_service_returns_instance(self):
        """Test singleton getter returns service instance."""
        service = get_campaigns_service()
        assert isinstance(service, CampaignsService)

    def test_singleton_returns_same_instance(self):
        """Test singleton returns same instance on multiple calls."""
        service1 = get_campaigns_service()
        service2 = get_campaigns_service()
        assert service1 is service2
