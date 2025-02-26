import discord
from discord.ext import commands
from data_manager import load_json, save_json, get_response, SHOP_FILE, GOLD_FILE, PLAYER_INVENTORY_FILE

class ShopTransactions(commands.Cog):
    """Cog for handling purchases in Stanley's shop."""

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="buy", description="Purchase an item from Stanley's shop.")
    async def buy(self, interaction: discord.Interaction, item: str):
        """Allows players to buy an item if they have enough money and if it's in stock."""
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        shop_data = load_json(SHOP_FILE, {})
        gold_data = load_json(GOLD_FILE, {})
        inventory_data = load_json(PLAYER_INVENTORY_FILE, {})

        item = item.lower().strip()

        print(f"🔍 Debug: {interaction.user.name} is attempting to buy `{item}`.")

        # Search for item in all categories
        found_item = None
        for category in shop_data.values():
            for shop_item in category.keys():
                if shop_item.lower() == item:
                    found_item = category[shop_item]
                    item = shop_item  # Preserve proper item name formatting
                    break
            if found_item:
                break

        if not found_item:
            await interaction.followup.send(get_response("buy_not_available", item=item))
            return

        # Check stock
        if found_item["stock"] <= 0:
            await interaction.followup.send(get_response("buy_no_stock", item=item))
            return

        item_price_cp = found_item["price_cp"]
        player_cp = (gold_data.get(user_id, {"gp": 10, "sp": 0, "cp": 0})["gp"] * 100 +
                     gold_data.get(user_id, {"gp": 10, "sp": 0, "cp": 0})["sp"] * 10 +
                     gold_data.get(user_id, {"gp": 10, "sp": 0, "cp": 0})["cp"])

        if player_cp < item_price_cp:
            await interaction.followup.send(f"❌ You don't have enough gold to buy `{item}`.")
            return

        # Deduct price from player's gold
        player_cp -= item_price_cp
        gold_data[user_id] = {"gp": player_cp // 100, "sp": (player_cp % 100) // 10, "cp": player_cp % 10}
        save_json(GOLD_FILE, gold_data)

        # Deduct stock
        found_item["stock"] -= 1
        save_json(SHOP_FILE, shop_data)

        # Add item to player's inventory
        if not isinstance(inventory_data.get(user_id), dict):  # ✅ Ensure it's a dictionary
            inventory_data[user_id] = {}

        inventory_data[user_id][item] = inventory_data[user_id].get(item, 0) + 1
        save_json(PLAYER_INVENTORY_FILE, inventory_data)

        await interaction.followup.send(get_response("buy_success", user=interaction.user.name, item=item))

    @discord.app_commands.command(name="sell", description="Sell an item back to Stanley for half its value.")
    async def sell(self, interaction: discord.Interaction, item: str):
        """Allows a player to sell an item for half its value."""
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        shop_data = load_json(SHOP_FILE, {})
        gold_data = load_json(GOLD_FILE, {})
        inventory_data = load_json(PLAYER_INVENTORY_FILE, {})

        print(f"🔍 Debug: {interaction.user.name} is attempting to sell `{item}`.")

        # Ensure inventory exists
        if user_id not in inventory_data or not isinstance(inventory_data[user_id], dict):
            await interaction.followup.send(f"❌ {interaction.user.mention}, you don't have anything to sell!")
            return

        item = item.lower().strip()

        # Check if the player owns the item
        if item not in (i.lower() for i in inventory_data[user_id]):
            await interaction.followup.send(get_response("sell_no_item", user=interaction.user.name, item=item))
            return

        # Find the item's price
        found_item = None
        for category in shop_data.values():
            for shop_item, data in category.items():
                if shop_item.lower() == item:
                    found_item = data
                    item = shop_item  # Preserve proper item name formatting
                    break
            if found_item:
                break

        if not found_item:
            await interaction.followup.send(get_response("sell_not_shop_item", user=interaction.user.name, item=item))
            return

        sell_price_cp = found_item["price_cp"] // 2  # Selling is half price

        # Remove item from inventory
        inventory_data[user_id][item] -= 1
        if inventory_data[user_id][item] <= 0:
            del inventory_data[user_id][item]  # Remove if count reaches 0
        save_json(PLAYER_INVENTORY_FILE, inventory_data)

        # Add stock back to the shop
        for category in shop_data.values():
            if item in category:
                category[item]["stock"] += 1
                save_json(SHOP_FILE, shop_data)
                break

        # Add gold to player
        total_cp = sell_price_cp
        player_cp = (gold_data.get(user_id, {"gp": 10, "sp": 0, "cp": 0})["gp"] * 100 +
                    gold_data.get(user_id, {"gp": 10, "sp": 0, "cp": 0})["sp"] * 10 +
                    gold_data.get(user_id, {"gp": 10, "sp": 0, "cp": 0})["cp"])

        player_cp += total_cp
        gold_data[user_id] = {"gp": player_cp // 100, "sp": (player_cp % 100) // 10, "cp": player_cp % 10}
        save_json(GOLD_FILE, gold_data)

        await interaction.followup.send(get_response("sell_success", user=interaction.user.name, item=item, price_gp=sell_price_cp // 100))

    @discord.app_commands.command(name="audit_log", description="(Admin) View recent shop transactions.")
    @commands.has_permissions(administrator=True)  # ✅ Admins only
    async def audit_log(self, interaction: discord.Interaction, limit: int = 10):
        """Allows admins to view recent shop transactions."""
        await interaction.response.defer(thinking=True)

        # Load audit log
        audit_data = load_json(AUDIT_LOG_FILE, [])

        if not audit_data:
            await interaction.followup.send(get_response("audit_log_empty"))
            return

        # Limit number of transactions displayed
        audit_data = audit_data[-limit:]

        # Format transactions
        log_lines = ["📜 **Recent Transactions:**"]
        for entry in reversed(audit_data):  # Reverse so latest is at the top
            timestamp = entry["timestamp"].split("T")[0]  # Get only the date
            log_lines.append(f"• `{timestamp}` - **{entry['user']}** {entry['action']} `{entry['item']}` for `{entry['price_gp']} gp`")

        # Send messages in chunks if needed
        message_chunks = []
        chunk = ""
        for line in log_lines:
            if len(chunk) + len(line) + 2 > 2000:
                message_chunks.append(chunk)
                chunk = ""
            chunk += line + "\n"
        if chunk:
            message_chunks.append(chunk)

        for msg in message_chunks:
            await interaction.followup.send(msg)

async def setup(bot):
    print("🔍 Debug: Loading ShopTransactions cog...")
    cog = ShopTransactions(bot)
    await bot.add_cog(cog)
    print("✅ ShopTransactions cog loaded!")

    if not bot.tree.get_command("buy"):
        bot.tree.add_command(cog.buy)
        print("🔄 Manually adding `/buy`...")

    if not bot.tree.get_command("sell"):
        bot.tree.add_command(cog.sell)
        print("🔄 Manually adding `/sell`...")

    if not bot.tree.get_command("audit_log"):
        bot.tree.add_command(cog.audit_log)
        print("🔄 Manually adding `/audit_log`...")

    print("🔄 Syncing shop transaction commands...")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands successfully!")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")