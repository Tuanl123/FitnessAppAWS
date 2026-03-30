"""Tests for authentication endpoints: register, login, refresh."""

import pytest


async def test_register_success(client):
    resp = await client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "SecureP@ss1", "name": "New User"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["name"] == "New User"
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "SecureP@ss1", "name": "First"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json={**payload, "name": "Second"})
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"].lower()


async def test_register_weak_password(client):
    resp = await client.post(
        "/auth/register",
        json={"email": "weak@example.com", "password": "short", "name": "Weak"},
    )
    assert resp.status_code == 422


async def test_login_success(client):
    await client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": "SecureP@ss1", "name": "Login User"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "SecureP@ss1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password(client):
    await client.post(
        "/auth/register",
        json={"email": "wrong@example.com", "password": "SecureP@ss1", "name": "Wrong"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "wrong@example.com", "password": "BadPassword1"},
    )
    assert resp.status_code == 401


async def test_login_nonexistent_user(client):
    resp = await client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "Anything1"},
    )
    assert resp.status_code == 401


async def test_refresh_token(client):
    reg = await client.post(
        "/auth/register",
        json={"email": "refresh@example.com", "password": "SecureP@ss1", "name": "Refresh"},
    )
    refresh_token = reg.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_refresh_with_invalid_token(client):
    resp = await client.post("/auth/refresh", json={"refresh_token": "not.a.real.token"})
    assert resp.status_code == 401
