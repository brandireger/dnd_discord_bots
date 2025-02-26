import asyncio
from discord.ext import commands
from data_manager import save_json, load_json, log_transaction, GOLD_FILE, PLAYER_INVENTORY_FILE

class Admin(commands.Cog):
    """Cog for admin-related commands, including resets."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="resetall")
    @commands.has_permissions(administrator=True)
    async def resetall(self, ctx):
        """Resets all player inventories and balances to default values after confirmation."""
        
        confirmation_message = await ctx.send(
            "⚠️ **WARNING:** This will **erase all inventories and reset all player balances**. "
            "Type `CONFIRM RESET` (case insensitive) to proceed or `CANCEL` to abort."
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=30)  # Wait for response
        except asyncio.TimeoutError:
            await ctx.send("⏳ Reset timed out. No changes made.")
            return

        if msg.content.strip().lower() == "confirm reset":
            # Load current data
            gold_data = load_json(GOLD_FILE, {})
            inventory_data = load_json(PLAYER_INVENTORY_FILE, {})

            # Reset all gold and inventory data
            gold_data.clear()
            inventory_data.clear()

            save_json(GOLD_FILE, gold_data)
            save_json(PLAYER_INVENTORY_FILE, inventory_data)

            await ctx.send("✅ **All player inventories and balances have been reset.**")
            await log_transaction(ctx, "🚨 **ADMIN RESET:** All inventories and balances were wiped.")

            print("🚨 Admin reset triggered by", ctx.author.name)
        else:
            await ctx.send("❌ Reset canceled. No changes made.")

# Setup function to add the Cog to the bot
async def setup(bot):
    await bot.add_cog(Admin(bot))
    print("✅ Admin Cog has been loaded successfully!")