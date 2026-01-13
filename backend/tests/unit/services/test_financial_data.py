"""Unit tests for the Financial Data Service."""

import pytest
from unittest.mock import patch
from app.services.financial_data import (
    FinancialDataService,
    get_financial_data_service,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def financial_service():
    """Create a fresh financial data service instance."""
    return FinancialDataService()


# ============================================================================
# FinancialDataService Tests
# ============================================================================

class TestFinancialDataService:
    """Tests for the FinancialDataService class."""

    def test_initialization_generates_rate_history(self, financial_service):
        """Test service initializes with rate history."""
        assert financial_service._rate_history is not None
        assert len(financial_service._rate_history) > 0
        assert "USD_MXN" in financial_service._rate_history
        assert "USD_GTM" in financial_service._rate_history

    def test_rate_history_has_30_days(self, financial_service):
        """Test rate history contains 30 days of data."""
        history = financial_service._rate_history["USD_MXN"]
        assert len(history) == 30

    def test_rate_history_has_required_fields(self, financial_service):
        """Test rate history entries have required fields."""
        history = financial_service._rate_history["USD_MXN"]
        entry = history[0]
        assert "date" in entry
        assert "rate" in entry
        assert isinstance(entry["rate"], float)


class TestGetUserFinancialSummary:
    """Tests for get_user_financial_summary method."""

    def test_returns_summary_for_user(self, financial_service):
        """Test returns financial summary with required fields."""
        summary = financial_service.get_user_financial_summary("user_123")

        assert summary["user_id"] == "user_123"
        assert "wallet_balance" in summary
        assert "total_sent_30_days" in summary
        assert "transaction_count_30_days" in summary
        assert "avg_transfer_amount" in summary
        assert "most_used_corridor" in summary
        assert "preferred_delivery_method" in summary
        assert "kyc_level" in summary
        assert "remaining_monthly_limit" in summary
        assert "loyalty_points" in summary

    def test_wallet_balance_is_numeric(self, financial_service):
        """Test wallet balance is a valid number."""
        summary = financial_service.get_user_financial_summary("user_123")
        assert isinstance(summary["wallet_balance"], float)
        assert summary["wallet_balance"] >= 0

    def test_kyc_level_is_valid(self, financial_service):
        """Test KYC level is 1, 2, or 3."""
        summary = financial_service.get_user_financial_summary("user_123")
        assert summary["kyc_level"] in [1, 2, 3]


class TestGetRateTrends:
    """Tests for get_rate_trends method."""

    def test_returns_trends_for_known_corridor(self, financial_service):
        """Test returns rate trends for USD_MXN corridor."""
        trends = financial_service.get_rate_trends("USD_MXN")

        assert trends["corridor"] == "USD_MXN"
        assert "current_rate" in trends
        assert "avg_rate" in trends
        assert "min_rate" in trends
        assert "max_rate" in trends
        assert "trend" in trends
        assert "percent_change" in trends
        assert "history" in trends

    def test_returns_error_for_unknown_corridor(self, financial_service):
        """Test returns error for unknown corridor."""
        trends = financial_service.get_rate_trends("UNKNOWN_CORRIDOR")
        assert "error" in trends
        assert "Unknown corridor" in trends["error"]

    def test_trend_direction_is_valid(self, financial_service):
        """Test trend direction is up, down, or stable."""
        trends = financial_service.get_rate_trends("USD_MXN")
        assert trends["trend"] in ["up", "down", "stable"]

    def test_respects_days_parameter(self, financial_service):
        """Test history length respects days parameter."""
        trends_10 = financial_service.get_rate_trends("USD_MXN", days=10)
        trends_5 = financial_service.get_rate_trends("USD_MXN", days=5)

        assert len(trends_10["history"]) == 10
        assert len(trends_5["history"]) == 5

    def test_min_max_rates_are_correct(self, financial_service):
        """Test min/max are actual bounds of the data."""
        trends = financial_service.get_rate_trends("USD_MXN", days=10)
        rates = [r["rate"] for r in trends["history"]]

        assert trends["min_rate"] == min(rates)
        assert trends["max_rate"] == max(rates)


class TestGetFeeOptimizationTips:
    """Tests for get_fee_optimization_tips method."""

    def test_returns_tips_list(self, financial_service):
        """Test returns list of tips."""
        tips = financial_service.get_fee_optimization_tips("user_123")

        assert isinstance(tips, list)
        assert len(tips) >= 1
        assert len(tips) <= 2

    def test_tips_have_required_fields(self, financial_service):
        """Test each tip has required fields."""
        tips = financial_service.get_fee_optimization_tips("user_123")

        for tip in tips:
            assert "id" in tip
            assert "priority" in tip
            assert "potential_savings" in tip
            assert "title" in tip
            assert "description" in tip

    def test_tips_are_bilingual(self, financial_service):
        """Test tips have English and Spanish versions."""
        tips = financial_service.get_fee_optimization_tips("user_123")

        for tip in tips:
            assert "en" in tip["title"]
            assert "es" in tip["title"]
            assert "en" in tip["description"]
            assert "es" in tip["description"]

    def test_priority_is_valid(self, financial_service):
        """Test priority is high, medium, or low."""
        tips = financial_service.get_fee_optimization_tips("user_123")

        for tip in tips:
            assert tip["priority"] in ["high", "medium", "low"]


class TestGetSpendingAnalysis:
    """Tests for get_spending_analysis method."""

    def test_returns_analysis_for_user(self, financial_service):
        """Test returns spending analysis with required fields."""
        analysis = financial_service.get_spending_analysis("user_123")

        assert analysis["user_id"] == "user_123"
        assert analysis["period"] == "last_30_days"
        assert "total_spent" in analysis
        assert "categories" in analysis
        assert "compared_to_average" in analysis
        assert "busiest_day" in analysis
        assert "recommended_budget" in analysis

    def test_categories_include_all_types(self, financial_service):
        """Test categories include all expected types."""
        analysis = financial_service.get_spending_analysis("user_123")

        assert "remittances" in analysis["categories"]
        assert "topups" in analysis["categories"]
        assert "bill_payments" in analysis["categories"]

    def test_comparison_is_valid(self, financial_service):
        """Test comparison to average is valid value."""
        analysis = financial_service.get_spending_analysis("user_123")
        assert analysis["compared_to_average"] in ["above", "below", "average"]


class TestGetSavingsRecommendations:
    """Tests for get_savings_recommendations method."""

    def test_returns_recommendations_list(self, financial_service):
        """Test returns list of recommendations."""
        recs = financial_service.get_savings_recommendations("user_123")

        assert isinstance(recs, list)
        assert len(recs) == 2

    def test_recommendations_have_required_fields(self, financial_service):
        """Test each recommendation has required fields."""
        recs = financial_service.get_savings_recommendations("user_123")

        for rec in recs:
            assert "id" in rec
            assert "type" in rec
            assert "title" in rec
            assert "description" in rec

    def test_recommendations_are_bilingual(self, financial_service):
        """Test recommendations have English and Spanish versions."""
        recs = financial_service.get_savings_recommendations("user_123")

        for rec in recs:
            assert "en" in rec["title"]
            assert "es" in rec["title"]


class TestSingletonInstance:
    """Tests for singleton instance getter."""

    def test_get_financial_data_service_returns_instance(self):
        """Test singleton getter returns service instance."""
        service = get_financial_data_service()
        assert isinstance(service, FinancialDataService)

    def test_singleton_returns_same_instance(self):
        """Test singleton returns same instance on multiple calls."""
        service1 = get_financial_data_service()
        service2 = get_financial_data_service()
        assert service1 is service2
