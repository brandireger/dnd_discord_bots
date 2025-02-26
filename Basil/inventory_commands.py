import discord
from discord import app_commands
from discord.ext import commands
import logging
from logging import getLogger
from logging.handlers import RotatingFileHandler
import sys
import os
from inventory_functions import add_item, remove_item, get_inventory

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

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="inventory", description="View your inventory.")
    async def inventory(self, interaction: discord.Interaction):
        """Displays the user's inventory."""
        player_id = str(interaction.user.id)
        inventory = get_inventory(player_id) or {}
        
        if not inventory:
            await interaction.response.send_message("Your inventory is empty.")
            return
        
        inventory_list = "\n".join([f"**{item}**: {qty}" for item, qty in inventory.items()])
        embed = discord.Embed(
            title=f"{interaction.user.name}'s Inventory",
            description=inventory_list,
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="add_item", description="(Admin) Adds an item to a player's inventory.")
    @commands.has_permissions(administrator=True)
    async def add_item_command(self, interaction: discord.Interaction, member: discord.Member, item: str, quantity: int):
        """Adds an item to a player's inventory (Admin only)."""
        if quantity <= 0:
            await interaction.response.send_message("❌ Quantity must be greater than **zero**.")
            return

        player_id = str(member.id)
        add_item(player_id, item, quantity)
        logger.info(f"Admin {interaction.user} added {quantity}x {item} to {member}.")
        await interaction.response.send_message(f"Added {quantity}x {item} to {member.mention}'s inventory.")

    @app_commands.command(name="remove_item", description="Removes an item from a player's inventory (Admin only).")
    @commands.has_permissions(administrator=True)
    async def remove_item_command(self, interaction: discord.Interaction, member: discord.Member, item: str, quantity: int):
        """Removes an item from a player's inventory (Admin only)."""
        if quantity <= 0:
            await interaction.response.send_message("❌ Quantity must be greater than **zero**.")
            return

        player_id = str(member.id)
        inventory = get_inventory(player_id) or {}

        # ✅ Check if the player actually has enough of the item
        if item not in inventory or inventory[item] < quantity:
            await interaction.response.send_message(f"❌ {member.mention} does not have `{quantity}x {item}` to remove.")
            return

        remove_item(player_id, item, quantity)
        logger.info(f"Admin {interaction.user} removed {quantity}x {item} from {member}.")
        await interaction.response.send_message(f"✅ **Removed** `{quantity}x {item}` from {member.mention}'s inventory.")

async def setup(bot):
    cog = Inventory(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")