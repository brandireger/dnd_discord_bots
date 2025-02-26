import discord
from discord import app_commands
from discord.ext import commands
import json
import logging
from logging import getLogger
from logging.handlers import RotatingFileHandler
from data_manager import load_json, save_json
from economy import save_market, generate_market
import os
import sys
from inventory_functions import remove_item, get_all_players

# Configure logging
logger = getLogger(__name__)

# ✅ Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get Basil's main directory
BASE_FOLDER = os.path.join(BASE_DIR, "inventory")
DEFAULTS_FOLDER = os.path.join(BASE_DIR, "default_game_files")
SHARED_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "..", "shared_inventories"))

# ✅ Load Data from JSON (Centralized Handling)
INGREDIENTS = load_json("ingredients.json", folder=BASE_FOLDER) or {}
RECIPES = load_json("recipes.json", folder=BASE_FOLDER) or {}
IN_GAME_TIME = load_json("in_game_time.json", folder=BASE_FOLDER) or {}
PLAYER_COOLDOWNS = load_json("player_cooldowns.json", folder=BASE_FOLDER) or {}

class AdminCommands(commands.Cog):
    """Admin-only commands for resetting game data."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="advance_time", description="(Admin) Advances in-game time by a set number of hours.")
    @commands.has_permissions(administrator=True)
    async def advance_time(self, interaction: discord.Interaction, hours: int):
        """Advances the in-game time and updates player cooldowns accordingly."""
        if hours <= 0:
            await interaction.response.send_message("❌ Hours must be a positive number.")
            return
        
        old_hours = IN_GAME_TIME["hours"]
        old_days = IN_GAME_TIME["days"]

        # ✅ Update in-game time
        IN_GAME_TIME["hours"] += hours
        if IN_GAME_TIME["hours"] >= 24:
            days_passed = IN_GAME_TIME["hours"] // 24
            IN_GAME_TIME["days"] += days_passed
            IN_GAME_TIME["hours"] %= 24  # Reset hour count within the day

        print(f"Saving IN_GAME_TIME to: {os.path.join(BASE_FOLDER, 'in_game_time.json')}")
        print(f"IN_GAME_TIME Data: {IN_GAME_TIME}")  # Ensure it's a dictionary
        print(f"BASE_FOLDER Type: {type(BASE_FOLDER)}")  # Ensure it's a string
        save_json("in_game_time.json", IN_GAME_TIME, folder=BASE_FOLDER)

        # ✅ Update player gather attempts
        for player_id in get_all_players():
            PLAYER_COOLDOWNS.setdefault(player_id, {"gather_attempts": 0})
            PLAYER_COOLDOWNS[player_id]["gather_attempts"] += hours  # ✅ 1 attempt per hour

            # ✅ Reset daily identify cooldowns if a new day starts
            if old_days != IN_GAME_TIME["days"]:
                PLAYER_COOLDOWNS[player_id] = {
                    key: value for key, value in PLAYER_COOLDOWNS[player_id].items() if not key.startswith("identify_")
                }

        save_json("player_cooldowns.json", PLAYER_COOLDOWNS, folder=BASE_FOLDER)

        # ✅ Process Basil's Crafting
        crafted_potions, failures = await self.process_basil_crafting(hours)

        # ✅ Response message
        result_text = f"🕰️ **Time Advanced!**\n⏳ In-game time: `{IN_GAME_TIME['hours']} hours, {IN_GAME_TIME['days']} days`\n\n"
        
        if crafted_potions:
            result_text += "**🧪 Basil has crafted:**\n" + "\n".join(
                [f"• **{item}** x{qty}" for item, qty in crafted_potions]) + "\n"
        
        if failures:
            result_text += "**⚠️ Basil had some critical failures:**\n" + "\n".join(
                [f"• **{item}** (Toxic Failure!)" for item in failures]) + "\n"

        if not crafted_potions and not failures:
            result_text += "🔬 Basil worked hard but didn't successfully finish any potions this time."

        logger.info(f"Admin {interaction.user} advanced in-game time by {hours} hours. New time: {IN_GAME_TIME['hours']}h, {IN_GAME_TIME['days']}d.")
        await interaction.response.send_message(result_text)

    async def _reset_data_logic(self, target: str):
        """Handles resetting recipes, ingredients, or both."""
        if target.lower() not in ["recipes", "ingredients", "all"]:
            return "❌ Invalid option. Choose from: recipes, ingredients, or all."

        if target.lower() in ["recipes", "all"]:
            save_json("recipes.json", load_json("recipes.json", folder=DEFAULTS_FOLDER))
            logger.info("Recipes reset to default.")

        if target.lower() in ["ingredients", "all"]:
            save_json("ingredients.json", load_json("ingredients.json", folder=DEFAULTS_FOLDER))
            logger.info("Ingredients reset to default.")

        return f"✅ **{target.capitalize()} reset successfully!**"

    async def process_basil_crafting(self, hours):
        """Processes Basil's crafting progress over the given hours."""
        basil_cog = self.bot.get_cog("BasilCrafting")  # ✅ Fetch the cog
        if not basil_cog:
            logger.error("❌ BasilCrafting cog not found! Ensure it's loaded.")
            return [], []

        crafted_potions, failures = [], []
        for _ in range(hours):  # Basil attempts to craft once per in-game hour
            crafting_result = await self.basil_crafting(interaction, 1)
            if crafting_result:  
                crafted, failed = crafting_result
                crafted_potions.extend(crafted)
                failures.extend(failed)

        return crafted_potions, failures

    @app_commands.command(name="reset_market", description="(Admin) Reset and regenerate the market inventory.")
    @commands.has_permissions(administrator=True)
    async def reset_market(self, interaction: discord.Interaction):
        """Regenerates the market inventory."""
        if not INGREDIENTS:
            await interaction.response.send_message("❌ No ingredients found. The market cannot be refreshed.")
            return
        
        # ✅ Regenerate market using centralized function
        self.bot.get_cog("Economy").market = generate_market()
        save_market(self.bot.get_cog("Economy").market)  # ✅ Save market after reset
        logger.warning(f"Admin {interaction.user} reset the market.")
        await interaction.response.send_message("✅ The market has been **refreshed** with new items!")

    @app_commands.command(name="reset_inventory", description="(Admin) Reset a player's inventory.")
    @commands.has_permissions(administrator=True)
    async def reset_inventory(self, interaction: discord.Interaction, member: discord.Member = None):
        """Clears a player's inventory or resets all inventories if no player is specified."""
        if member:
            player_id = str(member.id)
            remove_item(player_id, item=None, clear_all=True)
            logger.info(f"Admin {interaction.user} reset {member.name}'s inventory.")
            await interaction.response.send_message(f"✅ {member.mention}'s inventory has been reset!")
        else:
            # Reset all players
            for player in get_all_players():
                remove_item(player, item=None, clear_all=True)
            logger.info(f"Admin {interaction.user} reset ALL player inventories.")
            await interaction.response.send_message("✅ **All** player inventories have been reset!")
            
    @app_commands.command(name="reset_data", description="(Admin) Reset recipes, ingredients, or both.")
    @commands.has_permissions(administrator=True)
    async def reset_data(self, interaction: discord.Interaction, target: str):
        """Resets recipes.json, ingredients.json, or both."""
        reset_message = await self._reset_data_logic(target)
        await interaction.response.send_message(reset_message)
        
    @app_commands.command(name="reset_all", description="(Admin) Fully reset inventories, market, and game data.")
    @commands.has_permissions(administrator=True)
    async def reset_all(self, interaction: discord.Interaction):
        """Fully resets all data: market, inventories, recipes, ingredients, and Basil's crafting stock."""
        self.bot.get_cog("Economy").market = generate_market()
        save_market(self.bot.get_cog("Economy").market)
        await self.reset_inventory(interaction)

        # Reset Basil's stock & crafted items
        save_json("basil_inventory.json", {})
        save_json("crafted_items.json", {})

        # Reset recipes & ingredients
        await self.reset_data(interaction, "all")
        # ✅ Reset in-game time
        save_json("in_game_time.json", {"days": 0, "hours": 0})

        logger.info(f"Admin {interaction.user} performed a **FULL RESET** of all game data.")
        await interaction.response.send_message("⚠️ **Full reset complete!** All data has been reset.")
        
    @app_commands.command(name="open_shop", description="(Admin) Resets and prepares Basil's shop.")
    @commands.has_permissions(administrator=True)
    async def open_shop(self, interaction: discord.Interaction):
        """Admin command that resets the shop to its default state."""
        await interaction.response.defer(thinking=True)  # Prevents timeout issues
        reset_message = await self._reset_data_logic("all")
        
        # ✅ Refresh the market using central function
        self.bot.get_cog("Economy").market = generate_market()
        save_market(self.bot.get_cog("Economy").market)

        logger.warning(f"Admin {interaction.user} reset the shop.")
        await interaction.followup.send(f"✅ **Basil's shop has been fully reset!**\n- {reset_message}\n- Market refreshed")

async def setup(bot):
    cog = AdminCommands(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")