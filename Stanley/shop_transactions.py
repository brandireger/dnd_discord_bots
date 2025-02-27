import discord
from discord import app_commands
from discord.ext import commands
import logging
import os
from data_manager import load_json, save_json, get_response

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.join(BASE_DIR, "..", "shared_inventories")

class ShopTransactions(commands.Cog):
    """Cog for handling purchases in Stanley's shop."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="buy", description="Purchase an item from Stanley's shop.")
    async def buy(self, interaction: discord.Interaction, item: str):
        """Allows players to buy an item if they have enough money and if it's in stock."""
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)

        shop_data = load_json("stanley_shop.json", folder=SHARED_DIR)
        gold_data = load_json("gold_data.json", folder=SHARED_DIR)
        inventory_data = load_json("player_inventories.json", folder=SHARED_DIR)

        item = item.lower().strip()
        logger.info(f"🔍 {interaction.user.name} is attempting to buy `{item}`.")

        # Search for item in all categories
        found_item = next(
            (data for category in shop_data.values() for name, data in category.items() if name.lower() == item),
            None
        )

        if not found_item:
            await interaction.followup.send(get_response("buy_not_available", item=item))
            return

        if found_item["stock"] <= 0:
            await interaction.followup.send(get_response("buy_no_stock", item=item))
            return

        player_cp = sum(
            gold_data.get(user_id, {}).get(k, 0) * v
            for k, v in {"gp": 100, "sp": 10, "cp": 1}.items()
        )

        if player_cp < found_item["price_cp"]:
            await interaction.followup.send(f"❌ You don't have enough gold to buy `{item}`.")
            return

        # Deduct price from player's gold
        player_cp -= found_item["price_cp"]
        gold_data[user_id] = {"gp": player_cp // 100, "sp": (player_cp % 100) // 10, "cp": player_cp % 10}
        save_json("gold_data.json", gold_data, folder=SHARED_DIR)

        # Deduct stock
        found_item["stock"] -= 1
        save_json("stanley_shop.json", shop_data, folder=SHARED_DIR)

        # Add item to player's inventory
        inventory_data.setdefault(user_id, {})
        inventory_data[user_id][item] = inventory_data[user_id].get(item, 0) + 1
        save_json("player_inventories.json", inventory_data, folder=shared_dir)

        logger.info(f"✅ {interaction.user.name} successfully bought `{item}`.")
        await interaction.followup.send(get_response("buy_success", user=interaction.user.name, item=item))

    @app_commands.command(name="sell", description="Sell an item back to Stanley for half its value.")
    async def sell(self, interaction: discord.Interaction, item: str):
        """Allows a player to sell an item for half its value."""
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        shop_data = load_json("stanley_shop.json", folder=SHARED_DIR)
        gold_data = load_json("gold_data.json", folder=SHARED_DIR)
        inventory_data = load_json("player_inventories.json", folder=SHARED_DIR)

        logger.info(f"🔍 {interaction.user.name} is attempting to sell `{item}`.")

        # Ensure inventory exists
        if user_id not in inventory_data or not inventory_data[user_id]:
            await interaction.followup.send(f"❌ {interaction.user.mention}, you don't have anything to sell!")
            return

        item = item.lower().strip()

        # Check if the player owns the item
        matched_item = next((name for name in inventory_data[user_id] if name.lower() == item), None)
        if not matched_item:
            await interaction.followup.send(get_response("sell_no_item", user=interaction.user.name, item=item))
            return

        # Find the item's price
        found_item = next(
            (data for category in shop_data.values() for name, data in category.items() if name.lower() == item),
            None
        )

        if not found_item:
            await interaction.followup.send(get_response("sell_not_shop_item", user=interaction.user.name, item=item))
            return

        sell_price_cp = found_item["price_cp"] // 2  # Selling is half price

        # Remove item from inventory
        inventory_data[user_id][item] -= 1
        if inventory_data[user_id][item] <= 0:
            del inventory_data[user_id][item]  # Remove if count reaches 0
        save_json("player_inventories.json", inventory_data, folder=SHARED_DIR)

        # Add stock back to the shop
        for category in shop_data.values():
            if matched_item in category:
                category[matched_item]["stock"] += 1
                save_json("stanley_shop.json", shop_data)
                break

        # Add gold to player
        player_cp = sum(
            gold_data.get(user_id, {}).get(k, 0) * v
            for k, v in {"gp": 100, "sp": 10, "cp": 1}.items()
        )

        player_cp += sell_price_cp
        gold_data[user_id] = {"gp": player_cp // 100, "sp": (player_cp % 100) // 10, "cp": player_cp % 10}
        save_json("gold_data.json", gold_data, folder=SHARED_DIR)

        logger.info(f"✅ {interaction.user.name} sold `{matched_item}` for `{sell_price_cp // 100} gp`.")
        await interaction.followup.send(get_response("sell_success", user=interaction.user.name, item=matched_item, price_gp=sell_price_cp // 100))

async def setup(bot):
    """Loads the ShopTransactions cog into the bot."""
    print("🔍 Debug: Loading ShopTransactions cog...")
    await bot.add_cog(ShopTransactions(bot))
    print("✅ ShopTransactions cog loaded!")