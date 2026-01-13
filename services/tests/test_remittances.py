"""Tests for remittances service endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_get_corridors(client):
    """Test getting corridors."""
    response = await client.get(
        "/api/v1/remittances/corridors",
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "corridors" in data["data"]
    assert len(data["data"]["corridors"]) == 7  # 7 countries


@pytest.mark.asyncio
async def test_get_exchange_rate(client):
    """Test getting exchange rate."""
    response = await client.get(
        "/api/v1/remittances/exchange-rate",
        params={"country": "MX"},
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "rate" in data["data"]
    assert data["data"]["to_currency"] == "MXN"


@pytest.mark.asyncio
async def test_get_exchange_rate_invalid_country(client):
    """Test getting exchange rate for invalid country."""
    response = await client.get(
        "/api/v1/remittances/exchange-rate",
        params={"country": "XX"},
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "COUNTRY_NOT_SUPPORTED"


@pytest.mark.asyncio
async def test_create_quote(client):
    """Test creating a quote."""
    response = await client.post(
        "/api/v1/remittances/quotes",
        json={"amount_usd": 200, "country": "MX", "delivery_type": "BANK"},
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "quote_id" in data["data"]
    assert data["data"]["amount_usd"] == 200
    assert "rate" in data["data"]
    assert "fee" in data["data"]


@pytest.mark.asyncio
async def test_list_recipients(client):
    """Test listing recipients."""
    response = await client.get(
        "/api/v1/remittances/recipients",
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "recipients" in data["data"]
    assert len(data["data"]["recipients"]) > 0


@pytest.mark.asyncio
async def test_get_recipient(client):
    """Test getting a specific recipient."""
    response = await client.get(
        "/api/v1/remittances/recipients/rec_maria",
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == "rec_maria"


@pytest.mark.asyncio
async def test_get_recipient_not_found(client):
    """Test getting a non-existent recipient."""
    response = await client.get(
        "/api/v1/remittances/recipients/rec_nonexistent",
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_user_limits(client):
    """Test getting user limits."""
    response = await client.get(
        "/api/v1/remittances/limits",
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "kyc_level" in data["data"]
    assert "limits" in data["data"]


@pytest.mark.asyncio
async def test_get_delivery_methods(client):
    """Test getting delivery methods for a country."""
    response = await client.get(
        "/api/v1/remittances/delivery-methods",
        params={"country": "MX"},
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "delivery_methods" in data["data"]
    assert len(data["data"]["delivery_methods"]) > 0


@pytest.mark.asyncio
async def test_list_transfers(client):
    """Test listing transfers."""
    response = await client.get(
        "/api/v1/remittances/transfers",
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "transfers" in data["data"]


@pytest.mark.asyncio
async def test_get_quick_send_options(client):
    """Test getting quick send options."""
    response = await client.get(
        "/api/v1/remittances/quick-send",
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "options" in data["data"]
