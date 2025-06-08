# src/faucet.py
import requests
import time
import random
from .utils import logger
from config import CAPTCHA_API_KEY
from .captha import Solvium
from web3 import Web3

class FaucetService:
    def __init__(self, wallet: str, session, proxy: str = None):
        self.wallet = wallet
        self.proxy = proxy
        self.session = session
        self.public_address = self._get_public_address()

    def _get_public_address(self) -> str:
        """Get public address from private key."""
        try:
            w3 = Web3()
            account = w3.eth.account.from_key(self.wallet.replace('0x', ''))
            return account.address
        except Exception as e:
            logger.error(f"Failed to get address for {self.wallet[:8]}...: {e}")
            return ""

    def request_faucet(self) -> bool:
        """Request faucet."""
        logger.info(f"Requesting faucet for {self.public_address[:8]}...")
        
        # Solve hCaptcha
        solvium = Solvium(api_key=CAPTCHA_API_KEY, proxy=self.proxy)
        captcha_token = solvium.solve_captcha(
            sitekey="5b86452e-488a-4f62-bd32-a332445e2f51",
            pageurl="https://faucet.campnetwork.xyz/"
        )
        if not captcha_token:
            logger.error(f"Failed to solve hCaptcha for {self.public_address[:8]}...")
            return False

        logger.info(f"hCaptcha solved for {self.public_address[:8]}...")

        headers = {
            'accept': '*/*',
            'accept-language': 'ru,en-US;q=0.9,en;q=0.8,ru-RU;q=0.7,zh-TW;q=0.6,zh;q=0.5,uk;q=0.4',
            'content-type': 'application/json',
            'h-captcha-response': captcha_token,
            'origin': 'https://faucet.campnetwork.xyz',
            'priority': 'u=1, i',
            'referer': 'https://faucet.campnetwork.xyz/',
            'sec-ch-ua': '"Chromium";v="133", "Google Chrome";v="133", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        }
        json_data = {'address': self.public_address}
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        try:
            response = self.session.post(
                'https://faucet-go-production.up.railway.app/api/claim',
                headers=headers,
                json=json_data,
                proxies=proxies,
                timeout=30
            )

            if "Bot detected" in response.text:
                logger.error(f"Bot detected for {self.public_address[:8]}...; needs transactions")
                return False
            if "Your IP has exceeded the rate limit" in response.text:
                logger.error(f"Rate limit exceeded for IP: {response.json().get('msg', '')}")
                return False
            if "Not enough transactions" in response.text:
                logger.info(f"Not enough transactions {self.public_address[:8]}...")
                return False
            if "Too many successful transactions for this wallet address" in response.text:
                logger.info(f"Faucet already claimed for {self.public_address[:8]}...; wait 24h")
                return True
            
            

            logger.info(f"Faucet claimed for {self.public_address[:8]}...")
            return True

        except Exception as e:
            if "Wallet does not meet eligibility requirements" in str(e):
                logger.error(f"Wallet {self.public_address[:8]}... ineligible: needs 0.05 ETH or 3+ transactions")
                return False
            logger.error(f"Failed to request faucet for {self.public_address[:8]}...: {e}")
            return False