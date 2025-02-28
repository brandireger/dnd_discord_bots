import json
import os
import logging
from logging import getLogger

logger = getLogger(__name__)

# ✅ Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get Basil's main directory
SHARED_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "..", "shared_inventories"))  # ✅ Shared data for Basil & Stanley
BASIL_DATA_FOLDER = os.path.join(BASE_DIR, "basil_data")  # ✅ Basil-specific files
DEFAULTS_FOLDER = os.path.join(BASE_DIR, "default_game_files")  # ✅ Backup files

# ✅ Required Files & Default Data
REQUIRED_FILES = {
    "ingredients.json": (BASIL_DATA_FOLDER, {}),  
    "recipes.json": (BASIL_DATA_FOLDER, {}),  
    "terrain_tables.json": (BASIL_DATA_FOLDER, {}),  
    "market.json": (SHARED_FOLDER, {"last_update": 0}),  
    "gold_data.json": (SHARED_FOLDER, {}),  
    "player_stats.json": (SHARED_FOLDER, {}),  
    "crafted_items.json": (BASIL_DATA_FOLDER, {}),  # ✅ Basil's crafting inventory
    "in_game_time.json": (BASIL_DATA_FOLDER, {"days": 0, "hours": 0}),  # ✅ Tracks game time
    "player_cooldowns.json": (BASIL_DATA_FOLDER, {}),  # ✅ Tracks player cooldowns
    "basil_inventory.json": (SHARED_FOLDER, {}),  # ✅ Fixed missing inventory file
    "enhanced_recipes.json": (BASIL_DATA_FOLDER, {}),  
    "responses.json": (BASIL_DATA_FOLDER, {}),
    "player_inventories.json": (SHARED_FOLDER, {})
}

def ensure_file_exists(filename):
    """Ensures a required file exists, copying from defaults or creating an empty one."""
    if filename not in REQUIRED_FILES:
        logger.error(f"⚠️ `{filename}` is not in REQUIRED_FILES! Check path definitions.")
        return

    folder, default_content = REQUIRED_FILES[filename]  # ✅ Get correct folder & default structure
    file_path = os.path.join(folder, filename)
    default_path = os.path.join(DEFAULTS_FOLDER, filename)

    if not os.path.exists(file_path):
        os.makedirs(folder, exist_ok=True)  # ✅ Ensure directory exists

        if os.path.exists(default_path):
            with open(default_path, "r", encoding="utf-8") as src, open(file_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())  # ✅ Copy default file
            logger.info(f"📄 Created `{filename}` from defaults.")
        else:
            with open(file_path, "w", encoding="utf-8") as dst:
                json.dump(default_content, dst, indent=4)  # ✅ Create empty file
            logger.warning(f"⚠️ `{filename}` was missing! Created an empty one.")

def load_json(filename, retry=True):
    """Loads a JSON file, ensuring it exists first."""
    if filename not in REQUIRED_FILES:
        logger.error(f"⚠️ `{filename}` is not in REQUIRED_FILES! Check path definitions.")
        return None

    folder, _ = REQUIRED_FILES[filename]  # ✅ Get correct folder
    file_path = os.path.join(folder, filename)

    ensure_file_exists(filename)  # ✅ Ensure file exists before loading

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        if retry:  # Prevent infinite recursion
            logger.error(f"❌ `{filename}` is corrupted! Resetting to default. Error: {e}")
            os.remove(file_path)
            return load_json(filename, retry=False)  # ✅ Try once more
        else:
            logger.critical(f"⚠️ `{filename}` failed to reload! Creating a blank version.")
            return REQUIRED_FILES.get(filename, (None, {}))[1]  # ✅ Return default structure

def save_json(filename, data):
    """Saves data to a JSON file."""
    if filename not in REQUIRED_FILES:
        logger.error(f"⚠️ `{filename}` is not in REQUIRED_FILES! Check path definitions.")
        return

    folder, _ = REQUIRED_FILES[filename]  # ✅ Get correct folder
    file_path = os.path.join(folder, filename)

    try:
        os.makedirs(folder, exist_ok=True)  # ✅ Ensure directory exists
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        logger.info(f"✅ Saved `{filename}` to `{folder}`.")
    except Exception as e:
        logger.error(f"❌ Failed to save `{filename}` to `{folder}`. Error: {e}")

def reset_data(target: str):
    """Resets recipes, ingredients, or both."""
    if target.lower() not in ["recipes", "ingredients", "all"]:
        return "❌ Invalid option. Choose from: recipes, ingredients, or all."

    if target.lower() in ["recipes", "all"]:
        save_json("recipes.json", load_json("recipes.json"))
        logger.info("Recipes reset to default.")

    if target.lower() in ["ingredients", "all"]:
        save_json("ingredients.json", load_json("ingredients.json"))
        logger.info("Ingredients reset to default.")

    return f"✅ **{target.capitalize()} reset successfully!**"