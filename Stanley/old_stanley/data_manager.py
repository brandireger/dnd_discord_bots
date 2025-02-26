import json
import os
import pandas as pd
import discord
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def log_transaction(action, user, item, price_gp):
    """Logs a transaction event."""
    logging.info(f"{user} {action} {item} for {price_gp}gp.")

# Load Stanley's responses
RESPONSES_FILE = "data/stanley_responses.json"

def get_response(category, **kwargs):
    """Fetches a random response from Stanley's response file, replacing placeholders."""
    try:
        with open(RESPONSES_FILE, "r") as f:
            responses = json.load(f)
        if category in responses:
            return random.choice(responses[category]).format(**kwargs)
    except FileNotFoundError:
        return f"⚠️ Error: Response file `{RESPONSES_FILE}` not found!"
    except KeyError:
        return f"⚠️ Error: Response category `{category}` not found!"

# Load configuration settings (to be placed in `config.json`)
CONFIG_FILE = "config.json"
DATA_FOLDER = "data"

# Ensure data folder exists
os.makedirs(DATA_FOLDER, exist_ok=True)

# Define paths for JSON files
GOLD_FILE = os.path.join(DATA_FOLDER, "gold_data.json")
PLAYER_INVENTORY_FILE = os.path.join(DATA_FOLDER, "player_inventories.json")
SHOP_FILE = os.path.join(DATA_FOLDER, "stocked_advGear.json")
REQUESTS_FILE = os.path.join(DATA_FOLDER, "requests.json")
REQUESTABLE_ITEMS_FILE = os.path.join(DATA_FOLDER, "requestable_items.json")  # Stores what can be requested

def load_config():
    """Loads bot configuration from config.json."""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ Config file not found! Creating a default one.")
        default_config = {
            "starting_gold": {"gp": 10, "sp": 0, "cp": 0},
            "csv_file": "AdventuringItems.csv",
            "audit_channel_id": 1234567890  # Replace with actual channel ID
        }
        save_config(default_config)
        return default_config

def save_config(config):
    """Saves the config settings to config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def load_json(file_path, default_data=None):
    """Loads JSON data from a file, creating a default if missing or corrupted."""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"⚠️ Warning: {file_path} missing or corrupted. Resetting to default.")
        save_json(file_path, default_data if default_data is not None else {})
        return default_data if default_data is not None else {}

def save_json(file_path, data):
    """Saves JSON data safely using a temporary file to prevent corruption."""
    temp_file = f"{file_path}.tmp"
    try:
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_file, file_path)  # ✅ Safely replace original file
    except Exception as e:
        print(f"❌ Error saving {file_path}: {e}")

def load_shop_items():
    """Loads categorized shop items from JSON with error handling."""
    try:
        with open(SHOP_FILE, "r") as f:
            return json.load(f) or {}  # ✅ Ensure `{}` is returned even if file is empty
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"⚠️ Error: {SHOP_FILE} is missing or corrupted. Resetting shop data.")
        save_json(SHOP_FILE, {})  # ✅ Reset file to empty dictionary
        return {}

def ensure_currency(user_id):
    """Ensures a player has a valid currency balance. Initializes if missing."""
    global gold_data  # Ensure we're modifying the global variable

    if user_id not in gold_data or not isinstance(gold_data[user_id], dict):
        gold_data[user_id] = config["starting_gold"].copy()
    else:
        for key in ["gp", "sp", "cp"]:
            gold_data[user_id].setdefault(key, 0)

    save_json(GOLD_FILE, gold_data)  # ✅ Immediately save changes

def save_shop_items(data):
    """Saves updated shop data (including stock levels)."""
    with open(SHOP_FILE, "w") as f:
        json.dump(data, f, indent=4)

async def log_transaction(bot, message: str):
    """Logs a transaction to the audit channel and console."""
    print(f"📜 AUDIT: {message}")  # ✅ Always log to console for debugging

    channel_id = config.get("audit_channel_id")
    if not channel_id:
        print("⚠️ Warning: No audit channel ID set in config.")
        return

    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"📜 {message}")
    else:
        print(f"⚠️ Warning: Audit channel {channel_id} not found. Check bot permissions.")
        
def load_requests():
    """Loads all item requests from JSON."""
    return load_json(REQUESTS_FILE, {"mundane": {}, "magical": {}})

def save_requests(data):
    """Saves updated request data."""
    save_json(REQUESTS_FILE, data)

# Load bot settings
config = load_config()

# Load existing player data or create defaults
gold_data = load_json(GOLD_FILE, {})
SHOP_CATEGORIES = load_shop_items()
PLAYER_INVENTORIES = load_json(PLAYER_INVENTORY_FILE, {})