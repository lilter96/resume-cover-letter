"""
Telegram OAuth Service for Resume Generator
Handles Telegram Login Widget authentication flow
"""

import hashlib
import hmac
import time
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class TelegramOAuthService:
    """Service for handling Telegram Login Widget authentication."""

    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.bot_username = os.getenv('TELEGRAM_BOT_USERNAME')

        if not self.bot_token or not self.bot_username:
            raise ValueError(
                "Telegram Bot credentials not configured. "
                "Please set TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_USERNAME environment variables."
            )

        # Secret key = SHA-256 of the bot token (per Telegram docs)
        self._secret_key = hashlib.sha256(self.bot_token.encode()).digest()

    def verify_auth(self, data: Dict[str, Any]) -> bool:
        """Verify Telegram Login Widget auth data integrity and freshness."""
        received_hash = data.get('hash', '')
        if not received_hash:
            return False

        check_data = {k: v for k, v in data.items() if k != 'hash'}
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(check_data.items())
        )

        computed_hash = hmac.new(
            self._secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        auth_date = int(data.get('auth_date', 0))
        is_fresh = (time.time() - auth_date) < 86400  # 24 hours

        return hmac.compare_digest(computed_hash, received_hash) and is_fresh

    def extract_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant user data from Telegram auth params."""
        telegram_id = str(data['id'])
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        name = f"{first_name} {last_name}".strip() or f"User {telegram_id}"

        return {
            'telegram_id': telegram_id,
            'telegram_username': data.get('username'),
            'name': name,
            'photo_url': data.get('photo_url'),
            'email': f"{telegram_id}@telegram.user",
        }

    def is_configured(self) -> bool:
        """Check if Telegram bot credentials are properly configured."""
        return bool(self.bot_token and self.bot_username)


# Global singleton
_telegram_oauth_service: Optional[TelegramOAuthService] = None


def get_telegram_oauth_service() -> Optional[TelegramOAuthService]:
    """Get Telegram OAuth service instance (lazy singleton)."""
    global _telegram_oauth_service

    if _telegram_oauth_service is None:
        try:
            _telegram_oauth_service = TelegramOAuthService()
        except ValueError as e:
            print(f"Telegram OAuth not configured: {e}")
            return None

    return _telegram_oauth_service
