import discord
from discord.ext import commands
from data_manager import (
    gold_data, PLAYER_INVENTORIES, ensure_currency, save_json, config,
    SHOP_CATEGORIES, load_shop_items, load_json, REQUESTS_FILE, REQUESTABLE_ITEMS_FILE,
    SHOP_FILE, PLAYER_INVENTORY_FILE
)

class ShopRequests(commands.Cog):
    """Handles item requests and broker interactions."""

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="broker", description="Manage Stanley's requestable items and inventory.")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def broker_add(self, interaction: discord.Interaction, action: str, item: str, price_gp: int, rarity: str, category: str):
        """Allows an admin to add an item to the requestable items list or the shop inventory."""
        
        # Ensure action is valid
        if action.lower() not in ["add_requestable", "add_shop", "view"]:
            await interaction.response.send_message("❌ **Error:** Invalid action. Use `/broker view`, `/broker add_requestable`, or `/broker add_shop`.")
            return

        # Load existing data
        from data_manager import load_json, save_json, REQUESTS_FILE, SHOP_FILE, REQUESTABLE_ITEMS_FILE

        if action.lower() == "view":
            shop_inventory = load_json(SHOP_FILE, {})
            requestable_items = load_json(REQUESTABLE_ITEMS_FILE, {})

            shop_list = "\n".join(
                [f"• {i.capitalize()} ({d['price_cp'] // 100}gp)" for c in shop_inventory.values() for i, d in c.items()]
            )
            request_list = "\n".join(
                [f"• {i.capitalize()} ({d['price_gp']}gp)" for c in requestable_items.values() for i, d in c.items()]
            )

            await interaction.response.send_message(f"🛒 **Current Shop Items:**\n{shop_list}\n\n📜 **Requestable Items:**\n{request_list}")
            return

        if None in [item, price_gp, rarity, category]:
            await interaction.response.send_message("❌ **Error:** Missing parameters. Example: `/broker add_shop potion 50 common consumables`")
            return

        item = item.lower()
        category = category.lower()

        # Validate category
        valid_categories = ["consumables", "non_combat", "combat"]
        if category not in valid_categories:
            await interaction.response.send_message(f"❌ **Error:** `{category}` is not a valid category. Choose from: {', '.join(valid_categories)}.")
            return

        if action == "add_requestable":
            requestable_items = load_json(REQUESTABLE_ITEMS_FILE, {})
            
            if category not in requestable_items:
                requestable_items[category] = {}
                
            if item in requestable_items[category]:
                await interaction.response.send_message(f"⚠️ `{item}` is already in the requestable items list.")
                return
            
            requestable_items[category][item] = {"price_gp": price_gp, "rarity": rarity}
            save_json(REQUESTABLE_ITEMS_FILE, requestable_items)
            
            await interaction.response.send_message(f"✅ **{item.capitalize()}** has been added to the **requestable items list** under `{category}`.")

        elif action == "add_shop":
            shop_inventory = load_json(SHOP_FILE, {})
            
            if category not in shop_inventory:
                shop_inventory[category] = {}

            if item in shop_inventory[category]:  # ✅ Correct condition
                await interaction.response.send_message(f"⚠️ `{item}` is already in the shop inventory.")
                return
            
            shop_inventory[category][item] = {"price_cp": price_gp * 100, "stock": 1, "rarity": rarity}
            save_json(SHOP_FILE, shop_inventory)
            
            await interaction.response.send_message(f"✅ **{item.capitalize()}** has been added to the **shop inventory** under `{category}` with **1 in stock**.")

    @discord.app_commands.command(name="request", description="Request an item from Stanley's catalog.")
    async def request_item(self, interaction: discord.Interaction, *, item: str = None):
        """Allows players to request an item from Stanley."""
        if not item:
            await interaction.response.send_message("❌ **Error:** You must specify an item to request. Example: `/request rope`")
            return

        item = item.lower().strip()
        user_id = str(interaction.user.id)

        # Load requestable items
        requestable_items = load_json(REQUESTABLE_ITEMS_FILE, {})

        # Check if item exists in the requestable list
        found_item = None
        for category, items in requestable_items.items():
            if item in items:
                found_item = category
                break

        if not found_item:
            await interaction.response.send_message(f"❌ **Error:** `{item}` is not a requestable item.")
            return

        # Load active requests
        active_requests = load_json(REQUESTS_FILE, {})

        # Add request
        if item not in active_requests:
            active_requests[item] = []

        if user_id not in active_requests[item]:
            active_requests[item].append(user_id)

        save_json(REQUESTS_FILE, active_requests)

        await interaction.response.send_message(f"📜 **Stanley records your request.**\n_\"Give me some time, and I’ll see what I can do.\"_\nYour request for `{item}` has been added.")

    @discord.app_commands.command(name="requests", description="View all pending item requests.")
    async def requests_list(self, interaction: discord.Interaction):
        """Shows all pending item requests."""
        from data_manager import load_json, REQUESTS_FILE

        requestable_items = load_json(REQUESTS_FILE, {})

        if not requestable_items or not any(isinstance(v, list) and v for v in requestable_items.values()):
            await interaction.response.send_message("📜 **Stanley flips through his ledger.**\n_\"Strangely quiet lately... No requests at all!\"_")
            return

        request_lines = ["📜 **Pending Requests:**"]
        
        for item, players in requestable_items.items():
            if isinstance(players, list) and players:  # ✅ Only list items with actual requests
                request_lines.append(f"• **{item.capitalize()}** → {', '.join(f'<@{p}>' for p in players)}")

        if len(request_lines) == 1:  # No valid requests found
            await interaction.response.send_message("📜 **Stanley flips through his ledger.**\n_\"Strangely quiet lately... No requests at all!\"_")
        else:
            await interaction.response.send_message("\n".join(request_lines))

    @discord.app_commands.command(name="requests_available", description="Lists all requestable items.")
    async def requests_available(self, interaction: discord.Interaction):
        """Lists all items that can be requested from Stanley."""
        requestable_items = load_json(REQUESTABLE_ITEMS_FILE, {})

        if not requestable_items:
            await interaction.response.send_message("📜 **Stanley shrugs.**\n_\"Nothing is requestable at the moment!\"_")
            return

        # Format the list for display
        request_lines = ["📜 **Items Available for Request:**"]
        request_lines.append(", ".join(f"`{item}`" for item in requestable_items.keys()))

        await interaction.response.send_message("\n".join(request_lines))

# Setup function to add the Cog to the bot
async def setup(bot):
    print(f"🔍 Debug: Loading {__name__} cog...")  # ✅ Debugging message
    await bot.add_cog(ShopRequests(bot))  # ✅ Ensure this line is running
    print(f"✅ {__name__} cog loaded successfully!")