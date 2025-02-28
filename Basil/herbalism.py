import discord
from discord import ui, app_commands
from discord.ext import commands
import random
import os
from data_manager import load_json, save_json
from inventory_functions import add_item, remove_item
from bot_logging import logger

logger.info("✅ Herbalism module initialized")

class TerrainSelect(ui.Select):
    """Dropdown menu for selecting a terrain type."""
    def __init__(self, interaction):
        terrain_tables = load_json("terrain_tables.json")

        options = [
            discord.SelectOption(label=terrain, value=terrain)
            for terrain in terrain_tables.keys()
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
        player_cooldowns = load_json("player_cooldowns.json")
        in_game_time = load_json("in_game_time.json")
        terrain_tables = load_json("terrain_tables.json")

        # ✅ Ensure player cooldown data exists
        player_cooldowns.setdefault(player_id, {"gather_attempts": 0, "last_gather_hour": -999})

        # ✅ Ensure in-game time is tracked
        if "hours" not in in_game_time:
            in_game_time["hours"], in_game_time["days"] = 0, 0
            save_json("in_game_time.json", in_game_time)

        # ✅ Check if player has remaining gather attempts
        if player_cooldowns[player_id]["gather_attempts"] <= 0:
            await interaction.response.send_message("❌ You have no gathering attempts left. Wait for more in-game time to pass.")
            return

        if not terrain_tables:
            await interaction.response.send_message("❌ No terrain data found. Admin should update `terrain_tables.json`.")
            return

        # ✅ Deduct one attempt
        player_cooldowns[player_id]["gather_attempts"] -= 1
        save_json("player_cooldowns.json", player_cooldowns)
        
        await interaction.response.send_message(
            "🌍 **Select a terrain to gather herbs from:**",
            view=TerrainView(interaction),
            ephemeral=True
        )

    @app_commands.command(name="identify", description="Identify an unknown herb with an Herbalism check.")
    async def identify(self, interaction: discord.Interaction, ingredient: str):
        """Allows players to identify herbs using their stats."""
        player_id = str(interaction.user.id)
        stats = load_json("player_stats.json").get(player_id, {})
        ingredients = load_json("ingredients.json")
        player_cooldowns = load_json("player_cooldowns.json")
        in_game_time = load_json("in_game_time.json")

        ingredient = ingredient.lower().strip()

        # ✅ Normalize common ingredient names
        if "common ingredient" in ingredient:
            possible_common_ingredients = ["Wild Sageroot", "Mandrake Root", "Bloodgrass", "Milkweed Seeds"]
            identified_ingredient = random.choice(possible_common_ingredients)  # Pick one at random
            ingredient_to_remove = "Common Ingredient"  # Correct name in inventory
        else:
            identified_ingredient = next((key for key in ingredients.keys() if key.lower() == ingredient), None)
            ingredient_to_remove = identified_ingredient

        if not identified_ingredient:
            logger.warning(f"User {interaction.user} tried to identify an unknown ingredient: {ingredient}")
            await interaction.response.send_message("❌ That ingredient does not exist in my records.")
            return

        ingredient_data = ingredients.get(identified_ingredient)
        if not ingredient_data:
            logger.error(f"⚠️ {identified_ingredient} exists in name matching but is missing from INGREDIENTS data!")
            await interaction.response.send_message("❌ I can't seem to find details on this ingredient. Check your spelling!")
            return

        last_identify_day = player_cooldowns.get(player_id, {}).get(f"identify_{ingredient}_day", -999)
        if in_game_time["days"] - last_identify_day < 1:
            await interaction.response.send_message(f"❌ You have already attempted to identify **{ingredient}** today. Try again tomorrow.")
            return

        # ✅ Determine best stat (Wisdom OR Intelligence)
        best_mod = max(stats.get("wisdom", 0), stats.get("intelligence", 0))
        proficiency_bonus = stats.get("proficiency", 0) if stats.get("proficient", False) else 0
        kit_bonus = 2 if stats.get("herbalism_kit", False) else 0
        dc = 10 + ingredient_data.get("DC", 0)
        roll = random.randint(1, 20) + best_mod + proficiency_bonus + kit_bonus

        logger.info(f"User {interaction.user} rolled {roll} vs DC {dc} to identify {identified_ingredient}.")

        if roll >= dc:
            # ✅ Success: Update inventory
            logger.info(f"User {interaction.user} successfully identified {identified_ingredient}.")
            remove_item(player_id, ingredient_to_remove, 1)  # Remove the unidentified version
            add_item(player_id, identified_ingredient, 1)  # Add identified herb
            player_cooldowns.setdefault(player_id, {})[f"identify_{ingredient}_day"] = in_game_time["days"]
            save_json("player_cooldowns.json", player_cooldowns)

            await interaction.response.send_message(f"✅ Success! You identify **{identified_ingredient}**: {ingredients[identified_ingredient]['effect']}")
        else:
            # ❌ Failure
            logger.info(f"User {interaction.user} failed to identify {ingredient}.")
            player_cooldowns.setdefault(player_id, {})[f"identify_{ingredient}_day"] = in_game_time["days"]
            save_json("player_cooldowns.json", player_cooldowns)
            await interaction.response.send_message("❌ You failed to identify the herb. Try again later!")
            
async def gather_execute(interaction: discord.Interaction, terrain: str):
    """Handles the actual herb gathering logic."""
    player_id = str(interaction.user.id)
    stats = load_json("player_stats.json").get(player_id, {})
    terrain_tables = load_json("terrain_tables.json")

    # Validate terrain exists in our tables.
    if terrain not in terrain_tables:
        await interaction.response.send_message("❌ Invalid terrain selection!")
        return

    # Calculate the herbalism roll.
    best_mod = max(stats.get("wisdom", 0), stats.get("intelligence", 0))
    proficiency_bonus = stats.get("proficiency", 0) if stats.get("proficient", False) else 0
    kit_bonus = 2 if stats.get("herbalism_kit", False) else 0
    roll_value = random.randint(1, 20) + best_mod + proficiency_bonus + kit_bonus

    # Look up the terrain data.
    terrain_data = terrain_tables[terrain]
    # Convert keys to integers (assuming keys are stored as strings of numbers).
    valid_keys = [int(k) for k in terrain_data.keys() if int(k) <= roll_value]

    if valid_keys:
        best_match = max(valid_keys)
        # Use the string version of the key for lookup.
        ingredient_name = terrain_data.get(str(best_match), "Nothing found")
    else:
        ingredient_name = "Nothing found"

    quantity = random.randint(1, 4)

    logger.info(f"User {interaction.user} rolled {roll_value} = {best_mod} (stat) + {proficiency_bonus} (prof) + {kit_bonus} (kit). Found: {ingredient_name}.")

    if ingredient_name != "Nothing found":
        # Retrieve ingredient info (e.g. rarity) from the ingredients file.
        ingredient_info = load_json("ingredients.json").get(ingredient_name, {})
        rarity = ingredient_info.get("rarity", "Unknown")
        add_item(player_id, ingredient_name, quantity)  # Add the gathered items to the player's inventory.
        logger.info(f"User {interaction.user} gathered {quantity}x {ingredient_name} in {terrain}.")
        await interaction.response.send_message(
            f"🌿 You gathered **{quantity}x {ingredient_name}** ({rarity})."
        )
    else:
        logger.info(f"User {interaction.user} searched in {terrain} but found nothing.")
        await interaction.response.send_message("You searched but found nothing useful.")

async def setup(bot):
    cog = Herbalism(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")