import discord
import random
from discord.ext import commands
from discord import app_commands
from data_manager import load_json, SHOP_FILE

class ShopBrowse(commands.Cog):
    """Cog for browsing Stanley's shop system."""

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="shop", description="Browse Stanley's legendary wares.")
    async def shop(self, interaction: discord.Interaction, category: str = None):
        """Lists available shop items by category, showing stock levels."""
        SHOP_CATEGORIES = load_json(SHOP_FILE, {})  # ✅ Load fresh data at runtime
        
        if not SHOP_CATEGORIES:
            await interaction.response.send_message("⚠️ No shop items available!")
            return

        # If no category is specified, list available categories
        if category is None:
            greeting = "🛒 **Welcome to Stanley's Shop!**"
            category_list = "\n".join(
                [f"🔹 **{c.replace('_', ' ').title()}** → `/shop {c}`" for c in SHOP_CATEGORIES.keys()]
            )
            await interaction.response.send_message(
                f"{greeting}\n\n"
                f"**🛍️ Available Categories:**\n{category_list}\n\n"
                f"💡 *Copy and paste a category command to browse it!*"
            )
            return

        if category not in SHOP_CATEGORIES:
            await interaction.response.send_message(f"❌ **Error:** `{category}` is not a valid category.")
            return

        # Display items in the selected category with stock
        item_list = [
            f"• **{item.capitalize()}** - {data['price_cp'] // 100} gp (Stock: {data['stock']})"
            for item, data in SHOP_CATEGORIES[category].items()
        ]
        shop_message = "\n".join(item_list)

        await interaction.response.send_message(
            f"🛒 **{category.replace('_', ' ').title()} Available Items:**\n{shop_message}\n\n"
            f"_\"See something you like? Just `/buy item_name` and it's yours... for a price.\"_"
        )
        
async def setup(bot):
    print(f"🔍 Debug: Loading {__name__} cog...")  # ✅ Debug message
    await bot.add_cog(ShopBrowse(bot))
    print(f"✅ {__name__} cog loaded successfully!")