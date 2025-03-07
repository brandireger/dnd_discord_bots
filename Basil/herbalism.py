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
    def __init__(self, interaction, roll):
        terrain_tables = load_json("terrain_tables.json")

        options = [
            discord.SelectOption(label=terrain, value=terrain)
            for terrain in terrain_tables.keys()
        ]

        super().__init__(placeholder="Choose a terrain to gather herbs...", min_values=1, max_values=1, options=options)
        self.interaction = interaction
        self.roll = roll

    async def callback(self, interaction: discord.Interaction):
        """Handles the selection of a terrain type."""
        self.view.stop()  # ✅ Disables the dropdown after the first selection

        selected_terrain = self.values[0]
        await gather_execute(interaction, selected_terrain, self.roll)

class TerrainView(ui.View):
    """View that contains the terrain selection dropdown."""
    def __init__(self, interaction: discord.Interaction, roll: int):
        super().__init__()
        self.interaction = interaction  # ✅ Store interaction
        self.add_item(TerrainSelect(interaction, roll))  # ✅ Pass interaction to TerrainSelect

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.interaction.user

class Herbalism(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gather", description="Gather herbs based on terrain type.")
    async def gather(self, interaction: discord.Interaction, roll: int = None):
        """Asks the player to select a terrain type using a dropdown menu."""
        roll = roll or random.randint(1, 20)

        if roll < 1 or roll > 20:
            await interaction.response.send_message("❌ Invalid roll! Please provide a d20 roll between 1 and 20.")
            return

        player_id = str(interaction.user.id)
        player_cooldowns = load_json("player_cooldowns.json")
        in_game_time = load_json("in_game_time.json")
        terrain_tables = load_json("terrain_tables.json")
        MAX_GATHER_ATTEMPTS = 3

        # ✅ Ensure player cooldown data exists
        player_cooldowns.setdefault(player_id, {"gather_attempts": 3, "last_gather_hour": -999})

        # ✅ Ensure in-game time is tracked
        if "hours" not in in_game_time:
            in_game_time["hours"], in_game_time["days"] = 0, 0
            save_json("in_game_time.json", in_game_time)

        if in_game_time["hours"] >= 24:
            in_game_time["days"] += in_game_time["hours"] // 24  # ✅ Correctly increment days
            in_game_time["hours"] %= 24  # ✅ Carry over remaining hours

            for player in player_cooldowns:
                player_cooldowns[player]["gather_attempts"] = 3  # ✅ Reset for all players

            save_json("player_cooldowns.json", player_cooldowns)
            save_json("in_game_time.json", in_game_time)

        # ✅ Check if gather attempts should reset before limiting it
        if player_cooldowns[player_id]["gather_attempts"] > MAX_GATHER_ATTEMPTS:
            player_cooldowns[player_id]["gather_attempts"] = MAX_GATHER_ATTEMPTS
            save_json("player_cooldowns.json", player_cooldowns)

        # ✅ Prevent gathering if attempts are 0
        if player_cooldowns[player_id]["gather_attempts"] <= 0:
            await interaction.response.send_message("❌ You've gathered enough for now. Try again after a long rest.")
            return

        if not terrain_tables:
            await interaction.response.send_message("❌ No terrain data found. Admin should update `terrain_tables.json`.")
            return

        # ✅ Deduct one attempt
        player_cooldowns[player_id]["gather_attempts"] -= 1
        save_json("player_cooldowns.json", player_cooldowns)
        
        await interaction.response.send_message(
            "🌍 **Select a terrain to gather herbs from:**",
            view=TerrainView(interaction, roll),
            ephemeral=True
        )

    @app_commands.command(name="identify", description="Identify an unknown herb with an Herbalism check.")
    async def identify(self, interaction: discord.Interaction, ingredient: str, roll: int = None):
        """Allows players to identify herbs using their stats."""
        roll = roll or random.randint(1, 20)

        if roll < 1 or roll > 20:
            await interaction.response.send_message("❌ Invalid roll! Please provide a d20 roll between 1 and 20.")
            return
    
        player_id = str(interaction.user.id)
        stats = load_json("player_stats.json").get(player_id, {})
        ingredients = load_json("ingredients.json")
        player_cooldowns = load_json("player_cooldowns.json")
        in_game_time = load_json("in_game_time.json")

        ingredient = ingredient.lower().strip().replace(" ", "_")

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
        total_roll = roll + best_mod + proficiency_bonus + kit_bonus

        logger.info(f"User {interaction.user} rolled {total_roll} vs DC {dc} to identify {identified_ingredient}.")

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
            
async def gather_execute(interaction: discord.Interaction, terrain: str, roll_value: int = None):
    """Handles the actual herb gathering logic."""
    player_id = str(interaction.user.id)
    stats = load_json("player_stats.json").get(player_id, {})
    terrain_tables = load_json("terrain_tables.json")

    roll_value = roll_value or random.randint(1,20)

    if roll_value < 1 or roll_value > 20:
            await interaction.response.send_message("❌ Invalid roll! Please provide a d20 roll between 1 and 20.")
            return

    # Validate terrain exists in our tables.
    if terrain not in terrain_tables:
        await interaction.response.send_message("❌ Invalid terrain selection!")
        return

    # Calculate the herbalism roll.  # Pass the player's roll instead of rolling randomly
    best_mod = max(stats.get("wisdom", 0), stats.get("intelligence", 0))
    proficiency_bonus = stats.get("proficiency", 0) if stats.get("proficient", False) else 0
    kit_bonus = 2 if stats.get("herbalism_kit", False) else 0
    total_roll = roll_value + best_mod + proficiency_bonus + kit_bonus

    # Look up the terrain data.
    terrain_data = terrain_tables[terrain]
    # Convert keys to integers (assuming keys are stored as strings of numbers).
    valid_keys = [int(k) for k in terrain_data.keys() if int(k) <= total_roll]

    ingredient_name = terrain_data.get(str(max(valid_keys))) if valid_keys else "Nothing found"
    quantity = random.randint(1, 4)

    logger.info(f"User {interaction.user} rolled {total_roll} = {best_mod} (stat) + {proficiency_bonus} (prof) + {kit_bonus} (kit). Found: {ingredient_name}.")

    if ingredient_name == "Nothing found":
        await interaction.response.send_message("❌ The area seems barren. You found nothing.")
        return
    
    # ✅ Add the found ingredient
    ingredient_info = load_json("ingredients.json").get(ingredient_name, {})
    rarity = ingredient_info.get("rarity", "Unknown")
    add_item(player_id, ingredient_name, quantity)
    logger.info(f"User {interaction.user} gathered {quantity}x {ingredient_name} in {terrain}.")

    await interaction.response.send_message(
        f"🌿 You gathered **{quantity}x {ingredient_name}** ({rarity}).", ephemeral=True
    )

async def setup(bot):
    cog = Herbalism(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")