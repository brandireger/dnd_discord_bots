import discord
from discord import app_commands
from discord.ext import commands
import random
import time
import os
import logging
from logging import getLogger
from data_manager import load_json, save_json, ensure_currency, get_response

# ✅ Configure logging
logger = getLogger(__name__)

class Economy(commands.Cog):
    """Handles player currency transactions."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your current gold balance.")
    async def balance(self, interaction: discord.Interaction):
        """Shows the user's current gold balance."""
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        shared_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared_inventories")
        gold_data = load_json("gold_data.json", folder=shared_dir)

        # Ensure user has a balance
        balance = ensure_currency(user_id)
        gp, sp, cp = balance["gp"], balance["sp"], balance["cp"]

        await interaction.followup.send(f"💰 Your balance: `{gp} gp, {sp} sp, {cp} cp`.")

    @app_commands.command(name="inventory", description="Check your inventory.")
    async def inventory(self, interaction: discord.Interaction):
        """Displays the player's current inventory."""
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        inventory_data = load_json(PLAYER_INVENTORY_FILE, {})

        # Check if player has any items
        if user_id not in inventory_data or not inventory_data[user_id]:
            await interaction.followup.send(f"🎒 {interaction.user.mention}, you own absolutely nothing. Not even a rusty dagger. How tragic.")
            return

        # Format inventory items
        inventory_list = [f"🔹 **{item.capitalize()}** (x{qty})" for item, qty in inventory_data[user_id].items()]
        
        # Pagination: Discord has a 2000-character message limit
        message_chunks = []
        chunk = ""
        for item in inventory_list:
            if len(chunk) + len(item) + 2 > 2000:  # +2 accounts for newline characters
                message_chunks.append(chunk)
                chunk = ""
            chunk += item + "\n"
        if chunk:
            message_chunks.append(chunk)

        # Send messages
        for idx, msg in enumerate(message_chunks):
            await interaction.followup.send(f"🎒 **{interaction.user.name}'s Inventory (Page {idx+1}/{len(message_chunks)})**\n{msg}")

    @app_commands.command(name="givegold", description="Give gold to another player.")
    async def givegold(self, interaction: discord.Interaction, member: discord.Member, gp: int = 0, sp: int = 0, cp: int = 0):
        """Allows players to give gold to each other."""
        await interaction.response.defer(thinking=True)

        giver_id = str(interaction.user.id)
        receiver_id = str(member.id)

        shared_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared_inventories")
        gold_data = load_json("gold_data.json", folder=shared_dir)

        # Ensure both players have an account
        ensure_currency(giver_id)
        ensure_currency(receiver_id)

        # Convert to total copper
        total_cp = (gp * 100) + (sp * 10) + cp
        giver_cp = (gold_data[giver_id]["gp"] * 100) + (gold_data[giver_id]["sp"] * 10) + gold_data[giver_id]["cp"]

        if giver_cp < total_cp:
            await interaction.followup.send("❌ You don't have enough gold!")
            return

        # Deduct from giver
        giver_cp -= total_cp
        gold_data[giver_id] = {"gp": giver_cp // 100, "sp": (giver_cp % 100) // 10, "cp": giver_cp % 10}

        # Add to receiver
        receiver_cp = (gold_data[receiver_id]["gp"] * 100) + (gold_data[receiver_id]["sp"] * 10) + gold_data[receiver_id]["cp"]
        receiver_cp += total_cp
        gold_data[receiver_id] = {"gp": receiver_cp // 100, "sp": (receiver_cp % 100) // 10, "cp": receiver_cp % 10}

        save_json("gold_data.json", gold_data, folder=shared_dir)
        await interaction.followup.send(get_response("givegold_success", user=interaction.user.name, receiver=receiver.display_name, amount=total_cp // 100))

    @app_commands.command(name="takegold", description="Remove gold from a player.")
    @commands.has_permissions(administrator=True)
    async def takegold(self, interaction: discord.Interaction, member: discord.Member, gp: int = 0, sp: int = 0, cp: int = 0):
        """Removes gold from a player."""
        await interaction.response.defer(thinking=True)

        user_id = str(member.id)
        shared_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared_inventories")
        gold_data = load_json("gold_data.json", folder=shared_dir)

        ensure_currency(user_id)

        # Convert to total copper
        total_cp = (gp * 100) + (sp * 10) + cp
        player_cp = (gold_data[user_id]["gp"] * 100) + (gold_data[user_id]["sp"] * 10) + gold_data[user_id]["cp"]

        if player_cp < total_cp:
            await interaction.followup.send("❌ Player does not have enough gold!")
            return

        # Deduct gold
        player_cp -= total_cp
        gold_data[user_id] = {"gp": player_cp // 100, "sp": (player_cp % 100) // 10, "cp": player_cp % 10}

        save_json("gold_data.json", gold_data, folder=shared_dir)
        await interaction.followup.send(get_response("takegold_success", user=interaction.user.name, target=member.display_name, amount=total_cp // 100))

    @app_commands.command(name="admin_givegold", description="Admin-only: Give gold to a player without deducting it.")
    @commands.has_permissions(administrator=True)
    async def admin_givegold(self, interaction: discord.Interaction, member: discord.Member, gp: int = 0, sp: int = 0, cp: int = 0):
        """Admins can reward gold to players (for quests, events, etc.) without taking it from themselves."""
        await interaction.response.defer(thinking=True)

        receiver_id = str(member.id)
        shared_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared_inventories")
        gold_data = load_json("gold_data.json", folder=shared_dir)

        print(f"🔍 Debug: {interaction.user.name} is giving (admin reward) {gp} gp, {sp} sp, {cp} cp to {member.name}.")

        ensure_currency(user_id)

        # Convert to total copper and add to the receiver
        total_cp = (gp * 100) + (sp * 10) + cp
        receiver_cp = (gold_data[receiver_id]["gp"] * 100) + (gold_data[receiver_id]["sp"] * 10) + gold_data[receiver_id]["cp"]
        receiver_cp += total_cp

        # Convert back to gp/sp/cp format
        gold_data[receiver_id] = {"gp": receiver_cp // 100, "sp": (receiver_cp % 100) // 10, "cp": receiver_cp % 10}

        # Save updated balance
        save_json("gold_data.json", gold_data, folder=shared_dir)
        await interaction.followup.send(f"✨ {interaction.user.mention} **rewarded** {member.mention} `{gp} gp, {sp} sp, {cp} cp`!")
    
    @app_commands.command(name="load_market", description="(Admin) Force-refresh the market.")
    @commands.has_permissions(administrator=True)
    async def load_market(self, interaction: discord.Interaction):
        """Forces a market refresh."""
        await interaction.response.defer(thinking=True)
        market = load_market()
        await interaction.followup.send("✅ **Market successfully loaded!**")

    @app_commands.command(name="refresh_market", description="(Admin) Manually regenerate the market.")
    @commands.has_permissions(administrator=True)
    async def refresh_market(self, interaction: discord.Interaction):
        """Regenerates the market, replacing old stock."""
        await interaction.response.defer(thinking=True)
        new_market = generate_market()
        save_market(new_market)
        await interaction.followup.send("🔄 **Market refreshed!** New items available.")

async def setup(bot):
    cog = Economy(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")