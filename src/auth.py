# src/auth.py
import json
import random
import time
import base64
from datetime import datetime, timezone
from web3 import Web3
from eth_account.messages import encode_defunct
from curl_cffi import requests
from curl_cffi.requests import Session
from .utils import logger, private_key_to_address, random_delay
from .cookie_manager import CookieManager
from .captha import Solvium
from config import CAPTCHA_API_KEY

def retry(max_attempts=3, delay_range=(5, 10)):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    pause = random.randint(*delay_range)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {pause} sec...")
                    time.sleep(pause)
        return wrapper
    return decorator

class Auth:
    def __init__(self, private_key, proxy=None, captcha_api_key=CAPTCHA_API_KEY):
        self.private_key = private_key
        self.proxy = proxy
        self.captcha_api_key = captcha_api_key
        self.session = Session(impersonate="chrome136", verify=False, timeout=30)
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self.cookie_manager = CookieManager()
        self.wallet_address = private_key_to_address(private_key)
        self.web3 = Web3()
        self.base_url = "https://loyalty.campnetwork.xyz"
        self.headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "referer": f"{self.base_url}/loyalty",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }

    @retry()
    def _get_nonce(self, cf_token):
        """Retrieve CSRF token (nonce)."""
        cf_clearance, _ = self.cookie_manager.get_valid_cookies(self.wallet_address)
        cookies = {"cf_clearance": cf_clearance or cf_token}
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        try:
            headers = {
                "accept": "*/*",
                "content-type": "application/json",
                "referer": f"{self.base_url}/loyalty",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            }
            response = self.session.get(
                f"{self.base_url}/api/auth/csrf",
                headers=headers,
                cookies=cookies,
                proxies=proxies
            )
            if "Just a moment" in response.text:
                logger.error(f"Cloudflare challenge encountered for {self.wallet_address[:8]}...")
                return None
            return response.json()["csrfToken"]
        except Exception as e:
            logger.error(f"Error retrieving nonce for {self.wallet_address[:8]}...: {e}")
            return None

    def _sign_message(self, message):
        """Sign message with private key."""
        try:
            message_hash = self.web3.eth.account.sign_message(
                encode_defunct(text=message),
                private_key=self.private_key
            )
            return message_hash.signature.hex()
        except Exception as e:
            logger.error(f"Error signing message for {self.wallet_address[:8]}...: {e}")
            return None

    @retry()
    def _solve_cloudflare(self):
        """Solve Cloudflare challenge."""
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        }
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        try:
            response = self.session.get(f"{self.base_url}/loyalty", headers=headers, proxies=proxies)
            if "Just a moment" not in response.text:
                return None  # Cloudflare not required
            logger.info(f"Cloudflare challenge detected for {self.wallet_address[:8]}...")
            solvium = Solvium(api_key=self.captcha_api_key, proxy=self.proxy.split("://")[1] if self.proxy else None)
            cf_clearance = solvium.solve_cf_clearance(
                pageurl=f"{self.base_url}/loyalty",
                body_b64=base64.b64encode(response.content).decode(),
                proxy=self.proxy
            )
            if not cf_clearance:
                logger.error(f"Failed to solve Cloudflare challenge for {self.wallet_address[:8]}...")
                return False
            logger.info(f"Cloudflare challenge solved for {self.wallet_address[:8]}...")
            return cf_clearance
        except Exception as e:
            logger.error(f"Error checking Cloudflare for {self.wallet_address[:8]}...: {e}")
            return False

    @retry()
    def login(self):
        """Authenticate using wallet."""
        # Check for valid cookies
        cf_clearance, session_token = self.cookie_manager.get_valid_cookies(self.wallet_address)
        if cf_clearance and session_token:
            logger.info(f"Using saved cookies for {self.wallet_address[:8]}...")
            time.sleep(5)
            return cf_clearance, session_token
        
        # Solve Cloudflare
        cf_clearance = self._solve_cloudflare()
        if cf_clearance is False:
            return None, None

        # Get nonce
        nonce = self._get_nonce(cf_clearance)
        if not nonce:
            return None, None

        # Create message for signing
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        message = (
            f"loyalty.campnetwork.xyz wants you to sign in with your Ethereum account:\n"
            f"{self.wallet_address}\n\n"
            f"Sign in to the app. Powered by Snag Solutions.\n\n"
            f"URI: {self.base_url}\n"
            f"Version: 1\n"
            f"Chain ID: 123420001114\n"
            f"Nonce: {nonce}\n"
            f"Issued At: {current_time}"
        )
        # Sign message
        signature = self._sign_message(message)
        if not signature:
            return None, None

        # Send authentication request
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded",
            "origin": self.base_url,
            "referer": f"{self.base_url}/loyalty",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        }
        data = {
            "message": json.dumps({
                "domain": "loyalty.campnetwork.xyz",
                "address": self.wallet_address,
                "statement": "Sign in to the app. Powered by Snag Solutions.",
                "uri": self.base_url,
                "version": "1",
                "chainId": 123420001114,
                "nonce": nonce,
                "issuedAt": current_time
            }),
            "accessToken": f"0x{signature}",
            "signature": f"0x{signature}",
            "walletConnectorName": "Rabby Wallet",
            "walletAddress": self.wallet_address,
            "redirect": "false",
            "callbackUrl": "/protected",
            "chainType": "evm",
            "csrfToken": nonce,
            "json": "true",
        }
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        response = self.session.post(
            f"{self.base_url}/api/auth/callback/credentials",
            headers=headers,
            data=data,
            cookies={"cf_clearance": cf_clearance},
            proxies=proxies
        )

        session_token = response.cookies.get("__Secure-next-auth.session-token")
        if not session_token:
            logger.error(f"Failed to obtain session token for {self.wallet_address[:8]}...")
            return None, None
        logger.info(f"Successful authentication for {self.wallet_address[:8]}...")
        self.cookie_manager.save_cookies(self.wallet_address, cf_clearance, session_token)
        time.sleep(5)
        return cf_clearance, session_token