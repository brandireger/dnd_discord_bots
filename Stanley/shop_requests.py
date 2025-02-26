import discord
from discord.ext import commands
from data_manager import load_json, save_json, get_response, REQUESTS_FILE, REQUESTABLE_ITEMS_FILE

class ShopRequests(commands.Cog):
    """Handles item requests and broker interactions."""

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="request", description="Request an approved item from Stanley's catalog.")
    async def request_item(self, interaction: discord.Interaction, item: str):
        """Allows players to request an item, but only from pre-approved requestable items."""
        await interaction.response.defer(thinking=True)

        item = item.lower().strip()
        user_id = str(interaction.user.id)

        # Load requestable items
        requestable_items = load_json(REQUESTABLE_ITEMS_FILE, {})

        # Flatten categories into a single list of requestable item names
        valid_items = {item_name.lower(): category for category in requestable_items.values() for item_name in category}

        # Check if item exists in requestable list
        if item not in valid_items:
            await interaction.followup.send(
                f"❌ `{item}` is not a requestable item.\n"
                "📜 **Stanley flips through his catalog.**\n"
                "_\"You can only request pre-approved items. Try `/requests_available` to see the list!\"_"
            )
            return

        # Load existing requests
        requests_data = load_json(REQUESTS_FILE, {})

        if item not in requests_data:
            requests_data[item] = []

        # Check if user already requested the item
        if user_id in requests_data[item]:
            await interaction.followup.send(f"📜 **Stanley sighs.**\n_\"You've already requested `{item}`. Patience, adventurer!\"_")
            return

        # Add request
        requests_data[item].append(user_id)
        save_json(REQUESTS_FILE, requests_data)

        await interaction.followup.send(f"📜 **Stanley records your request.**\n_\"Give me some time, and I’ll see what I can do.\"_\nYour request for `{item}` has been added.")

    @discord.app_commands.command(name="requests_available", description="Lists all requestable items.")
    async def requests_available(self, interaction: discord.Interaction):
        """Lists all items that can be requested from Stanley."""
        await interaction.response.defer(thinking=True)

        requestable_items = load_json(REQUESTABLE_ITEMS_FILE, {})

        if not requestable_items:
            await interaction.followup.send("📜 **Stanley shrugs.**\n_\"Nothing is requestable at the moment!\"_")
            return

        # Format the list for display
        request_lines = ["📜 **Items Available for Request:**"]
        for category, items in requestable_items.items():
            item_list = ", ".join(f"`{item}`" for item in items)
            request_lines.append(f"**{category.title()}**: {item_list}")

        # Discord 2000-character limit handling
        message_chunks = []
        chunk = ""

        for line in request_lines:
            if len(chunk) + len(line) + 2 > 2000:  # +2 for newline characters
                message_chunks.append(chunk)
                chunk = ""
            chunk += line + "\n"

        if chunk:
            message_chunks.append(chunk)  # Add the last chunk

        # Send messages in multiple parts
        first_chunk = message_chunks.pop(0)  # Send the first chunk
        await interaction.followup.send(first_chunk)

        for idx, msg in enumerate(message_chunks):
            if idx == 0:
                await interaction.followup.send(msg)  # First message
            else:
                await interaction.followup.send(msg)  # Send remaining chunks

    @discord.app_commands.command(name="all_requests", description="View all pending item requests.")
    async def all_requests(self, interaction: discord.Interaction):
        """Shows all pending item requests."""
        await interaction.response.defer(thinking=True)

        requests_data = load_json(REQUESTS_FILE, {})

        if not requests_data or all(not users for users in requests_data.values()):
            await interaction.followup.send(get_response("requests_none"))
            return

        request_lines = ["📜 **Pending Requests:**"]
        for item, users in requests_data.items():
            if users:
                request_lines.append(f"• **{item.capitalize()}** → {', '.join(f'<@{u}>' for u in users)}")

        if len(request_lines) == 1:
            await interaction.followup.send("📜 **Stanley flips through his ledger.**\n_\"Strangely quiet lately... No requests at all!\"_")
        else:
            await interaction.followup.send("\n".join(request_lines))

    @discord.app_commands.command(name="request_add", description="(Admin) Add a new item to the requestable list.")
    @commands.has_permissions(administrator=True)  # ✅ Admins only
    async def request_add(self, interaction: discord.Interaction, item: str, price_gp: int, rarity: str, category: str):
        """Allows an admin to add an item to the requestable items list."""
        await interaction.response.defer(thinking=True)

        item = item.lower().strip()
        category = category.lower().strip()

        # Load existing requestable items
        requestable_items = load_json(REQUESTABLE_ITEMS_FILE, {})

        # Validate category
        valid_categories = requestable_items.keys()  # Uses existing categories
        if category not in valid_categories:
            await interaction.followup.send(f"❌ `{category}` is not a valid category.\n"
                                            "📜 **Stanley grumbles.**\n"
                                            "_\"Choose an existing category from `/requests_available`.\"_")
            return

        # Check if item already exists
        if item in requestable_items[category]:
            await interaction.followup.send(f"⚠️ `{item}` is already in the requestable items list.")
            return

        # Add new item
        requestable_items[category][item] = {"price_gp": price_gp, "rarity": rarity}
        save_json(REQUESTABLE_ITEMS_FILE, requestable_items)

        await interaction.followup.send(f"✅ **{item.capitalize()}** has been added to the **requestable items list** under `{category}`!")

    @discord.app_commands.command(name="request_approve", description="(Admin) Approve a requested item and add it to the shop.")
    @commands.has_permissions(administrator=True)  # ✅ Admins only
    async def request_approve(self, interaction: discord.Interaction, item: str, stock: int = 1):
        """Allows an admin to approve a request and move it into the shop."""
        await interaction.response.defer(thinking=True)

        item = item.lower().strip()

        # Load request & shop data
        requests_data = load_json(REQUESTS_FILE, {})
        shop_data = load_json(SHOP_FILE, {})
        requestable_items = load_json(REQUESTABLE_ITEMS_FILE, {})

        # Check if item is in the request list
        if item not in requests_data or not requests_data[item]:
            await interaction.followup.send(f"❌ `{item}` is not in the request list!")
            return
        if stock <= 0:
            await interaction.followup.send(f"❌ Cannot approve `{item}` with zero stock!")
            return

        # Find the item details in the requestable items list
        found_category = None
        found_item = None

        for category, items in requestable_items.items():
            if item in items:
                found_category = category
                found_item = items[item]
                break

        if not found_item:
            await interaction.followup.send(f"❌ `{item}` is not a valid requestable item.")
            return

        # Add item to the shop
        if found_category not in shop_data:
            shop_data[found_category] = {}

        shop_data[found_category][item] = {
            "price_cp": found_item["price_gp"] * 100,  # Convert GP to CP
            "stock": stock,
            "rarity": found_item["rarity"]
        }

        # Save changes
        save_json(SHOP_FILE, shop_data)
        save_json(REQUESTS_FILE, requests_data)

        # Remove item from requests list
        del requests_data[item]

        await interaction.followup.send(f"✅ **{item.capitalize()}** has been approved and added to Stanley's shop with `{stock}` in stock!")

async def setup(bot):
    print("🔍 Debug: Loading ShopRequests cog...")
    cog = ShopRequests(bot)
    await bot.add_cog(cog)
    print("✅ ShopRequests cog loaded!")

    if not bot.tree.get_command("request"):
        bot.tree.add_command(cog.request_item)
        print("🔄 Manually adding `/request`...")

    if not bot.tree.get_command("requests_available"):
        bot.tree.add_command(cog.requests_available)
        print("🔄 Manually adding `/requests_available`...")

    if not bot.tree.get_command("all_requests"):
        bot.tree.add_command(cog.all_requests)
        print("🔄 Manually adding `/all_requests`...")

    if not bot.tree.get_command("request_add"):
        bot.tree.add_command(cog.request_add)
        print("🔄 Manually adding `/request_add`...")

    if not bot.tree.get_command("request_approve"):
        bot.tree.add_command(cog.request_approve)
        print("🔄 Manually adding `/request_approve`...")

    print("🔄 Syncing shop request commands...")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands successfully!")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")