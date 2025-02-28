import json
import time
import os
import logging
from logging import getLogger
from datetime import datetime
import random

logger = getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)  # ✅ Moves up one level to access shared data
INVENTORY_DIR = os.path.join(BASE_DIR, "inventory")  # General inventory
SHARED_DIR = os.path.join(PARENT_DIR, "shared_inventories")  # ✅ Corrected path
STANLEY_DATA_DIR = os.path.join(BASE_DIR, "stanley_data")  # Unique Stanley files
DEFAULTS_DIR = os.path.join(BASE_DIR, "default_game_files")  # Backup files

# ✅ Required Files & Default Data
REQUIRED_FILES = {
    "gold_data.json": (SHARED_DIR, {}),  
    "player_stats.json": (SHARED_DIR, {}),  
    "shop_requests.json": (SHARED_DIR, []),  
    "stanley_shop.json": (SHARED_DIR, {}),  
    "inventory_logs.json": (SHARED_DIR, []),  
    "player_inventories.json": (SHARED_DIR, {}),
    "requestable_items.json": (STANLEY_DATA_DIR, {}),  
    "stanley_responses.json": (STANLEY_DATA_DIR, {}),  
    "requests.json": (STANLEY_DATA_DIR, {"mundane": {}, "magical": {}}),  
    "market.json": (DEFAULTS_DIR, {"last_update": 0}),  
}
 
def ensure_file_exists(filename):
    """Ensures required files exist, copying defaults or creating empty ones."""
    if filename not in REQUIRED_FILES:
        logger.error(f"⚠️ `{filename}` is not in REQUIRED_FILES! Check path definitions.")
        return

    folder, default_content = REQUIRED_FILES[filename]
    file_path = os.path.join(folder, filename)
    default_path = os.path.join(DEFAULTS_DIR, filename)

    if not os.path.exists(file_path):
        os.makedirs(folder, exist_ok=True)  # Ensure directory exists

        if os.path.exists(default_path):
            with open(default_path, "r", encoding="utf-8") as src, open(file_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())  # Copy default file
            logger.info(f"📄 Created `{filename}` from defaults in `{folder}`.")
        else:
            # Create empty file with default structure
            with open(file_path, "w", encoding="utf-8") as dst:
                json.dump(default_content, dst, indent=4)
            logger.warning(f"⚠️ `{filename}` was missing! Created an empty one in `{folder}`.")

def load_json(filename):
    """Loads a JSON file, ensuring it exists first."""
    if filename not in REQUIRED_FILES:
        logger.error(f"⚠️ `{filename}` is not in REQUIRED_FILES! Check path definitions.")
        return None

    folder, default_data = REQUIRED_FILES[filename]  
    file_path = os.path.join(folder, filename)
    ensure_file_exists(filename)  # ✅ Ensure file exists before loading

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        logger.error(f"❌ `{filename}` is corrupted! Resetting to default. Error: {e}")
        os.remove(file_path)
        ensure_file_exists(filename)  # Recreate if corrupted
        return default_data  # Return default structure

def save_json(filename, data):
    """Saves data to a JSON file."""
    if filename not in REQUIRED_FILES:
        logger.error(f"⚠️ `{filename}` is not in REQUIRED_FILES! Check path definitions.")
        return

    folder, _ = REQUIRED_FILES[filename]  
    file_path = os.path.join(folder, filename)

    try:
        os.makedirs(folder, exist_ok=True)  
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        logger.info(f"✅ Saved `{filename}` to `{folder}`.")
    except Exception as e:
        logger.error(f"❌ Failed to save `{filename}` to `{folder}`. Error: {e}")

def get_response(category, **kwargs):
    """Fetches a random response from Stanley's response file, replacing placeholders."""
    responses = load_json("stanley_responses.json")

    if not responses or category not in responses or not responses[category]:
        return "⚠️ Error: Stanley's response file is missing or empty!"

    return random.choice(responses.get(category, ["🤔 Stanley scratches his head. _\"I wasn't prepared for that one!\"_"])).format(**kwargs)

def ensure_currency(user_id):
    """Ensures a player has a valid currency balance. Initializes if missing."""
    gold_data = load_json("gold_data.json")  # ✅ Load latest data

    if user_id not in gold_data or not isinstance(gold_data[user_id], dict):
        gold_data[user_id] = {"gp": 0, "sp": 0, "cp": 0}  # Default starting gold
    else:
        for key in ["gp", "sp", "cp"]:
            gold_data[user_id].setdefault(key, 0)

    save_json("gold_data.json", gold_data)  
    return gold_data[user_id]  

def generate_market():
    """Generates a fresh market with randomized base prices that last for one week."""
    market = {}    
    price_ranges = {"Common": (5, 15), "Uncommon": (15, 30), "Rare": (30, 50), "Very Rare": (50, 100)}
    ingredients = load_json("ingredients.json")

    for ingredient, data in ingredients.items():
        rarity = data.get("rarity", "Common")
        base_price = random.randint(*price_ranges.get(rarity, (5, 15)))

        market[ingredient] = {
            "base_price": base_price,
            "stock": random.randint(1, 5)
        }

    market["last_update"] = time.time()
    save_json("market.json", market)
    return market

def load_market():
    """Loads the market, regenerating it if a week has passed or file is missing."""
    market = load_json("market.json")
    if not market or (time.time() - market.get("last_update", 0) > 7 * 24 * 60 * 60):
        logger.info("🔄 Market refreshed after one week!")
        return generate_market()
    return market

def save_market(market_data):
    """Saves the current market state to file."""
    save_json("market.json", market_data)
    logger.info("✅ Market state saved.")

def log_transaction(action, user, item, price_gp):
    """Logs a transaction event and saves it to the audit log."""
    timestamp = datetime.utcnow().isoformat()
    audit_log = load_json("inventory_logs.json")

    if not isinstance(audit_log, list):  
        audit_log = [] 

    audit_log.append({"timestamp": timestamp, "user": user, "action": action, "item": item, "price_gp": price_gp})
    audit_log = audit_log[-50:]

    save_json("inventory_logs.json", audit_log)

# Load existing player data or create defaults
gold_data = load_json("gold_data.json")
SHOP_CATEGORIES = load_json("stanley_shop.json")
PLAYER_INVENTORIES = load_json("player_inventories.json")