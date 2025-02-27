import json
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

GOLD_FILE = os.path.join(SHARED_DIR, "gold_data.json")
STATS_FILE = os.path.join(SHARED_DIR, "player_stats.json")
SHOP_REQUESTS_FILE = os.path.join(SHARED_DIR, "shop_requests.json")
REQUESTS_FILE = os.path.join(STANLEY_DATA_DIR, "requests.json")  
SHOP_FILE = os.path.join(SHARED_DIR, "stanley_shop.json")  
AUDIT_LOG_FILE = os.path.join(SHARED_DIR, "inventory_logs.json")  

# ✅ Required Files & Default Data
REQUIRED_FILES = {
    "gold_data.json": (SHARED_DIR, {}),  
    "player_stats.json": (SHARED_DIR, {}),  
    "shop_requests.json": (SHARED_DIR, []),  
    "stanley_shop.json": (SHARED_DIR, {}),  
    "inventory_logs.json": (SHARED_DIR, []),  
    "player_inventories.json": (SHARED_DIR, {}),
    
    # Stanley-specific data
    "requestable_items.json": (STANLEY_DATA_DIR, {}),  
    "stanley_responses.json": (STANLEY_DATA_DIR, {}),  
    "requests.json": (STANLEY_DATA_DIR, {"mundane": {}, "magical": {}}),  

    # Default backup files
    "market.json": (DEFAULTS_DIR, {"last_update": 0}),  
}
 
def ensure_file_exists(filename, folder=BASE_DIR):
    """Ensures required files exist, copying defaults or creating empty ones."""
    if filename not in REQUIRED_FILES:
        logger.error(f"⚠️ `{filename}` is not in REQUIRED_FILES! Check path definitions.")
        return

    folder, default_content = REQUIRED_FILES[filename]  # Get correct folder & default structure
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

def load_json(filename, folder=None):
    """Loads a JSON file, ensuring it exists first."""
    if filename not in REQUIRED_FILES:
        logger.error(f"⚠️ `{filename}` is not in REQUIRED_FILES! Check path definitions.")
        return None

    folder = folder or REQUIRED_FILES[filename][0]  # Default to predefined folder
    file_path = os.path.join(folder, filename)

    ensure_file_exists(filename)  # ✅ Ensure file exists before loading

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        logger.error(f"❌ `{filename}` is corrupted! Resetting to default. Error: {e}")
        os.remove(file_path)
        ensure_file_exists(filename)  # Recreate if corrupted
        return REQUIRED_FILES[filename][1]  # Return default structure

def save_json(filename, data):
    """Saves data to a JSON file."""
    if filename not in REQUIRED_FILES:
        logger.error(f"⚠️ `{filename}` is not in REQUIRED_FILES! Check path definitions.")
        return

    folder = folder or REQUIRED_FILES[filename][0]  # Default to predefined folder
    file_path = os.path.join(folder, filename)

    try:
        os.makedirs(folder, exist_ok=True)  # Ensure directory exists
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        logger.info(f"✅ Saved `{filename}` to `{folder}`.")
    except Exception as e:
        logger.error(f"❌ Failed to save `{filename}` to `{folder}`. Error: {e}")

def get_response(category, **kwargs):
    """Fetches a random response from Stanley's response file, replacing placeholders."""
    responses = load_json("stanley_responses.json", folder=STANLEY_DATA_DIR)

    if not responses:
        return "⚠️ Error: Stanley's response file is missing or empty!"

    return random.choice(responses.get(category, ["🤔 Stanley scratches his head. _\"I wasn't prepared for that one!\"_"])).format(**kwargs)

def load_shop_items():
    """Loads categorized shop items from JSON with error handling."""
    return load_json("stanley_shop.json", folder=SHARED_DIR)  # ✅ Uses `load_json()` for consistency

def save_shop_items(data):
    """Saves updated shop data (including stock levels)."""
    save_json("stanley_shop.json", data, folder=SHARED_DIR)

def load_requests():
    """Loads all item requests from JSON."""
    return load_json("requests.json", folder=STANLEY_DATA_DIR)

def save_requests(data):
    """Saves updated request data."""
    save_json("requests.json", data, folder=STANLEY_DATA_DIR)

def ensure_currency(user_id):
    """Ensures a player has a valid currency balance. Initializes if missing."""
    gold_data = load_json("gold_data.json", folder=SHARED_DIR)  # ✅ Load latest data

    if user_id not in gold_data or not isinstance(gold_data[user_id], dict):
        gold_data[user_id] = {"gp": 0, "sp": 0, "cp": 0}  # Default starting gold
    else:
        for key in ["gp", "sp", "cp"]:
            gold_data[user_id].setdefault(key, 0)

    save_json("gold_data.json", gold_data, folder=SHARED_DIR)  
    return gold_data[user_id]  

def log_transaction(action, user, item, price_gp):
    """Logs a transaction event and saves it to the audit log."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    log_message = f"[{timestamp}] {user} {action} {item} for {price_gp}gp."  
    logger.info(log_message)

    # ✅ Load & Update Audit Log
    audit_log = load_json("inventory_logs.json", folder=SHARED_DIR)
    audit_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "user": user,
        "action": action,
        "item": item,
        "price_gp": price_gp
    })

    # ✅ Keep only the last 50 transactions
    audit_log = audit_log[-50:]

    save_json("inventory_logs.json", audit_log, folder=SHARED_DIR)

# Load existing player data or create defaults
gold_data = load_json("gold_data.json", folder=SHARED_DIR)
SHOP_CATEGORIES = load_shop_items()
PLAYER_INVENTORIES = load_json("player_inventories.json", folder=SHARED_DIR)