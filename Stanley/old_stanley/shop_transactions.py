import discord
from discord.ext import commands
from data_manager import  (
    gold_data, PLAYER_INVENTORIES, save_json, config,
    SHOP_CATEGORIES, load_shop_items, load_json, GOLD_FILE,  # ✅ Fixed missing comma
    SHOP_FILE, PLAYER_INVENTORY_FILE, get_response, log_transaction
)

class ShopTransactions(commands.Cog):
    """Cog for Stanley's shop system."""

    def __init__(self, bot):
        self.bot = bot

    def get_economy_cog(self):
        """Retrieve the Economy cog to access shared functions."""
        return self.bot.get_cog("Economy")

    def convert_currency(self, user_id, total_cp):
        """Handles conversion for copper, silver, and gold when making purchases."""
        economy = self.get_economy_cog()  # ✅ Fetch Economy cog dynamically
        if not economy:
            print("❌ Error: Economy cog not found!")
            return False  # ✅ Prevents crashes
        return economy.convert_currency(user_id, total_cp)  # ✅ Now calls the function correctly

    @discord.app_commands.command(name="buy", description="Purchase an item from Stanley's shop.")
    async def buy(self, interaction: discord.Interaction, item: str):
        """Allows a player to buy an item if they have enough money and if it's in stock."""
        user_id = str(interaction.user.id)

        # Search for item in all categories
        found_item = None
        for category in SHOP_CATEGORIES.values():
            for shop_item in category.keys():
                if shop_item.lower() == item.lower():
                    found_item = category[shop_item]
                    item = shop_item  # Preserve proper item name formatting
                    break
            if found_item:
                break

        if found_item is None:
            await interaction.response.send_message(get_response("buy_not_available", item=item))
            return

        # Check stock
        if found_item["stock"] <= 0:
            await interaction.response.send_message(get_response("buy_no_stock", item=item))
            return

        item_price_cp = found_item["price_cp"]

        # Convert currency and check if the player can afford the item
        if not self.convert_currency(user_id, item_price_cp):
            await interaction.response.send_message(get_response("buy_no_money"))
            return

        # Deduct stock
        found_item["stock"] -= 1
        save_json(SHOP_FILE, SHOP_CATEGORIES)

        # Add item to player's inventory
        inventory_data = load_json(PLAYER_INVENTORY_FILE, {})

        if user_id not in inventory_data:
            inventory_data[user_id] = {}

        if item in inventory_data[user_id]:
            inventory_data[user_id][item] += 1
        else:
            inventory_data[user_id][item] = 1

        save_json(PLAYER_INVENTORY_FILE, inventory_data)

        await log_transaction("bought", interaction.user.name, item, item_price_cp // 100)
        await interaction.response.send_message(get_response("buy_success", user=interaction.user.name, item=item))

    @discord.app_commands.command(name="sell", description="Sell an item back to Stanley for half its value.")
    async def sell(self, interaction: discord.Interaction, item: str):
        """Allows a player to sell an item for half its value."""
        user_id = str(interaction.user.id)

        # Load inventory
        inventory_data = load_json(PLAYER_INVENTORY_FILE, {})

        # Check if the player owns the item
        if user_id not in inventory_data or item not in inventory_data[user_id] or inventory_data[user_id][item] <= 0:
            await interaction.response.send_message(f"❌ **Error:** You don't own a `{item}` to sell.")
            return

        # Find the item's price
        item_price_cp = None
        for category in SHOP_CATEGORIES.values():
            if item in category:
                item_price_cp = category[item]["price_cp"]
                break

        if item_price_cp is None:
            await interaction.response.send_message(f"❌ **Error:** `{item}` is not a recognized shop item.")
            return

        sell_price_cp = item_price_cp // 2  # Selling is half price

        # Deduct item from inventory (by quantity)
        inventory_data[user_id][item] -= 1
        if inventory_data[user_id][item] <= 0:
            del inventory_data[user_id][item]  # Remove if count reaches 0
        save_json(PLAYER_INVENTORY_FILE, inventory_data)

        # Add stock back to the shop
        for category in SHOP_CATEGORIES.values():
            if item in category:
                category[item]["stock"] += 1
                save_json(SHOP_FILE, SHOP_CATEGORIES)
                break

        # Retrieve Economy cog dynamically
        economy = self.get_economy_cog()  
        if economy:
            economy.add_gold(user_id, sell_price_cp)  # ✅ Calls `add_gold()` properly
        else:
            await interaction.response.send_message("❌ Error: Economy system unavailable. Please contact the DM.")

        await log_transaction("sold", interaction.user.name, item, sell_price_cp // 100)
        await interaction.response.send_message(f"💰 {interaction.user.mention} sold **{item.capitalize()}** for `{sell_price_cp // 100} gp`. Inventory updated.")

    @discord.app_commands.command(name="inventory", description="Check your inventory.")
    async def inventory(self, interaction: discord.Interaction):
        """Displays the player's current inventory."""
        user_id = str(interaction.user.id)

        # Load inventory from file instead of relying on memory
        inventory_data = load_json(PLAYER_INVENTORY_FILE, {})

        # Check if player has any items
        if user_id not in inventory_data or not inventory_data[user_id]:
            await interaction.response.send_message(
                f"🎒 {interaction.user.name}, you own absolutely nothing. Not even a rusty dagger. How tragic."
            )
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
        await interaction.response.send_message(f"🎒 **{interaction.user.name}'s Inventory (Page 1/{len(message_chunks)})**\n{message_chunks[0]}")

        for idx in range(1, len(message_chunks)):  # ✅ Use followup for additional messages
            await interaction.followup.send(f"🎒 (Page {idx+1}/{len(message_chunks)})\n{message_chunks[idx]}")

# Setup function to add the Cog to the bot
async def setup(bot):
    print("🔍 Debug: Registering shop_transactions commands...")  # ✅ Debugging
    cog = ShopTransactions(bot)
    await bot.add_cog(cog)
    print("✅ ShopTransactions commands registered successfully!")