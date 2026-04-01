"""Test fixtures for ingestion-service.

Mocks SQS and db_reader so no external dependencies are needed.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config import settings
from app.main import app


def _make_token(user_id: str | None = None) -> str:
    uid = user_id or str(uuid.uuid4())
    exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode({"sub": uid, "exp": exp}, settings.jwt_secret, algorithm="HS256")


@pytest.fixture
def user_id():
    return str(uuid.uuid4())


@pytest.fixture
def token(user_id):
    return _make_token(user_id)


@pytest.fixture
async def client(token):
    with patch("app.sqs_client.send_message", return_value="mock-msg-id"):
        with patch("app.db_reader.query_history", return_value=([], 0)):
            with patch("app.db_reader.query_summary", return_value=([], [])):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                    headers={"Authorization": f"Bearer {token}"},
                ) as c:
                    yield c
