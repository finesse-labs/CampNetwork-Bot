import time
import random
import logging
import requests
import colorlog
from web3 import Web3
from typing import Tuple

# Initialize logger
logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)
logger.propagate = False

# Console format: colored level, plain message
console_format = colorlog.ColoredFormatter(
    "%(cyan)s%(asctime)s ➤ %(log_color)s%(bold)s%(levelname)s%(reset)s%(white)s ➤ %(message)s%(reset)s",
    datefmt="%H:%M:%S",
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    },
    style='%'
)

# File format: no color, same style
file_format = logging.Formatter("%(asctime)s ➤ %(levelname)s - %(message)s", datefmt="%H:%M:%S")

# File handler
file_handler = logging.FileHandler("./logs/bot.log")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(file_format)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_format)
logger.addHandler(console_handler)

def private_key_to_address(private_key: str) -> str:
    """Convert private key to public address."""
    try:
        private_key = private_key.replace('0x', '')
        w3 = Web3()
        account = w3.eth.account.from_key(private_key)
        return account.address
    except Exception as e:
        logger.error(f"Failed to convert key {private_key[:10]}...: {e}")
        return ""

def random_delay(delay_range: Tuple[int, int]) -> None:
    """Apply random delay in given range."""
    time.sleep(random.uniform(delay_range[0] * 60, delay_range[1] * 60))

def get_user_id(wallet: str, session, api_url: str = "https://testnet.campnetwork.xyz/api/snag/user", cf_clearance: str = None, session_token: str = None) -> str:
    """Fetch userId by wallet address via API."""
    time.sleep(2)
    public_address = private_key_to_address(wallet)
    if not public_address:
        logger.error(f"Failed to get address for {wallet[:10]}...")
        return ""

    try:
        headers = {
            "accept": "*/*",
            "accept-language": "ru,en-US;q=0.9,en;q=0.8,ru-RU;q=0.7,zh-TW;q=0.6,zh;q=0.5,uk;q=0.4",
            "priority": "u=1, i",
            "referer": "https://loyalty.campnetwork.xyz/loyalty",
            "sec-ch-ua": '"Chromium";v="133", "Google Chrome";v="133", "Not.A/Brand";v="99"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        }

        params = {
            "limit": "1000",
            "websiteId": "32afc5c9-f0fb-4938-9572-775dee0b4a2b",
            "organizationId": "26a1764f-5637-425e-89fa-2f3fb86e758c",
            "walletAddress": public_address,
        }

        response = session.get(
            "https://testnet.campnetwork.xyz/api/snag/user",
            params=params,
            cookies={"cf_clearance": cf_clearance},
            headers=headers,
        )
        
        if "Just a moment" in response.text:
            logger.error(f"Cloudflare challenge when fetching user_id for {public_address[:8]}...")
            return ""
        
        data = response.json()
        
        user_id = data.get("data", [{}])[0].get("id", "")
    
        if not user_id:
            logger.error(f"userId not found for {public_address[:8]}...")
        else:
            logger.info(f"Got userId: {user_id[:8]}... for {public_address[:8]}...")
        return user_id
    except Exception as e:
        logger.error(f"Failed to fetch userId for {public_address[:8]}...: {e}")
        return ""

def save_result(account: str, quest: dict, status: str, response_text: str = "") -> None:
    """Save quest result."""
    logger.info(f"Account {account[:8]}... | Quest {quest.get('ruleId')} | Status: {status}")