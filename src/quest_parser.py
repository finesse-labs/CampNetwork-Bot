# src/quest_parser.py
import json
from .utils import logger

def parse_api_quests(response_text: str) -> list:
    """Parse quests from API response at loyalty.campnetwork.xyz/api/loyalty/rule_groups."""
    try:
        data = json.loads(response_text)
        if not isinstance(data, dict) or "data" not in data:
            logger.error("Invalid API response format: missing 'data'")
            return []

        quests = []
        for group in data["data"]:
            group_name = group.get("name", "Unknown")
            for item in group.get("loyaltyGroupItems", []):
                rule = item.get("loyaltyRule", {})
                rule_id = rule.get("id")
                if not rule_id:
                    logger.warning(f"Skipped quest without ruleId in group {group_name}")
                    continue
                
                quest_type = rule.get("type")
                if not quest_type:
                    logger.warning(f"Skipped quest type for ruleId {rule_id}")
                    continue
                
                # Normalize types to match quests.json
                type_mapping = {
                    "drip_x_follow": "follow",
                    "link_click": "social",
                    "smart_contract_event": "custom",
                }
                normalized_type = type_mapping.get(quest_type, quest_type)

                quests.append({
                    "ruleId": rule_id,
                    "name": rule.get("name", "Unknown"),
                    "type": normalized_type,
                    "metadata": rule.get("metadata", {}),
                    "group_name": group_name,
                })
        
        logger.info(f"Extracted {len(quests)} quests from API")
        return quests
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON API response")
        return []
    except Exception as e:
        logger.error(f"Error parsing API quests: {e}")
        return []