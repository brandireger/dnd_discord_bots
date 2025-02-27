import discord
from discord import ui, app_commands
from discord.ext import commands
import random
import json
import logging
from logging import getLogger
from logging.handlers import RotatingFileHandler
import sys
import os
from data_manager import load_json, save_json
from inventory_functions import add_item, remove_item

# Configure logging
logger = getLogger(__name__)
handler = RotatingFileHandler("logs/basil_bot.log", maxBytes=5000000, backupCount=2)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Load necessary game data
INGREDIENTS = load_json("ingredients.json") or {}
TERRAIN_TABLES = load_json("terrain_tables.json") or {}
IN_GAME_TIME = load_json("in_game_time.json") or {}  # ✅ Tracks in-game hours/days
PLAYER_COOLDOWNS = load_json("player_cooldowns.json") or {}  # ✅ Tracks last gather/identify and remaining attempts
STATS_FILE = os.path.join("shared_inventories", "player_stats.json")

class TerrainSelect(ui.Select):
    """Dropdown menu for selecting a terrain type."""
    def __init__(self, interaction):
        options = [
            discord.SelectOption(label=terrain, value=terrain)
            for terrain in TERRAIN_TABLES.keys()
        ]

        super().__init__(placeholder="Choose a terrain to gather herbs...", min_values=1, max_values=1, options=options)
        self.interaction = interaction

    async def callback(self, interaction: discord.Interaction):
        """Handles the selection of a terrain type."""
        selected_terrain = self.values[0]
        await gather_execute(interaction, selected_terrain)

class TerrainView(ui.View):
    """View that contains the terrain selection dropdown."""
    def __init__(self, interaction: discord.Interaction):
        super().__init__()
        self.interaction = interaction  # ✅ Store interaction
        self.add_item(TerrainSelect(interaction))  # ✅ Pass interaction to TerrainSelect

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.interaction.user

class Herbalism(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gather", description="Gather herbs based on terrain type.")
    async def gather(self, interaction: discord.Interaction):
        """Asks the player to select a terrain type using a dropdown menu."""
        player_id = str(interaction.user.id)

        # ✅ Ensure player cooldown data exists
        if player_id not in PLAYER_COOLDOWNS:
            PLAYER_COOLDOWNS[player_id] = {"gather_attempts": 0, "last_gather_hour": -999}

        # ✅ Ensure in-game time is tracked
        if "hours" not in IN_GAME_TIME:
            IN_GAME_TIME["hours"] = 0
            IN_GAME_TIME["days"] = 0
            save_json("in_game_time.json", IN_GAME_TIME)

        # ✅ Check if player has remaining gather attempts
        if PLAYER_COOLDOWNS[player_id]["gather_attempts"] <= 0:
            await interaction.response.send_message("❌ You have no gathering attempts left. Wait for more in-game time to pass.")
            return

        if not TERRAIN_TABLES:
            await interaction.response.send_message("❌ No terrain data found. Admin should update `terrain_tables.json`.")
            return

        # ✅ Deduct one attempt
        PLAYER_COOLDOWNS[player_id]["gather_attempts"] -= 1
        save_json("player_cooldowns.json", PLAYER_COOLDOWNS)
        
        await interaction.response.send_message(
            "🌍 **Select a terrain to gather herbs from:**",
            view=TerrainView(interaction),
            ephemeral=True
        )

    @app_commands.command(name="identify", description="Identify an unknown herb with an Herbalism check.")
    async def identify(self, interaction: discord.Interaction, ingredient: str):
        """Allows players to identify herbs using their stats."""
        player_id = str(interaction.user.id)
        stats = load_json(STATS_FILE).get(player_id, {})
        ingredient = ingredient.lower().strip()

        # ✅ Normalize common ingredient names
        if "common ingredient" in ingredient:
            possible_common_ingredients = ["Wild Sageroot", "Mandrake Root", "Bloodgrass", "Milkweed Seeds"]
            identified_ingredient = random.choice(possible_common_ingredients)  # Pick one at random
            ingredient_to_remove = "Common Ingredient"  # Correct name in inventory
        else:
            identified_ingredient = next((key for key in INGREDIENTS.keys() if key.lower() == ingredient), None)
            ingredient_to_remove = identified_ingredient

        if not identified_ingredient:
            logger.warning(f"User {interaction.user} tried to identify an unknown ingredient: {ingredient}")
            await interaction.response.send_message("❌ That ingredient does not exist in my records.")
            return

        # ✅ Prevent KeyError: Ensure the ingredient exists in INGREDIENTS before accessing it
        ingredient_data = INGREDIENTS.get(identified_ingredient, None)
        if not ingredient_data:
            logger.error(f"⚠️ {identified_ingredient} exists in name matching but is missing from INGREDIENTS data!")
            await interaction.response.send_message("❌ I can't seem to find details on this ingredient. Check your spelling!")
            return

        # ✅ Check last identify time
        last_identify_day = PLAYER_COOLDOWNS.get(player_id, {}).get(f"identify_{ingredient}_day", -999)
        if IN_GAME_TIME["days"] - last_identify_day < 1:
            await interaction.response.send_message(f"❌ You have already attempted to identify **{ingredient}** today. Try again tomorrow.")
            return

        # ✅ Determine best stat (Wisdom OR Intelligence)
        best_mod = max(stats.get("wisdom", 0), stats.get("intelligence", 0))
        proficiency_bonus = stats.get("proficiency", 0) if stats.get("proficient", False) else 0
        kit_bonus = 2 if stats.get("herbalism_kit", False) else 0

        # ✅ Set Difficulty
        dc = 10 + ingredient_data.get("DC", 0)
        roll = random.randint(1, 20) + best_mod + proficiency_bonus + kit_bonus

        logger.info(f"User {interaction.user} rolled {roll} vs DC {dc} to identify {identified_ingredient}.")

        if roll >= dc:
            # ✅ Success: Update inventory
            logger.info(f"User {interaction.user} successfully identified {identified_ingredient}.")
            remove_item(player_id, ingredient_to_remove, 1)  # Remove the unidentified version
            add_item(player_id, identified_ingredient, 1)  # Add identified herb
            PLAYER_COOLDOWNS.setdefault(player_id, {})[f"identify_{ingredient}_day"] = IN_GAME_TIME["days"]
            save_json("player_cooldowns.json", PLAYER_COOLDOWNS)

            await interaction.response.send_message(f"✅ Success! You identify **{identified_ingredient}**: {INGREDIENTS[identified_ingredient]['effect']}")
        else:
            # ❌ Failure
            logger.info(f"User {interaction.user} failed to identify {ingredient}.")
            PLAYER_COOLDOWNS.setdefault(player_id, {})[f"identify_{ingredient}_day"] = IN_GAME_TIME["days"]
            save_json("player_cooldowns.json", PLAYER_COOLDOWNS)
            await interaction.response.send_message("❌ You failed to identify the herb. Try again later!")
            
async def gather_execute(interaction: discord.Interaction, terrain: str):
    """Handles the actual herb gathering logic."""
    player_id = str(interaction.user.id)
    stats = load_json(STATS_FILE).get(player_id, {})

    if terrain not in TERRAIN_TABLES:
        await interaction.response.send_message("❌ Invalid terrain selection!")
        return

    # ✅ Determine best stat for herbalism
    best_mod = max(stats.get("wisdom", 0), stats.get("intelligence", 0))

    # ✅ Apply proficiency and herbalism kit bonuses
    proficiency_bonus = stats.get("proficiency", 0) if stats.get("proficient", False) else 0
    kit_bonus = 2 if stats.get("herbalism_kit", False) else 0

    # ✅ Roll for gathering success
    roll = random.randint(1, 20) + best_mod + proficiency_bonus + kit_bonus

    ingredient_name = TERRAIN_TABLES[terrain].get(str(roll), "Nothing found")
    quantity = random.randint(1, 4)

    logger.info(f"User {interaction.user} rolled {roll} = {best_mod} (stat) + {proficiency_bonus} (prof) + {kit_bonus} (kit). Found: {ingredient_name}.")

    if ingredient_name != "Nothing found":
        ingredient_info = INGREDIENTS.get(ingredient_name, {})
        add_item(player_id, ingredient_name, quantity)  # ✅ Add to inventory
        logger.info(f"User {interaction.user} gathered {quantity}x {ingredient_name} in {terrain}.")
        await interaction.response.send_message(
            f"🌿 You gathered **{quantity}x {ingredient_name}** ({ingredient_info.get('rarity', 'Unknown')})."
        )
    else:
        logger.info(f"User {interaction.user} searched in {terrain} but found nothing.")
        await interaction.response.send_message("You searched but found nothing useful.")

async def setup(bot):
    cog = Herbalism(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")