"""Tests for user profile endpoints."""

import pytest


async def test_get_profile(auth_client):
    client, data = auth_client
    resp = await client.get("/profile")
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["email"] == "test@example.com"
    assert profile["name"] == "Test User"
    assert profile["user_id"] == data["user_id"]


async def test_get_profile_unauthorized(client):
    resp = await client.get("/profile")
    assert resp.status_code in (401, 403)


async def test_update_profile(auth_client):
    client, _ = auth_client
    resp = await client.put(
        "/profile",
        json={"name": "Updated Name", "age": 25, "weight": 70.5, "fitness_goals": "Run a marathon"},
    )
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["name"] == "Updated Name"
    assert profile["age"] == 25
    assert profile["weight"] == 70.5
    assert profile["fitness_goals"] == "Run a marathon"


async def test_update_profile_partial(auth_client):
    client, _ = auth_client
    resp = await client.put("/profile", json={"age": 30})
    assert resp.status_code == 200
    assert resp.json()["age"] == 30
    assert resp.json()["name"] == "Test User"


async def test_update_profile_validation(auth_client):
    client, _ = auth_client
    resp = await client.put("/profile", json={"age": 5})
    assert resp.status_code == 422
