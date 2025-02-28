import discord
from discord.ext import commands
from discord import app_commands
from data_manager import load_json

class ShopBrowse(commands.Cog):
    """Cog for browsing Stanley's shop system."""

    def __init__(self, bot):
        self.bot = bot

    async def shop_autocomplete(interaction: discord.Interaction, command: discord.app_commands.Command, current: str):
        """Provides autocomplete suggestions for shop categories."""
        SHOP_CATEGORIES = load_json("stanley_shop.json")
        
        return [
            discord.app_commands.Choice(name=c.replace("_", " ").title(), value=c)
            for c in SHOP_CATEGORIES.keys() if current.lower() in c.lower()
        ]

    @app_commands.command(name="shop", description="Browse Stanley's legendary wares.")
    @app_commands.autocomplete(category=shop_autocomplete)
    async def shop(self, interaction: discord.Interaction, category: str = None):
        """Lists available shop items by category."""
        await interaction.response.defer(thinking=True)

        shared_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared_inventories")
        SHOP_CATEGORIES = load_json("stanley_shop.json")
        
        if not SHOP_CATEGORIES:
            await interaction.followup.send("⚠️ No shop items available!")
            return

        # If no category is specified, list available categories
        if not category:
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
async def setup(bot):
    """Loads the ShopBrowse cog into the bot."""
    cog = ShopBrowse(bot)
    await bot.add_cog(cog)  
    print(f"✅ {cog} cog loaded!")