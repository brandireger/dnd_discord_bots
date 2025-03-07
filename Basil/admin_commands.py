import discord
from discord import app_commands
from discord.ext import commands
from data_manager import load_json, save_json, reset_data
from economy import save_market, generate_market
import os
from inventory_functions import remove_item, get_all_players
from bot_logging import logger

logger.info("✅ AdminCommands module initialized")

class AdminCommands(commands.Cog):
    """Admin-only commands for resetting game data."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="advance_time", description="(Admin) Advances in-game time by a set number of hours.")
    @app_commands.default_permissions(administrator=True)
    async def advance_time(self, interaction: discord.Interaction, hours: int):
        """Advances the in-game time and updates player cooldowns accordingly."""
        if hours <= 0:
            await interaction.response.send_message("❌ Hours must be a positive number.")
            return
        
        in_game_time = load_json("in_game_time.json")
        old_days = in_game_time["days"]

        # ✅ Update time
        in_game_time["hours"] += hours
        if in_game_time["hours"] >= 24:
            days_passed = in_game_time["hours"] // 24
            in_game_time["days"] += days_passed
            in_game_time["hours"] %= 24  

        save_json("in_game_time.json", in_game_time)

        # ✅ Reset gather attempts for all players when a new day starts
        if old_days != in_game_time["days"]:
            player_cooldowns = load_json("player_cooldowns.json")
            for player_id in player_cooldowns:
                player_cooldowns[player_id]["gather_attempts"] = 3  # ✅ Correctly reset all players
            save_json("player_cooldowns.json", player_cooldowns)

        # ✅ Process Basil's crafting
        basil_cog = self.bot.get_cog("BasilCrafting")
        
        if not basil_cog:
            logger.error("❌ Basil crafting command not found!")
            return [], []

        basil_crafting_cmd = self.bot.tree.get_command("basil_crafting")

        crafted_potions, failures = [], []
        for _ in range(hours):  # Basil attempts to craft once per in-game hour
            crafting_result = await basil_crafting_cmd._callback(basil_cog, interaction, hours)
            if crafting_result:
                crafted, failed = crafting_result
                crafted_potions.extend(crafted)
                failures.extend(failed)

        # ✅ Response message
        result_text = f"🕰️ **Time Advanced!**\n⏳ In-game time: `{in_game_time['hours']} hours, {in_game_time['days']} days`\n\n"
        if crafted_potions:
            result_text += "**🧪 Basil has crafted:**\n" + "\n".join([f"• **{item}** x{qty}" for item, qty in crafted_potions]) + "\n"
        if failures:
            result_text += "**⚠️ Basil had some critical failures:**\n" + "\n".join([f"• **{item}** (Toxic Failure!)" for item in failures]) + "\n"
        if not crafted_potions and not failures:
            result_text += "🔬 Basil worked hard but didn't successfully finish any potions this time."

        logger.info(f"Admin {interaction.user} advanced time by {hours} hours. New time: {in_game_time['hours']}h, {in_game_time['days']}d.")
        await interaction.response.send_message(result_text)
        
    async def process_basil_crafting(self, interaction, hours):
        """Processes Basil's crafting progress over the given hours."""
        basil_cog = self.bot.get_cog("BasilCrafting")  # ✅ Fetch the cog
        if not basil_cog:
            logger.error("❌ BasilCrafting cog not found! Ensure it's loaded.")
            return [], []

        basil_crafting_cmd = self.bot.get_command("basil_crafting")  # ✅ Get the command properly
        if not basil_crafting_cmd:
            logger.error("❌ Basil crafting command not found!")
            return [], []

        crafted_potions, failures = [], []
        for _ in range(hours):  # Basil attempts to craft once per in-game hour
            crafting_result = await basil_crafting_cmd.callback(basil_cog, interaction, hours)
            if crafting_result:
                crafted, failed = crafting_result
                crafted_potions.extend(crafted)
                failures.extend(failed)

        return crafted_potions, failures

    @app_commands.command(name="reset_market", description="(Admin) Reset and regenerate the market inventory.")
    @app_commands.default_permissions(administrator=True)
    async def reset_market(self, interaction: discord.Interaction):
        """Regenerates the market inventory."""
        self.bot.get_cog("Economy").market = generate_market()
        save_market(self.bot.get_cog("Economy").market) 
        logger.warning(f"Admin {interaction.user} reset the market.")
        await interaction.response.send_message("✅ The market has been **refreshed** with new items!")

    @app_commands.command(name="reset_inventory", description="(Admin) Reset a player's inventory.")
    @app_commands.default_permissions(administrator=True)
    async def reset_inventory(self, interaction: discord.Interaction, member: discord.Member = None):
        """Clears a player's inventory or resets all inventories if no player is specified."""
        if member:
            remove_item(str(member.id), item=None, clear_all=True)
            logger.info(f"Admin {interaction.user} reset {member.name}'s inventory.")
            await interaction.response.send_message(f"✅ {member.mention}'s inventory has been reset!")
        else:
            # Reset all players
            for player in get_all_players():
                remove_item(player, item=None, clear_all=True)
            logger.info(f"Admin {interaction.user} reset ALL player inventories.")
            await interaction.response.send_message("✅ **All** player inventories have been reset!")
                   
    @app_commands.command(name="open_shop", description="(Admin) Resets and prepares Basil's shop.")
    @app_commands.default_permissions(administrator=True)
    async def open_shop(self, interaction: discord.Interaction):
        """Admin command that resets the shop inventory and ensures it is properly prepared."""
        await interaction.response.defer(thinking=True)

        # ✅ Reset Recipes & Ingredients
        result = reset_data("all")
    
        # ✅ Refresh the Market with New Items
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.market = generate_market()
            save_market(economy_cog.market)

        # ✅ Ensure Basil's Shop Inventory Exists
        shop_inventory = load_json("market.json") or {}
        crafted_items = load_json("crafted_items.json") or {}

        # ✅ Combine Market Items & Crafted Items into Basil's Shop
        shop_inventory.update(economy_cog.market)  # Add Market Items
        shop_inventory.update(crafted_items)  # Add Crafted Items

        # ✅ Save the Shop Inventory
        save_json("market.json", shop_inventory)

        logger.info(f"Admin {interaction.user} reset Basil's shop inventory.")
        await interaction.followup.send(f"{result}\n✅ **Basil's shop has been fully reset and stocked with new items!**") 

async def setup(bot):
    cog = AdminCommands(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")