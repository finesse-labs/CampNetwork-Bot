# src/cookie_manager.py
import json
import os
from datetime import datetime, timedelta
from .utils import logger

class CookieManager:
    def __init__(self, file_path="data/cookies.json"):
        self.file_path = file_path
        self.cookies = self.load_cookies()

    def load_cookies(self):
        """Load cookies from JSON file."""
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return {}

    def save_cookies(self, wallet_address, cf_clearance, session_token, expires_at=None):
        """Save cookies and tokens for an account."""
        if not expires_at:
            expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        self.cookies[wallet_address] = {
            "cf_clearance": cf_clearance,
            "session_token": session_token,
            "expires_at": expires_at
        }
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.cookies, f, indent=4)
            logger.info(f"Cookies saved for {wallet_address[:8]}...")
        except Exception as e:
            logger.error(f"Error saving cookies: {e}")

    def get_valid_cookies(self, wallet_address):
        """Retrieve valid cookies if they haven't expired."""
        if wallet_address not in self.cookies:
            return None, None
        cookie_data = self.cookies[wallet_address]
        expires_at = datetime.fromisoformat(cookie_data["expires_at"])
        if datetime.utcnow() > expires_at:
            logger.info(f"Cookies for {wallet_address[:8]}... have expired")
            return None, None
        return cookie_data["cf_clearance"], cookie_data["session_token"]

    def remove_cookies(self, wallet_address):
        """Remove cookies for an account."""
        if wallet_address in self.cookies:
            del self.cookies[wallet_address]
            with open(self.file_path, 'w') as f:
                json.dump(self.cookies, f, indent=4)
            logger.info(f"Cookies removed for {wallet_address[:8]}...")