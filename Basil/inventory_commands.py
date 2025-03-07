import discord
from discord import app_commands
from discord.ext import commands
import os
from inventory_functions import add_item, remove_item, get_inventory
from bot_logging import logger

logger.info("✅ Inventory module initialized")

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="basil_inventory", description="View your inventory.")
    async def basil_inventory(self, interaction: discord.Interaction):
        """Displays the user's inventory."""
        player_id = str(interaction.user.id)
        inventory = get_inventory(player_id) or {}
        
        if not inventory:
            await interaction.response.send_message("Your inventory is empty.")
            return
        
        inventory_list = [f"🔹 **{item}**: `{qty}`" for item, qty in inventory.items()]
        chunks = [inventory_list[i: i + 10] for i in range(0, len(inventory_list), 10)]

        for idx, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"🎒 {interaction.user.name}'s Inventory (Page {idx+1}/{len(chunks)})",
                description="\n".join(chunk),
                color=discord.Color.green()
            )
            
            if idx == 0:
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.followup.send(embed=embed)

    @app_commands.command(name="add_item", description="(Admin) Adds an item to a player's inventory.")
    @commands.has_permissions(administrator=True)
    async def add_item_command(self, interaction: discord.Interaction, member: discord.Member, item: str, quantity: int):
        """Adds an item to a player's inventory (Admin only)."""
        if quantity <= 0:
            await interaction.response.send_message("❌ Quantity must be greater than **zero**.", ephemeral=True)
            return

        player_id = str(member.id)
        add_item(player_id, item, quantity)

        logger.info(f"Admin {interaction.user} added {quantity}x {item} to {member}.")
        await interaction.response.send_message(f"Added {quantity}x {item} to {member.mention}'s inventory.", ephemeral=True)

    @app_commands.command(name="remove_item", description="Removes an item from a player's inventory (Admin only).")
    @commands.has_permissions(administrator=True)
    async def remove_item_command(self, interaction: discord.Interaction, member: discord.Member, item: str, quantity: int):
        """Removes an item from a player's inventory (Admin only)."""
        if quantity <= 0:
            await interaction.response.send_message("❌ Quantity must be greater than **zero**.", ephemeral=True)
            return

        player_id = str(member.id)
        inventory = get_inventory(player_id) or {}

        # ✅ Check if the player actually has enough of the item
        if item not in inventory or inventory[item] < quantity:
            await interaction.response.send_message(f"❌ {member.mention} does not have `{quantity}x {item}` to remove.", ephemeral=True)
            return

        remove_item(player_id, item, quantity)
        logger.info(f"Admin {interaction.user} removed {quantity}x {item} from {member}.")
        await interaction.response.send_message(f"✅ **Removed** `{quantity}x {item}` from {member.mention}'s inventory.", ephemeral=True)

async def setup(bot):
    cog = Inventory(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")