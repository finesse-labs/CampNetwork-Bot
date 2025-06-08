# src/quest_sender.py
import requests
import base64
import json
import urllib3
import string
import random
from typing import *
from .utils import logger, random_delay
from .faucet import FaucetService
from .tasks.bleetz import Bleetz
from .tasks.pictographs import Pictographs
from config import QUEST_API_URL, TWITTER_API_URL, BEARER_TOKEN, QUEST_DELAY, CLAIM_DELAY

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_ct0(session: requests.Session, auth_token: str, extra_cookies: Dict[str, str] = None, proxy: str = None) -> Optional[str]:
    """Fetches ct0 via GET request to x.com, extracting it even if status isn't 200."""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            session.cookies.clear()
            session.cookies.set('auth_token', auth_token)
            if extra_cookies:
                for key, value in extra_cookies.items():
                    session.cookies.set(key, value)
            headers = {
                "authorization": f"Bearer {BEARER_TOKEN}",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                "accept": "*/*",
                "origin": "https://x.com",
                "referer": "https://x.com/",
            }
            proxies = {"http": proxy, "https": proxy} if proxy else None
            response = session.get("https://x.com", headers=headers, proxies=proxies, verify=False, timeout=15)
            ct0 = session.cookies.get("ct0")
            logger.debug(f"[Attempt {attempt + 1}] Response: HTTP {response.status_code}, Cookies: {session.cookies.get_dict()}")
            if ct0:
                logger.info(f"Successfully fetched ct0: {ct0[:8]}...")
                return ct0
            logger.warning(f"[Attempt {attempt + 1}] ct0 not found in response (HTTP {response.status_code})")
            if attempt < max_attempts - 1:
                logger.warning("Retrying ct0 fetch...")
                continue
            logger.error(f"Failed to fetch ct0: HTTP {response.status_code}, Response: {response.text[:100]}...")
            return None
        except Exception as e:
            logger.error(f"[Attempt {attempt + 1}] Error fetching ct0: {e}")
            if attempt < max_attempts - 1:
                continue
            return None
    logger.error("Max attempts reached for ct0 fetch")
    return None

def update_cookies(session: requests.Session, auth_token: str, extra_cookies: Dict[str, str] = None) -> Optional[str]:
    """Updates ct0 from session cookies, clearing unnecessary cookies."""
    try:
        ct0 = session.cookies.get("ct0")
        if not ct0:
            logger.error("ct0 not found in session cookies")
            return None
        session.cookies.clear()
        session.cookies.set('auth_token', auth_token)
        if extra_cookies:
            for key, value in extra_cookies.items():
                session.cookies.set(key, value)
        session.cookies.set("ct0", ct0)
        logger.debug(f"Updated cookies: {session.cookies.get_dict()}")
        return ct0
    except Exception as e:
        logger.error(f"Error updating cookies: {e}")
        return None

def verify_error_response(response_text: str, account) -> tuple[bool, str]:
    """Checks response for errors and returns whether to continue and account status."""
    if "this account is temporarily locked" in response_text:
        logger.error(f"Account {account['auth_token']} Account temporarily locked")
        return False, "locked"
    if "Could not authenticate you" in response_text:
        logger.error(f"Account {account['auth_token']} Invalid auth_token")
        return False, "wrong_token"
    if "to protect our users from spam" in response_text:
        logger.error(f"Account {account['auth_token']} Account suspended")
        return False, "suspended"
    if "Rate limit exceeded" in response_text:
        logger.error(f"Account {account['auth_token']} Rate limit exceeded")
        return False, "rate_limited"
    logger.error(f"Account {account['auth_token']} Unknown error: {response_text[:100]}...")
    return True, "unknown"


def generate_client_transaction_id() -> str:
    """Generate 64-char x-client-transaction-id."""
    chars = string.ascii_letters + string.digits + '/+'
    return ''.join(random.choice(chars) for _ in range(64))

def create_tweet(session, account: dict, tweet_text: str, proxy: str) -> bool:
    """Create post on X.com."""
    cookies_dict = decode_cookies(account['cookies_base64'])
    required_keys = ['auth_token', 'ct0', '_twitter_sess', 'twid']
    if not validate_cookies(cookies_dict, required_keys):
        return False

    headers = {
        "authorization": f"Bearer {BEARER_TOKEN}",
        "x-csrf-token": cookies_dict["ct0"],
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-active-user": "yes",
        "x-client-transaction-id": generate_client_transaction_id(),
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "content-type": "application/json",
        "accept": "*/*",
        "origin": "https://x.com",
        "referer": "https://x.com/home",
    }

    payload = {
        "variables": {
            "tweet_text": tweet_text,
            "dark_request": False,
            "media": {"media_entities": [], "possibly_sensitive": False},
            "semantic_annotation_ids": [],
        },
        "features": {
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "rweb_tipjar_consumption_enabled": True,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
        },
        "queryId": "eX0PqfsNKJZ1jAgyP_rHjQ"
    }

    url = "https://x.com/i/api/graphql/eX0PqfsNKJZ1jAgyP_rHjQ/CreateTweet"
    proxies = {"http": proxy, "https": proxy}

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response = session.post(url, headers=headers, json=payload, cookies=cookies_dict, proxies=proxies, verify=False, timeout=30)
            if response.status_code == 200:
                logger.info(f'Tweet created successfully: {tweet_text[:30]}...')
                return True
            elif response.status_code in (401, 403):
                logger.warning(f'Tweet creation failed (HTTP {response.status_code}), attempting to refresh ct0')
                new_ct0 = attempt_ct0_refresh(session, account, proxy)
                if new_ct0:
                    headers['x-csrf-token'] = new_ct0
                    cookies_dict['ct0'] = new_ct0
                    continue
                logger.error('Failed to refresh ct0, aborting tweet creation')
                return False
            else:
                logger.error(f'Tweet creation failed: HTTP {response.status_code}, {response.text}')
                return False
        except Exception as e:
            logger.error(f'Tweet creation error (attempt {attempt + 1}): {e}')
            if attempt < max_attempts - 1:
                continue
            return False
    logger.error('Max attempts reached for tweet creation')
    return False

def follow_twitter_user(session, account: dict, target_user_id: str, proxy: str) -> bool:
    """Follow Twitter account."""
    auth_token = account.get('auth_token')
    extra_cookies = account.get('extra_cookies', {})
    ct0 = account.get('ct0')
    if not auth_token:
        logger.error(f"Account {account['auth_token']} Missing auth_token")
        account['status'] = 'wrong_token'
        return False
    if not ct0:
        logger.error(f"Account {account['auth_token']} Missing ct0, cannot proceed")
        account['status'] = 'wrong_token'
        return False
    
    headers = {
        "authorization": f"Bearer {BEARER_TOKEN}",
        "x-csrf-token": ct0,
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-active-user": "yes",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "content-type": "application/x-www-form-urlencoded",
        "accept": "*/*",
        "origin": "https://twitter.com",
        "referer": "https://twitter.com/",
    }
    payload = {"user_id": target_user_id, "follow": "true"}
    proxies = {"http": proxy, "https": proxy}

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            random_delay([0.1, 0.2])
            session.cookies.clear()
            session.cookies.set('auth_token', auth_token)
            if extra_cookies:
                for key, value in extra_cookies.items():
                    session.cookies.set(key, value)
            session.cookies.set("ct0", ct0)
            response = session.post(TWITTER_API_URL, headers=headers, data=payload, proxies=proxies, verify=False, timeout=30)
            new_ct0 = update_cookies(session, auth_token, extra_cookies)
            if new_ct0:
                account['ct0'] = new_ct0
                ct0 = new_ct0
                headers["x-csrf-token"] = ct0

            if response.status_code == 200:
                logger.info(f"Account {account['auth_token']} Successfully followed user {target_user_id[:8]}...")
                return True
            elif response.status_code in (401, 403):
                logger.warning(f"Account {account['auth_token']} Follow failed (HTTP {response.status_code}), retrying with new ct0")
                should_continue, account_status = verify_error_response(response.text, account)
                if not should_continue:
                    account['status'] = account_status
                    return False
                new_ct0 = fetch_ct0(session, auth_token, extra_cookies, proxy)
                if new_ct0:
                    account['ct0'] = new_ct0
                    ct0 = new_ct0
                    headers["x-csrf-token"] = ct0
                    continue
                account['status'] = 'wrong_token'
                return False
            else:
                logger.error(f"Account {account['auth_token']} Follow failed: HTTP {response.status_code}, {response.text[:100]}...")
                return False
        except Exception as e:
            logger.error(f"Account {account['auth_token']} Follow error (attempt {attempt + 1}): {e}")
            if attempt < max_attempts - 1:
                continue
            return False
    logger.error(f"Account {account['auth_token']} Max attempts reached for follow action")
    return False

def complete_quest(auth, session, user_id: str, quest: dict, proxy: str, cf_clearance: str, session_token: str) -> bool:
    """Send quest completion request."""
    headers = {
        "accept": "application/json, text/plain, */*",
        "origin": "https://loyalty.campnetwork.xyz",
        "referer": "https://loyalty.campnetwork.xyz/loyalty",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    }
    cookies = {
        "cf_clearance": cf_clearance,
        "__Secure-next-auth.session-token": session_token,
        "__Secure-next-auth.callback-url": "https%3A%2F%2Floyalty.campnetwork.xyz",
    } if cf_clearance and session_token else {}
    data = {"ruleId": quest["ruleId"], "userId": user_id}
    proxies = {"http": proxy, "https": proxy} if proxy else None

    try:
        response = session.post(
            QUEST_API_URL,
            json=data,
            headers=headers,
            cookies=cookies,
            proxies=proxies
        )
        if "Just a moment" in response.text:
            logger.error(f"Cloudflare challenge for quest {quest.get('name', quest['ruleId'])}")
            auth.login()
            cf_clearance, session_token = auth.login()
            return complete_quest(auth, session, user_id, quest, proxy, cf_clearance, session_token)
            
        if response.status_code == 200:
            logger.info(f"Quest {quest.get('name', quest['ruleId'])} ({quest['type']}) completed")
        else:
            logger.error(f"Failed to complete quest {quest.get('name', quest['ruleId'])}: {response.status_code} | {response.text}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to complete quest {quest.get('name', quest['ruleId'])} ({quest['type']}): {e}")
        return False

def process_quest(account: dict, auth, session, user_id: str, quest: dict, wallet: str, proxy: str, cf_clearance: str, session_token: str) -> None:
    """Process single quest for account."""
    quest_name = quest.get('name', quest['ruleId'] or 'unknown')
    quest_type = quest.get('type', 'unknown')
    logger.info(f"Processing quest {quest_name} ({quest_type})")

    # Fetch ct0 once at the start if not present
    if 'ct0' not in account:
        auth_token = account.get('auth_token')
        extra_cookies = account.get('extra_cookies', {})
        if not auth_token:
            logger.error(f"Account {account['auth_token']} Missing auth_token")
            account['status'] = 'wrong_token'
            return
        ct0 = fetch_ct0(session, auth_token, extra_cookies, proxy)
        if not ct0:
            logger.error(f"Account {account['auth_token']} Failed to fetch ct0")
            account['status'] = 'wrong_token'
            return
        account['ct0'] = ct0

    if quest_type == "follow":
        if not quest.get("user_id"):
            logger.error(f"Quest {quest_name} (follow) missing user_id")
            return
        if follow_twitter_user(session, account, quest["user_id"], proxy):
            logger.info(f"Followed user {quest['user_id'][:8]}... for {quest_name}")
            random_delay(CLAIM_DELAY)
        else:
            logger.error(f"Failed to follow for {quest_name}")
            return
    elif quest_type == "social":
        task_id = quest.get("task_id")
        if task_id == "scoreplay_post":
            tweet_text = "Final : I won on ScorePlay!"
            if create_tweet(session, account, tweet_text, proxy):
                logger.info(f"Tweet posted for {quest_name} (scoreplay_post)")
                random_delay(CLAIM_DELAY)
                if quest.get("ruleId"):
                    if complete_quest(auth, session, user_id, quest, proxy, cf_clearance, session_token):
                        logger.info(f"Quest {quest_name} (social) completed")
                    else:
                        logger.error(f"Failed to claim {quest_name} (social)")
                else:
                    logger.error(f"Quest {quest_name} (social) missing ruleId")
            else:
                logger.error(f"Failed to post tweet for {quest_name} (scoreplay_post)")
                return
        else:
            if complete_quest(auth, session, user_id, quest, proxy, cf_clearance, session_token):
                logger.info(f"Quest {quest_name} (social) completed")
            else:
                logger.error(f"Failed to claim {quest_name} (social)")
            return
    elif quest_type == "faucet":
        faucet_service = FaucetService(wallet=wallet, session=session, proxy=proxy)
        if faucet_service.request_faucet():
            logger.info(f"Faucet requested for {quest_name}")
            if quest.get("ruleId"):
                random_delay(CLAIM_DELAY)
            else:
                return
        else:
            logger.error(f"Failed to request faucet for {quest_name}")
            return
    elif quest_type == "custom":
        task_id = quest.get("task_id")
        if task_id == "bleetz_mint":
            bleetz = Bleetz(wallet=wallet, proxy=proxy)
            if bleetz.mint_nft():
                logger.info(f"Task {quest_name} (bleetz_mint) completed")
                if quest.get("ruleId"):
                    random_delay(CLAIM_DELAY)
                else:
                    return
            else:
                logger.error(f"Failed to complete task {quest_name} (bleetz_mint)")
                return
        elif task_id == "pictographs_mint":
            pictographs = Pictographs(wallet=wallet, proxy=proxy)
            if pictographs.mint_nft():
                logger.info(f"Task {quest_name} (pictographs_mint) completed")
                if quest.get("ruleId"):
                    random_delay(CLAIM_DELAY)
                else:
                    return
            else:
                logger.error(f"Failed to complete task {quest_name} (pictographs_mint)")
                return
        else:
            logger.error(f"Unknown custom task {task_id} for {quest_name}")
            return
    else:
        logger.error(f"Unknown quest type: {quest_type}")
        return

    if quest.get("ruleId") and quest_type != "social":
        if complete_quest(auth, session, user_id, quest, proxy, cf_clearance, session_token):
            logger.info(f"Quest {quest_name} ({quest_type}) claimed")
        else:
            logger.error(f"Failed to claim {quest_name} ({quest_type})")