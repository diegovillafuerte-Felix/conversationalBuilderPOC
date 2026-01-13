"""Tests for SNPL service endpoints."""

import pytest


@pytest.mark.asyncio
async def test_get_eligibility(client):
    """Test getting SNPL eligibility."""
    response = await client.get(
        "/api/v1/snpl/eligibility",
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "eligible" in data["data"]


@pytest.mark.asyncio
async def test_calculate_terms(client):
    """Test calculating loan terms."""
    response = await client.post(
        "/api/v1/snpl/calculate",
        json={"amount": 500, "weeks": 12},
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "weekly_payment" in data["data"]
    assert "total_repayment" in data["data"]


@pytest.mark.asyncio
async def test_get_overview(client):
    """Test getting SNPL overview."""
    response = await client.get(
        "/api/v1/snpl/overview",
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_list_loans(client):
    """Test listing loans."""
    response = await client.get(
        "/api/v1/snpl/loans",
        headers={"X-User-Id": "user_demo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
