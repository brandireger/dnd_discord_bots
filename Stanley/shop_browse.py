import discord
from discord.ext import commands
from data_manager import load_json, SHOP_FILE, PLAYER_INVENTORY_FILE

class ShopBrowse(commands.Cog):
    """Cog for browsing Stanley's shop system."""

    def __init__(self, bot):
        self.bot = bot

    async def shop_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[discord.app_commands.Choice[str]]:
        """Provides autocomplete suggestions for shop categories."""
        SHOP_CATEGORIES = load_json(SHOP_FILE, {})  # ✅ Load fresh shop data
        return [
            discord.app_commands.Choice(name=c.replace("_", " ").title(), value=c)
            for c in SHOP_CATEGORIES.keys()
            if current.lower() in c.lower()
        ]  # ✅ Filters categories based on user input

    @discord.app_commands.command(name="shop", description="Browse Stanley's legendary wares.")
    @discord.app_commands.autocomplete(category=shop_autocomplete)
    async def shop(self, interaction: discord.Interaction, category: str = None):
        """Lists available shop items by category."""
        await interaction.response.defer(thinking=True)

        SHOP_CATEGORIES = load_json(SHOP_FILE, {})  # ✅ Load fresh data at runtime
        
        if not SHOP_CATEGORIES:
            await interaction.followup.send("⚠️ No shop items available!")
            return

        # If no category is specified, list available categories
        if category is None:
            greeting = "🛒 **Welcome to Stanley's Shop!**"
            category_list = "\n".join(
                [f"🔹 **{c.replace('_', ' ').title()}** → `/shop {c}`" for c in SHOP_CATEGORIES.keys()]
            )
            await interaction.followup.send(
                f"{greeting}\n\n"
                f"**🛍️ Available Categories:**\n{category_list}\n\n"
                f"💡 *Try selecting a category from the autocomplete list!*"
            )
            return

        # Validate category
        if category not in SHOP_CATEGORIES:
            await interaction.followup.send(f"❌ **Error:** `{category}` is not a valid category.")
            return

        # Display items in the selected category with stock
        item_list = [
            f"• **{item.capitalize()}** - {data['price_cp'] // 100} gp (Stock: {data['stock']})"
            for item, data in SHOP_CATEGORIES[category].items()
        ]
        shop_message = "\n".join(item_list)

        await interaction.followup.send(
            f"🛒 **{category.replace('_', ' ').title()} Available Items:**\n{shop_message}\n\n"
            f"_\"See something you like? Just `/buy item_name` and it's yours... for a price.\"_"
        )

    @discord.app_commands.command(name="inventory", description="Check your inventory.")
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

async def setup(bot):
    print("🔍 Debug: Loading ShopBrowse cog...")
    cog = ShopBrowse(bot)
    await bot.add_cog(cog)
    print("✅ ShopBrowse cog loaded!")

    if not bot.tree.get_command("shop"):
        bot.tree.add_command(cog.shop)
        print("🔄 Manually adding `/shop`...")

    if not bot.tree.get_command("inventory"):
        bot.tree.add_command(cog.inventory)
        print("🔄 Manually adding `/inventory`...")

    print("🔄 Syncing shop commands...")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands successfully!")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")