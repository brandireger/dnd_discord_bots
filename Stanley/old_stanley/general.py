import discord
from discord.ext import commands

class General(commands.Cog):
    """General bot commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test_command(self, ctx):
        """Test if commands are being processed."""
        await ctx.send("✅ Stanley is processing commands correctly!")

    @bot.command()
    @commands.is_owner()
    async def sync(ctx, force: bool = False):
        """Manually syncs slash commands with Discord. Use `/sync True` to force a sync."""
        if force:
            try:
                synced = await bot.tree.sync()
                await ctx.send(f"✅ Synced {len(synced)} commands!")
                print(f"✅ Synced {len(synced)} commands!")
            except Exception as e:
                print(f"❌ Error syncing commands: {e}")
        else:
            await ctx.send("ℹ️ Use `/sync True` to manually resync commands.")

async def setup(bot):
    await bot.add_cog(General(bot))