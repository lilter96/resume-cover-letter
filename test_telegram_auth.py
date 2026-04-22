"""
Tests for Telegram Login Widget authentication.
Covers: hash verification, user data extraction, DB registration/login,
and the FastAPI callback endpoint.
"""

import hashlib
import hmac
import time
import os
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "8780467017:AAGTKdf4O2mSuUj6MOs_EGi_J-RQJRsjVJk")
os.environ.setdefault("TELEGRAM_BOT_USERNAME", "Maksbeatiful_bot")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from models import Base, User, CreditTransaction
from auth import AuthManager, UserManager
from telegram_oauth import TelegramOAuthService, get_telegram_oauth_service

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


# ── helpers ────────────────────────────────────────────────────────────────

def _make_auth_data(telegram_id=123456789, first_name="Test", username="testuser",
                    photo_url=None, offset_secs=0):
    """Build a correctly signed Telegram auth payload."""
    data = {
        "id": str(telegram_id),
        "first_name": first_name,
        "auth_date": str(int(time.time()) - offset_secs),
    }
    if username:
        data["username"] = username
    if photo_url:
        data["photo_url"] = photo_url

    secret = hashlib.sha256(BOT_TOKEN.encode()).digest()
    check_str = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    data["hash"] = hmac.new(secret, check_str.encode(), hashlib.sha256).hexdigest()
    return data


def _in_memory_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


# ── TelegramOAuthService unit tests ────────────────────────────────────────

class TestTelegramOAuthService:

    def setup_method(self):
        self.svc = TelegramOAuthService()

    def test_is_configured(self):
        assert self.svc.is_configured() is True

    def test_valid_hash_accepted(self):
        data = _make_auth_data()
        assert self.svc.verify_auth(data) is True

    def test_tampered_hash_rejected(self):
        data = _make_auth_data()
        data["hash"] = "deadbeef" * 8
        assert self.svc.verify_auth(data) is False

    def test_missing_hash_rejected(self):
        data = _make_auth_data()
        del data["hash"]
        assert self.svc.verify_auth(data) is False

    def test_stale_auth_date_rejected(self):
        # auth_date more than 24 hours old
        data = _make_auth_data(offset_secs=90000)
        assert self.svc.verify_auth(data) is False

    def test_extract_full_user_data(self):
        data = _make_auth_data(
            telegram_id=42, first_name="John", username="john_doe",
            photo_url="https://t.me/photo.jpg"
        )
        result = self.svc.extract_user_data(data)
        assert result["telegram_id"] == "42"
        assert result["telegram_username"] == "john_doe"
        assert result["name"] == "John"
        assert result["photo_url"] == "https://t.me/photo.jpg"
        assert result["email"] == "42@telegram.user"

    def test_extract_user_data_no_username(self):
        data = _make_auth_data(telegram_id=99, first_name="Alice", username=None)
        result = self.svc.extract_user_data(data)
        assert result["telegram_username"] is None
        assert result["name"] == "Alice"

    def test_extract_user_data_name_fallback(self):
        # No first_name → name falls back to "User {id}"
        data = _make_auth_data(telegram_id=7, first_name="", username=None)
        result = self.svc.extract_user_data(data)
        assert result["name"] == "User 7"

    def test_singleton(self):
        # get_telegram_oauth_service() returns same instance
        svc1 = get_telegram_oauth_service()
        svc2 = get_telegram_oauth_service()
        assert svc1 is svc2

    def test_unconfigured_raises(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_BOT_USERNAME": ""}):
            with pytest.raises(ValueError):
                TelegramOAuthService()


# ── UserManager integration tests ──────────────────────────────────────────

class TestRegisterOrLoginTelegramUser:

    def setup_method(self):
        self.db = _in_memory_session()
        self.auth_manager = AuthManager(secret_key="test-secret")
        self.user_manager = UserManager(self.auth_manager)
        self.svc = TelegramOAuthService()

    def teardown_method(self):
        self.db.close()

    def _user_data(self, telegram_id="111", name="Tg User", username="tguser"):
        return {
            "telegram_id": telegram_id,
            "telegram_username": username,
            "name": name,
            "photo_url": None,
            "email": f"{telegram_id}@telegram.user",
        }

    def test_new_user_created(self):
        result = self.user_manager.register_or_login_telegram_user(
            self.db, self._user_data()
        )
        assert result["success"] is True
        assert "token" in result
        user = self.db.query(User).filter_by(telegram_id="111").first()
        assert user is not None
        assert user.auth_provider == "telegram"
        assert user.is_verified is True
        assert user.credits == 3

    def test_new_user_gets_welcome_credits(self):
        self.user_manager.register_or_login_telegram_user(
            self.db, self._user_data(telegram_id="222")
        )
        user = self.db.query(User).filter_by(telegram_id="222").first()
        tx = self.db.query(CreditTransaction).filter_by(user_id=user.id).first()
        assert tx is not None
        assert tx.transaction_type == "bonus"
        assert tx.credits_amount == 3

    def test_existing_user_login(self):
        # Register once
        r1 = self.user_manager.register_or_login_telegram_user(
            self.db, self._user_data(telegram_id="333")
        )
        # Login again
        r2 = self.user_manager.register_or_login_telegram_user(
            self.db, self._user_data(telegram_id="333")
        )
        assert r2["success"] is True
        # Only one user row
        count = self.db.query(User).filter_by(telegram_id="333").count()
        assert count == 1
        # Only one welcome credit transaction
        user = self.db.query(User).filter_by(telegram_id="333").first()
        tx_count = self.db.query(CreditTransaction).filter_by(user_id=user.id).count()
        assert tx_count == 1

    def test_missing_telegram_id_fails(self):
        bad_data = {"telegram_id": None, "name": "X", "email": "x@telegram.user"}
        result = self.user_manager.register_or_login_telegram_user(self.db, bad_data)
        assert result["success"] is False

    def test_token_is_valid_jwt(self):
        result = self.user_manager.register_or_login_telegram_user(
            self.db, self._user_data(telegram_id="444")
        )
        user_id = self.auth_manager.verify_token(result["token"])
        assert user_id is not None
        user = self.db.query(User).filter_by(id=user_id).first()
        assert user.telegram_id == "444"

    def test_linking_telegram_to_existing_email_account(self):
        # User already registered with the synthetic email
        existing = User(
            email="555@telegram.user",
            name="Existing",
            auth_provider="local",
            credits=5,
        )
        self.db.add(existing)
        self.db.commit()

        result = self.user_manager.register_or_login_telegram_user(
            self.db, self._user_data(telegram_id="555")
        )
        assert result["success"] is True
        self.db.refresh(existing)
        assert existing.telegram_id == "555"
        assert existing.credits == 5  # credits unchanged on link


# ── FastAPI endpoint smoke test ─────────────────────────────────────────────

def _make_app_client():
    """Import app with heavy optional deps mocked out."""
    import sys
    from unittest.mock import MagicMock
    for mod in (
        "pandas", "tronpy", "stripe", "prometheus_client", "openai",
        "tronpy.keys", "tronpy.providers",
        "scripts.resume_generator", "scripts.hh",
        "crypto_payment", "stripe_payment", "metrics", "middleware",
    ):
        sys.modules.setdefault(mod, MagicMock())

    import importlib
    if "app" in sys.modules:
        app_module = sys.modules["app"]
    else:
        app_module = importlib.import_module("app")

    from fastapi.testclient import TestClient
    app_module.telegram_oauth_service = TelegramOAuthService()
    return TestClient(app_module.app), app_module


class TestTelegramCallbackEndpoint:

    def setup_method(self):
        self.client, self.app_module = _make_app_client()

    def test_status_endpoint(self):
        resp = self.client.get("/api/auth/telegram/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert data["bot_username"] == "Maksbeatiful_bot"

    def test_callback_valid_auth(self):
        data = _make_auth_data(telegram_id=987654321, first_name="Widget", username="widgetuser")
        resp = self.client.get("/auth/telegram/callback", params=data,
                               follow_redirects=False)
        # Should set cookie and return HTML redirect (200 with redirect script)
        assert resp.status_code == 200
        assert "access_token" in resp.cookies

    def test_callback_invalid_hash(self):
        data = _make_auth_data()
        data["hash"] = "badhash"
        resp = self.client.get("/auth/telegram/callback", params=data)
        assert resp.status_code == 400

    def test_callback_missing_hash(self):
        data = _make_auth_data()
        del data["hash"]
        resp = self.client.get("/auth/telegram/callback", params=data)
        assert resp.status_code == 400
