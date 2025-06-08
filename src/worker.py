import random
import time
from .utils import get_user_id, random_delay, save_result, logger
from .quest_sender import process_quest
from .auth import Auth
from .quest_parser import parse_api_quests
from config import QUEST_DELAY, SHUFFLE_QUESTS


def filter_quests(local_quests: list, api_quests: list) -> list:
    """Filters local quests based on API data, keeping faucet and custom without ruleId."""
    api_rule_ids = {quest["ruleId"] for quest in api_quests if quest["ruleId"]}
    filtered_quests = []
    
    for quest in local_quests:
        quest_name = quest.get('name', 'unknown')
        quest_type = quest.get('type', 'unknown')
        
        # For faucet and custom without ruleId (with task_id), add without API check
        if quest_type == "faucet" or (quest_type == "custom" and not quest.get("ruleId") and quest.get("task_id")):
            filtered_quests.append(quest.copy())
            logger.info(f"Added quest {quest_name} ({quest_type}) without API check")
            continue
        
        # For quests with ruleId, check presence in API
        if quest.get("ruleId") and quest["ruleId"] in api_rule_ids:
            quest_copy = quest.copy()
            # Add metadata from API
            api_quest = next((q for q in api_quests if q["ruleId"] == quest["ruleId"]), None)
            if api_quest:
                quest_copy["metadata"] = api_quest.get("metadata", {})
                quest_copy["group_name"] = api_quest.get("group_name", "")
            filtered_quests.append(quest_copy)
            logger.info(f"Added quest {quest_name} ({quest_type}) with ruleId {quest['ruleId']}")
        else:
            logger.warning(f"Quest {quest_name} ({quest_type}) with ruleId {quest.get('ruleId', 'None')} not found in API, skipped")

    if not filtered_quests:
        logger.error("No quests available after filtering by API")
        return []
    
    if SHUFFLE_QUESTS:
        random.shuffle(filtered_quests)
    logger.info(f"✅ Filtered {len(filtered_quests)} quests for account")
    return filtered_quests


def process_account(account: dict, wallet: str, local_quests: list, proxy: str, captcha_api_key: str) -> None:
    """Processes a single account."""
    wallet_short = wallet[:10] + "..." if isinstance(wallet, str) else str(wallet)[:10] + "..."
    logger.info(f"Starting processing for account with wallet {wallet_short}")

    # Perform authorization
    auth = Auth(wallet, proxy, captcha_api_key)
    cf_clearance, session_token = auth.login()
    if not session_token:
        logger.error(f"Failed to authorize for wallet {wallet_short}")
        save_result(account, {}, "failed", "Authorization failed")
        return

    # Get user_id
    user_id = get_user_id(wallet, auth.session, cf_clearance=cf_clearance, session_token=session_token)
    if not user_id:
        logger.error(f"Failed to get user_id for wallet {wallet_short}")
        save_result(account, {}, "failed", "Error retrieving user_id")
        return
    
    # Get quests from API
    cookies = {
        "__Secure-next-auth.callback-url": "https%3A%2F%2Floyalty.campnetwork.xyz",
        "cf_clearance": cf_clearance,
        "__Secure-next-auth.session-token": session_token,
    }
    headers = {
        "accept": "*/*",
        "accept-language": "ru,en-US;q=0.9,en;q=0.8,ru-RU;q=0.7,zh-TW;q=0.6,zh;q=0.5,uk;q=0.4",
        "content-type": "application/json",
        "priority": "u=1, i",
        "referer": "https://loyalty.campnetwork.xyz/loyalty",
        "sec-ch-ua": '"Chromium";v="133", "Google Chrome";v="133", "Not.A/Brand";v="99"',
        "sec-ch-ua-arch": '"x86"',
        "sec-ch-ua-bitness": '"64"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-model": '""',
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-platform-version": '"19.0.0"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    }
    params = {
        "limit": "1000",
        "websiteId": "32afc5c9-f0fb-4938-9572-775dee0b4a2b",
        "organizationId": "26a1764f-5637-425e-89fa-2f3fb86e758c",
    }

    try:
        response = auth.session.get(
            "https://loyalty.campnetwork.xyz/api/loyalty/rule_groups",
            params=params,
            cookies=cookies,
            headers=headers,
            proxies={"http": proxy, "https": proxy} if proxy else None
        )
        api_quests = parse_api_quests(response.text)
        if not api_quests:
            logger.error(f"No quests retrieved from API for wallet {wallet_short}")
            save_result(account, {}, "failed", "No API quests available")
            return
    except Exception as e:
        logger.error(f"Failed to get API quests for wallet {wallet_short}: {e}")
        save_result(account, {}, "failed", "Error retrieving API quests")
        return

    # Filter local quests based on API
    filtered_quests = filter_quests(local_quests, api_quests)
    if not filtered_quests:
        logger.error(f"No quests available after filtering for wallet {wallet_short}")
        save_result(account, {}, "failed", "No quests after filtering")
        return
    

    # Process quests
    for quest in filtered_quests:
        random_delay(QUEST_DELAY)
        process_quest(account, auth, auth.session, user_id, quest, wallet, proxy, cf_clearance, session_token)
        
    
    logger.info(f"Finished processing for account with wallet {wallet_short}")
    random_delay([0.1, 0.2])