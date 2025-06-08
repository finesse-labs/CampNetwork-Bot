# src/account_parser.py
import random
import json
import re
import sys
import time

from .utils import logger
from config import ALLOWED_QUEST_TYPES, TASKS, SHUFFLE_QUESTS

PRIVATE_KEY_PATTERN = re.compile(r"^0x[a-fA-F0-9]{64}$")
PROXY_PATTERN = re.compile(r"^http://[a-zA-Z0-9._-]+:[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+:\d+$")

def validate_and_load(file_path: str, pattern: re.Pattern = None, name: str = "", required: bool = True) -> list:
    """Validate and load items from a file."""
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            items = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        if required:
            logger.error(f"{file_path} not found! Create the file with valid {name}s.")
            sys.exit(1)
        else:
            logger.warning(f"{file_path} not found. Continuing without {name}s.")
            return []

    if not items:
        if required:
            logger.error(f"{file_path} is empty. No {name}s loaded.")
            sys.exit(1)
        else:
            logger.warning(f"{file_path} is empty. Continuing without {name}s.")
            return []

    if pattern:
        invalid_lines = [(i + 1, line) for i, line in enumerate(items) if not pattern.match(line)]
        if invalid_lines:
            for line_num, line in invalid_lines:
                logger.error(f"Invalid {name} at line {line_num}: {line}")
            logger.error(f"Expected pattern for {name}: {pattern.pattern}")
            sys.exit(1)

    logger.info(f"✅ Loaded {len(items)} valid {name}s.")
    time.sleep(0.75)
    return items

def load_file(file_path: str) -> list:
    """Read lines from file (used for non-validated files)."""
    try:
        with open(file_path, 'r', encoding="utf-8-sig") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error(f"File {file_path} not found")
        return []

def parse_accounts(config_dir: str, shuffle: bool = False) -> list:
    """Parse accounts from accounts.txt without validating auth_token or cookies_base64."""
    lines = load_file(f"{config_dir}/accounts.txt")
    accounts = []
    for i, line in enumerate(lines, 1):
        parts = line.split(':')
        if len(parts) < 1:
            logger.error(f"Invalid account format at line {i}: {line}")
            sys.exit(1)
        accounts.append({
            'auth_token': parts[0]
        })
    
    if shuffle:
        random.shuffle(accounts)
    logger.info(f"✅ Loaded {len(accounts)} valid accounts.")
    return accounts

def load_proxies(config_dir: str) -> list:
    """Load and validate proxies from proxies.txt."""
    return validate_and_load(f"{config_dir}/proxies.txt", PROXY_PATTERN, "proxy", required=False)

def load_wallets(config_dir: str) -> list:
    """Load and validate wallets from wallets.txt."""
    return validate_and_load(f"{config_dir}/wallets.txt", PRIVATE_KEY_PATTERN, "wallet", required=True)

def load_quests(data_dir: str, shuffle: bool = False) -> list:
    """Load and filter quests from quests.json based on ALLOWED_QUEST_TYPES and TASKS."""
    # Load quests
    try:
        with open(f"{data_dir}/quests.json", 'r', encoding="utf-8-sig") as f:
            quests = json.load(f)
    except FileNotFoundError:
        logger.error("File quests.json not found")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in quests.json")
        sys.exit(1)

    # Validate ALLOWED_QUEST_TYPES and TASKS
    valid_types = ["follow", "social", "custom", "faucet"]
    if not all(t in valid_types for t in ALLOWED_QUEST_TYPES):
        logger.error(f"Invalid quest types in ALLOWED_QUEST_TYPES: {ALLOWED_QUEST_TYPES}")
        sys.exit(1)
    if not all(t in valid_types for t in TASKS):
        logger.error(f"Invalid quest types in TASKS: {TASKS}")
        sys.exit(1)
    if not all(t in ALLOWED_QUEST_TYPES for t in TASKS):
        logger.error(f"Some types in TASKS {TASKS} are not in ALLOWED_QUEST_TYPES {ALLOWED_QUEST_TYPES}")
        sys.exit(1)

    # Filter quests by ALLOWED_QUEST_TYPES and TASKS
    filtered_quests = []
    for quest in quests:
        if not isinstance(quest, dict) or "type" not in quest or "name" not in quest:
            logger.warning(f"Skipping invalid quest: {quest}")
            continue
        if quest["type"] not in ALLOWED_QUEST_TYPES:
            continue
        if quest["type"] not in TASKS:
            continue
        filtered_quests.append(quest)

    if not filtered_quests:
        logger.error("No quests available after filtering by ALLOWED_QUEST_TYPES and TASKS")
        sys.exit(1)

    if shuffle:
        random.shuffle(filtered_quests)
    logger.info(f"✅ Loaded {len(filtered_quests)} quests after filtering (TASKS: {TASKS}).")
    return filtered_quests