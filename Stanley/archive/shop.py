import discord
from discord.ext import commands
from data_manager import (
    gold_data, PLAYER_INVENTORIES, ensure_currency, save_json, config,
    SHOP_CATEGORIES, load_shop_items, load_json, REQUESTS_FILE, REQUESTABLE_ITEMS_FILE,
    SHOP_FILE, PLAYER_INVENTORY_FILE
)
class Shop(commands.Cog):
    """Cog for Stanley's shop system."""

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="shop", description="Browse Stanley's legendary wares.")
    async def shop(self, interaction: discord.Interaction, category: str = None):
        """Lists available shop items by category, showing stock levels."""
        if not SHOP_CATEGORIES:
            await interaction.response.send_message(get_response("shop_no_items"))
            return

        # If no category is specified, show available categories first
        if category is None:
            greeting = get_response("shop_intro")  # Stanley's greeting message

            category_list = [
                f"🔹 **{c.replace('_', ' ').title()}** → `/shop {c}`" 
                for c in SHOP_CATEGORIES.keys()
            ]
            category_message = "\n".join(category_list)
            
            example_category = random.choice(list(SHOP_CATEGORIES.keys()))
            example_command = f"```/shop {example_category}```"

            await interaction.response.send_message(
                f"{greeting}\n\n"
                f"**🛍️ Available Categories:**\n{category_message}\n\n"
                f"💡 *Try browsing a category:* {example_command}"
            )
            return

        # Ensure category is formatted correctly
        category = category.lower().replace(" ", "_")
        if category not in SHOP_CATEGORIES:
            valid_categories = "\n".join(
                [f"🔹 **{c.replace('_', ' ').title()}** → `/shop {c}`" for c in SHOP_CATEGORIES.keys()]
            )
            await interaction.response.send_message(
                f"❌ **Error:** `{category}` is not a valid category.\n\n"
                f"**🛍️ Available Categories:**\n{valid_categories}\n\n"
                f"💡 *Try:* ```/shop {random.choice(list(SHOP_CATEGORIES.keys()))}```"
            )
            return

        # Display items in the selected category with stock
        item_list = []
        for item, data in SHOP_CATEGORIES[category].items():
            price_cp = data["price_cp"]
            stock = data["stock"]

            gp, sp, cp = price_cp // 100, (price_cp % 100) // 10, price_cp % 10
            price_str = f"{gp} gp, {sp} sp, {cp} cp".replace(" 0 gp,", "").replace(" 0 sp,", "").replace(" 0 cp", "")
            item_list.append(f"• **{item.capitalize()}** - {price_str} (Stock: {stock})")

        shop_message = "\n".join(item_list)
        await interaction.response.send_message(
            f"🛒 **{category.replace('_', ' ').title()} Available:**\n{shop_message}\n\n"
            f"_\"See something you like? Just `/buy item_name` and it's yours... for a price.\"_"
        )

    @discord.app_commands.command(name="buy", description="Purchase an item from Stanley's shop.")
    async def buy(self, interaction: discord.Interaction, item: str):
        """Allows a player to buy an item if they have enough money and if it's in stock."""
        user_id = str(interaction.user.id)

        # Search for item in all categories
        found_item = None
        for category in SHOP_CATEGORIES.values():
            for shop_item in category.keys():
                if shop_item.lower() == item:
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
        if not Economy.convert_currency(user_id, item_price_cp):
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

        # Add gold to the player
        from economy import add_gold
        add_gold(user_id, sell_price_cp)

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
        for idx, msg in enumerate(message_chunks):
            await interaction.response.send_message(f"🎒 **{interaction.user.name}'s Inventory (Page {idx+1}/{len(message_chunks)})**\n{msg}")

    @commands.command(name="broker")
    @commands.has_permissions(administrator=True)
    async def broker_add(self, ctx, action: str, item: str, price_gp: int, rarity: str, category: str):
        """Allows an admin to add an item to the requestable items list or the shop inventory."""
        
        # Ensure action is valid
        if action.lower() not in ["add_requestable", "add_shop", "view"]:
            await ctx.send("❌ **Error:** Invalid action. Use `/broker view`, `/broker add_requestable` or `/broker add_shop`.")
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

            await ctx.send(f"🛒 **Current Shop Items:**\n{shop_list}\n\n📜 **Requestable Items:**\n{request_list}")
            return

        if None in [item, price_gp, rarity, category]:
            await ctx.send("❌ **Error:** Missing parameters. Example: `/broker add_shop potion 50 common consumables`")
            return

        item = item.lower()
        category = category.lower()

        # Validate category
        valid_categories = ["consumables", "non_combat", "combat"]
        if category not in valid_categories:
            await ctx.send(f"❌ **Error:** `{category}` is not a valid category. Choose from: {', '.join(valid_categories)}.")
            return

        if action == "add_requestable":
            requestable_items = load_json(REQUESTABLE_ITEMS_FILE, {})
            
            if category not in requestable_items:
                requestable_items[category] = {}
                
            if item in requestable_items[category]:
                await ctx.send(f"⚠️ `{item}` is already in the requestable items list.")
                return
            
            requestable_items[category][item] = {"price_gp": price_gp, "rarity": rarity}
            save_json(REQUESTABLE_ITEMS_FILE, requestable_items)
            
            await ctx.send(f"✅ **{item.capitalize()}** has been added to the **requestable items list** under `{category}`.")

        elif action == "add_shop":
            shop_inventory = load_json(SHOP_FILE, {})
            
            if item in shop_inventory[category]:
                await ctx.send(f"⚠️ `{item}` is already in the shop inventory.")
                return
            
            shop_inventory[category][item] = {"price_cp": price_gp * 100, "stock": 1, "rarity": rarity}
            save_json(SHOP_FILE, shop_inventory)
            
            await ctx.send(f"✅ **{item.capitalize()}** has been added to the **shop inventory** under `{category}` with **1 in stock**.")

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
        if item not in requestable_items:
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

    @commands.command(name="requests")
    async def requests_list(self, ctx):
        """Shows all pending item requests."""
        from data_manager import load_json, REQUESTS_FILE

        requestable_items = load_json(REQUESTS_FILE, {})

        if not requestable_items or not any(isinstance(v, list) and v for v in requestable_items.values()):
            await ctx.send("📜 **Stanley flips through his ledger.**\n_\"Strangely quiet lately... No requests at all!\"_")
            return

        request_lines = ["📜 **Pending Requests:**"]
        
        for item, players in requestable_items.items():
            if isinstance(players, list) and players:  # ✅ Only list items with actual requests
                request_lines.append(f"• **{item.capitalize()}** → {', '.join(f'<@{p}>' for p in players)}")

        if len(request_lines) == 1:  # No valid requests found
            await ctx.send("📜 **Stanley flips through his ledger.**\n_\"Strangely quiet lately... No requests at all!\"_")
        else:
            await ctx.send("\n".join(request_lines))

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
    await bot.add_cog(Shop(bot))  # ✅ Await add_cog()
    print("✅ Shop Cog has been loaded successfully!")