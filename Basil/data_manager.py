import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import logging
from logging import getLogger

logger = getLogger(__name__)

# ✅ Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get Basil's main directory
SHARED_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "..", "shared_inventories"))

BASE_FOLDER = "inventory"
DEFAULTS_FOLDER = "default_game_files"

STATS_FILE = os.path.join(SHARED_FOLDER, "player_stats.json")

REQUIRED_FILES = {
    "ingredients.json": {},
    "recipes.json": {},
    "terrain_tables.json": {},
    "market.json": {"last_update": 0},
    "gold_data.json": {},
    "player_stats.json": {},
    "crafted_items.json": {},  # ✅ Basil's crafting inventory
    "in_game_time.json": {"days": 0, "hours": 0},  # ✅ Tracks game time
    "player_cooldowns.json": {}, # ✅ Tracks player cooldowns
}

def ensure_file_exists(filename, folder=BASE_FOLDER):
    """Ensures a required file exists, copying from defaults or creating an empty one."""
    file_path = os.path.join(folder, filename)
    default_path = os.path.join(DEFAULTS_FOLDER, filename)

    if not os.path.exists(file_path):
        os.makedirs(folder, exist_ok=True)  # ✅ Ensure the directory exists

        if os.path.exists(default_path):
            with open(default_path, "r", encoding="utf-8") as src, open(file_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())  # ✅ Copy the default file
            logger.info(f"📄 Created `{filename}` from defaults.")
        else:
            # ✅ Create an empty file with predefined structure
            if filename in REQUIRED_FILES:
                with open(file_path, "w", encoding="utf-8") as dst:
                    json.dump(REQUIRED_FILES[filename], dst, indent=4)
                logger.warning(f"⚠️ `{filename}` was missing! Created an empty one.")

def load_json(filename, folder=BASE_FOLDER, retry=True):
    """Loads a JSON file, ensuring it exists first."""
    filename = os.path.basename(filename)
    ensure_file_exists(filename, folder)
    file_path = os.path.join(folder, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as e:        
        if retry:  # Prevent infinite recursion
            logger.error(f"❌ `{filename}` is corrupted! Resetting to default. Error: {e}")
            os.remove(file_path)
            return load_json(filename, folder, retry=False)  # Try once
        else:
            logger.critical(f"⚠️ `{filename}` failed to reload! Creating a blank version.")
            return REQUIRED_FILES.get(filename, {})  # Fallback to empty structure

def save_json(filename, data, folder=None):
    """Saves data to a JSON file."""
    if folder is None:
        folder = BASE_FOLDER 

    file_path = os.path.join(folder, filename)

    try:
        os.makedirs(folder, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        logger.info(f"✅ Saved `{filename}` to `{folder}`.")
    except Exception as e:
        logger.error(f"❌ Failed to save `{filename}` to `{folder}`. Error: {e}")

class PlayerStats(commands.Cog):
    """Handles player stat tracking for Basil's crafting system."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_basil_stats", description="Set your intelligence, wisdom, proficiency bonus, and tool proficiencies.")
    async def set_basil_stats(
        self,
        interaction: discord.Interaction,
        intelligence: int,
        wisdom: int,
        proficiency: int,
        proficient: bool,
        herbalism_kit: bool,
        alchemist_tools: bool
    ):
        """Players set their intelligence & wisdom modifiers, proficiency bonus, and tool proficiencies."""
        user_id = str(interaction.user.id)
        stats = load_json(STATS_FILE)

        # ✅ Update player's stats
        stats[user_id] = {
            "intelligence_mod": intelligence,
            "wisdom_mod": wisdom,
            "proficiency_bonus": proficiency,
            "proficient": proficient,  # Covers both Herbalism & Alchemy
            "herbalism_kit": herbalism_kit,
            "alchemist_tools": alchemist_tools
        }

        # ✅ Save to file
        save_json(STATS_FILE, stats)

        # ✅ Confirm update
        await interaction.response.send_message(
            f"✅ **Stats updated!**\n"
            f"📜 **Intelligence Modifier:** `{intelligence}`\n"
            f"🧠 **Wisdom Modifier:** `{wisdom}`\n"
            f"🎖️ **Proficiency Bonus:** `{proficiency}`\n"
            f"🔬 **Proficient in Herbalism & Alchemy:** `{proficient}`\n"
            f"🌿 **Herbalism Kit Proficiency:** `{herbalism_kit}`\n"
            f"⚗️ **Alchemist Tools Proficiency:** `{alchemist_tools}`"
        )

async def setup(bot):
    cog = PlayerStats(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")