import discord
from discord import app_commands
from discord.ext import commands
import random
import time
import os
from data_manager import load_json, save_json 
from inventory_functions import add_item, remove_item, get_inventory
from bot_logging import logger

logger.info("✅ Economy module initialized")

# ✅ File paths
MARKET_FILE = "market.json"
GOLD_FILE = "gold_data.json"
STATS_FILE = "player_stats.json"

INGREDIENTS = load_json("ingredients.json") or {}

def generate_market():
    """Generates a fresh market with randomized base prices that last for one week."""
    market = {}
    for ingredient, data in INGREDIENTS.items():
        rarity = data.get("rarity", "Common")
        price_ranges = {"Common": (5, 15), "Uncommon": (15, 30), "Rare": (30, 50), "Very Rare": (50, 100)}
        base_price = random.randint(*price_ranges.get(rarity, (5, 15)))  # ✅ Base price independent of player stats

        market[ingredient] = {
            "base_price": base_price,  # ✅ Fixed market price for the week
            "stock": random.randint(1, 5)
        }

    market["last_update"] = time.time()  # ✅ Track last update
    save_market(market)
    return market

def load_market():
    """Loads the market, regenerating it if a week has passed."""
    market = load_json(MARKET_FILE) or {}

    # ✅ Refresh if it's been more than 7 days
    if time.time() - market.get("last_update", 0) > 7 * 24 * 60 * 60:
        logger.info("🔄 Market prices refreshed after one week!")
        return generate_market()
    
    return market

def save_market(market_data):
    """Saves the current market state to file."""
    save_json(MARKET_FILE, market_data)
    logger.info("✅ Market state saved.")

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.market = load_market() or generate_market()

    @app_commands.command(name="market", description="View available ingredients for purchase.")
    async def market(self, interaction: discord.Interaction):
        """Displays the current market inventory."""
        if not self.market:
            await interaction.response.send_message("🛒 The market is empty. Check back later!")
            return

        market_items = "\n".join([
            f"**{item}** (Stock: {self.market[item]['stock'] if self.market[item]['stock'] > 0 else '❌ Out of Stock'})"
            f" - {INGREDIENTS.get(item, {}).get('rarity', 'Common')} - `{self.market[item]['base_price']} gp`"
            for item in self.market if item != "last_update"
        ])
        
        embed = discord.Embed(title="🛒 Market Inventory", description=market_items, color=discord.Color.blue())
        logger.info(f"User {interaction.user} viewed the market inventory.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="quote", description="Get the current price for selling an ingredient.")
    async def quote(self, interaction: discord.Interaction, ingredient: str):
        """Provides a quote for the selling price of an ingredient, based on player stats."""
        ingredient = ingredient.capitalize()
        user_id = str(interaction.user.id)
        stats = load_json(STATS_FILE).get(user_id, {})

        # ✅ Base player stats
        cha_mod = stats.get("charisma", 0)
        persuasion_bonus = 2 if stats.get("proficient_persuasion", False) else 0

        base_price = self.market.get(ingredient, {}).get("base_price", INGREDIENTS.get(ingredient, {}).get("base_price", 15))

        final_price = max(1, base_price + cha_mod + persuasion_bonus)  # ✅ Ensures non-negative price

        await interaction.response.send_message(f"💰 Current selling price for **{ingredient}**: `{final_price} gp`.")
        
    @app_commands.command(name="buy", description="Purchase an ingredient from the market.")
    async def buy(self, interaction: discord.Interaction, ingredient: str):
        """Allows players to buy ingredients from the market."""
        ingredient = ingredient.capitalize()
        user_id = str(interaction.user.id)
        gold_data = load_json(GOLD_FILE) or {}

        # ✅ Ensure player gold entry exists
        gold_data.setdefault(user_id, {"gp": 0, "sp": 0, "cp": 0})

        # ✅ Check if the item is in the market
        if ingredient not in self.market or self.market[ingredient]["stock"] <= 0:
            await interaction.response.send_message("❌ That item is not currently for sale.")
            return

        price = self.market[ingredient]["base_price"]

        if gold_data[user_id]["gp"] < price:
            await interaction.response.send_message("❌ You don't have enough gold!")
            return

        # ✅ Deduct gold and update inventory
        gold_data[user_id]["gp"] -= price
        save_json(GOLD_FILE, gold_data, folder=SHARED_FOLDER)
        add_item(user_id, ingredient, 1)

        # ✅ Reduce stock in market
        self.market[ingredient]["stock"] -= 1
        save_market(self.market)

        logger.info(f"User {interaction.user} purchased {ingredient} for {price} gp.")
        await interaction.response.send_message(f"✅ You purchased **{ingredient}** for `{price} gp`!")

    @app_commands.command(name="sell", description="Sell an ingredient.")
    async def sell(self, interaction: discord.Interaction, ingredient: str):
        """Allows players to sell ingredients to the market."""
        ingredient = ingredient.capitalize()
        user_id = str(interaction.user.id)
        gold_data = load_json(GOLD_FILE) or {}
        stats = load_json(STATS_FILE).get(user_id, {})

        # ✅ Check if the player owns the item
        player_inventory = get_inventory(user_id)
        if ingredient not in player_inventory or player_inventory[ingredient] <= 0:
            logger.warning(f"User {interaction.user} tried to sell {ingredient} but has none.")
            await interaction.response.send_message(f"❌ You don't have any **{ingredient}** to sell.")
            return

        # ✅ Get base market price
        self.market.setdefault(ingredient, {"base_price": INGREDIENTS.get(ingredient, {}).get("base_price", 10), "stock": 0})

        base_price = self.market[ingredient]["base_price"]

        # ✅ Apply Charisma & Persuasion bonuses dynamically
        cha_mod = stats.get("charisma", 0)
        persuasion_bonus = 2 if stats.get("proficient_persuasion", False) else 0
        final_price = max(1, base_price + cha_mod + persuasion_bonus)  # ✅ Ensures non-negative price

        # ✅ Remove item & add gold
        remove_item(user_id, ingredient, 1)
        gold_data[user_id]["gp"] += final_price
        save_json(GOLD_FILE, gold_data, folder=SHARED_FOLDER)

        # ✅ Add item to market
        self.market[ingredient]["stock"] += 1
        save_market(self.market)

        logger.info(f"User {interaction.user} (ID: {user_id}) sold {ingredient} for {final_price} gp.")
        await interaction.response.send_message(f"💰 You sold **{ingredient}** for `{final_price} gp`.")

async def setup(bot):
    cog = Economy(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")