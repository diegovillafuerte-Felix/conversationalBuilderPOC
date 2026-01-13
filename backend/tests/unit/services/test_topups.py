"""Unit tests for the MockTopUpsService."""

import pytest
from app.services.topups import MockTopUpsService


class TestMockTopUpsServiceCarriers:
    """Test cases for carrier-related functionality."""

    def test_get_carriers_mexico(self):
        """Test getting carriers for Mexico."""
        service = MockTopUpsService()
        result = service.get_carriers("MX")

        assert "carriers" in result
        carriers = result["carriers"]
        assert len(carriers) > 0

        carrier_names = [c["name"] for c in carriers]
        assert "Telcel" in carrier_names
        assert "Movistar" in carrier_names
        assert "AT&T México" in carrier_names

    def test_get_carriers_guatemala(self):
        """Test getting carriers for Guatemala."""
        service = MockTopUpsService()
        result = service.get_carriers("GT")

        carriers = result["carriers"]
        carrier_names = [c["name"] for c in carriers]
        assert "Claro Guatemala" in carrier_names
        assert "Tigo Guatemala" in carrier_names

    def test_get_carriers_unknown_country(self):
        """Test getting carriers for unknown country."""
        service = MockTopUpsService()
        result = service.get_carriers("XX")

        assert result["carriers"] == []

    def test_get_carrier_by_id(self):
        """Test getting a specific carrier by ID."""
        service = MockTopUpsService()
        carrier = service.get_carrier("telcel", "MX")

        assert carrier is not None
        assert carrier["id"] == "telcel"
        assert carrier["name"] == "Telcel"
        assert carrier["currency"] == "MXN"
        assert "plans" in carrier
        assert len(carrier["plans"]) > 0

    def test_get_carrier_not_found(self):
        """Test getting a non-existent carrier."""
        service = MockTopUpsService()
        carrier = service.get_carrier("nonexistent", "MX")

        assert carrier is None


class TestMockTopUpsServiceDetection:
    """Test cases for carrier detection."""

    def test_detect_carrier_mexico_number(self):
        """Test carrier detection for Mexican numbers."""
        service = MockTopUpsService()
        result = service.detect_carrier("+52 55 1234 5678")

        assert result["valid"] is True
        assert result["country"] == "MX"
        assert result["carrier"] == "telcel"
        assert result["currency"] == "MXN"

    def test_detect_carrier_mexico_number_no_plus(self):
        """Test carrier detection for Mexican numbers without plus."""
        service = MockTopUpsService()
        result = service.detect_carrier("52 55 1234 5678")

        assert result["valid"] is True
        assert result["country"] == "MX"

    def test_detect_carrier_guatemala_number(self):
        """Test carrier detection for Guatemala numbers."""
        service = MockTopUpsService()
        result = service.detect_carrier("+502 5555 1234")

        assert result["valid"] is True
        assert result["country"] == "GT"
        assert result["carrier"] == "claro_gt"
        assert result["currency"] == "GTQ"

    def test_detect_carrier_invalid_number(self):
        """Test carrier detection for invalid numbers."""
        service = MockTopUpsService()
        result = service.detect_carrier("+1 555 1234")

        assert result["valid"] is False
        assert result["carrier"] is None


class TestMockTopUpsServicePricing:
    """Test cases for pricing functionality."""

    def test_get_topup_price_mexico(self):
        """Test price calculation for Mexico."""
        service = MockTopUpsService()
        result = service.get_topup_price("telcel", 100, "MX")

        assert result["localAmount"] == 100
        assert result["localCurrency"] == "MXN"
        assert result["usdAmount"] > 0
        assert result["fee"] == 0.99
        assert result["totalUsd"] > result["usdAmount"]  # Includes fee
        assert result["totalUsd"] == round(result["usdAmount"] + result["fee"], 2)

    def test_get_topup_price_guatemala(self):
        """Test price calculation for Guatemala."""
        service = MockTopUpsService()
        result = service.get_topup_price("claro_gt", 50, "GT")

        assert result["localAmount"] == 50
        assert result["localCurrency"] == "GTQ"
        assert result["usdAmount"] > 0

    def test_get_topup_price_unknown_carrier(self):
        """Test price calculation for unknown carrier."""
        service = MockTopUpsService()

        with pytest.raises(ValueError, match="Carrier not found"):
            service.get_topup_price("unknown_carrier", 100, "MX")


class TestMockTopUpsServiceSendTopup:
    """Test cases for sending topups."""

    def test_send_topup(self):
        """Test sending a topup."""
        service = MockTopUpsService()
        result = service.send_topup(
            phone_number="+52 55 1234 5678",
            carrier_id="telcel",
            amount=100,
            user_id="test_user",
        )

        assert result["status"] == "completed"
        assert result["topupId"].startswith("TOP")
        assert result["phoneNumber"] == "+52 55 1234 5678"
        assert result["carrier"] == "telcel"
        assert result["localAmount"] == 100
        assert "usdCharged" in result
        assert "processedAt" in result


class TestMockTopUpsServiceFrequentNumbers:
    """Test cases for frequent numbers."""

    def test_get_frequent_numbers_demo_user(self):
        """Test getting frequent numbers for demo user."""
        service = MockTopUpsService()
        result = service.get_frequent_numbers("user_demo")

        assert "numbers" in result
        assert len(result["numbers"]) > 0

        first_number = result["numbers"][0]
        assert "phoneNumber" in first_number
        assert "carrier" in first_number
        assert "nickname" in first_number

    def test_get_frequent_numbers_fallback(self):
        """Test getting frequent numbers falls back to demo data."""
        service = MockTopUpsService()
        result = service.get_frequent_numbers("unknown_user")

        # Should fall back to demo data
        assert "numbers" in result
        assert len(result["numbers"]) > 0


class TestMockTopUpsServicePlans:
    """Test cases for carrier plans."""

    def test_get_carrier_plans(self):
        """Test getting carrier plans."""
        service = MockTopUpsService()
        plans = service.get_carrier_plans("telcel", "MX")

        assert len(plans) > 0
        for plan in plans:
            assert "amount" in plan
            assert "description" in plan
            assert "data" in plan

    def test_get_carrier_plans_not_found(self):
        """Test getting plans for non-existent carrier."""
        service = MockTopUpsService()
        plans = service.get_carrier_plans("unknown", "MX")

        assert plans == []


class TestMockTopUpsServiceHistory:
    """Test cases for topup history."""

    def test_get_topup_history(self):
        """Test getting topup history."""
        service = MockTopUpsService()
        history = service.get_topup_history("test_user")

        assert len(history) > 0
        for entry in history:
            assert "topupId" in entry
            assert "phoneNumber" in entry
            assert "carrier" in entry
            assert "status" in entry

    def test_get_topup_history_limit(self):
        """Test getting topup history with limit."""
        service = MockTopUpsService()
        history = service.get_topup_history("test_user", limit=1)

        assert len(history) <= 1


class TestMockTopUpsServiceLanguage:
    """Test cases for language handling."""

    def test_language_switching(self):
        """Test that service returns raw data without formatting."""
        service_es = MockTopUpsService(language="es")
        service_en = MockTopUpsService(language="en")

        result_es = service_es.get_carriers("MX")
        result_en = service_en.get_carriers("MX")

        # Service should return raw data only, no _message field
        assert "_message" not in result_es
        assert "_message" not in result_en
        # Should have raw data fields
        assert "carriers" in result_es
        assert "carriers" in result_en
        assert "country" in result_es
        assert "country" in result_en

    def test_set_language(self):
        """Test setting language."""
        service = MockTopUpsService(language="es")

        assert service.language == "es"

        service.language = "en"
        assert service.language == "en"
