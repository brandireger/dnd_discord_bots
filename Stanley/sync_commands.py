import discord
from discord.ext import commands

class SyncCommands(commands.Cog):
    """Cog for syncing commands."""

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="sync", description="Manually sync slash commands with Discord.")
    async def sync(self, interaction: discord.Interaction, guild_id: int = None):
        """Syncs slash commands globally or for a specific guild."""
        
        # ✅ Defer the response immediately to prevent timeout
        await interaction.response.defer(thinking=True)

        print(f"🛠️ Debug: `/sync` command triggered by {interaction.user} (Guild: {interaction.guild.id})")

        try:
            if guild_id:
                guild = discord.Object(id=guild_id)
                synced = await self.bot.tree.sync(guild=guild)
                await interaction.followup.send(f"✅ Synced {len(synced)} commands for guild `{guild_id}`!")
            else:
                synced = await self.bot.tree.sync()
                await interaction.followup.send(f"✅ Synced {len(synced)} global commands!")

        except Exception as e:
            print(f"❌ Debug: `/sync` failed with error: {e}")
            await interaction.followup.send(f"❌ Error syncing commands: {e}")

    @commands.command(name="force_sync")
    async def force_sync(self, ctx):
        """Force sync slash commands manually while Stanley is running."""
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"✅ Forced sync completed! Synced {len(synced)} commands.")
            print(f"✅ Forced sync completed! Synced {len(synced)} commands.")
        except Exception as e:
            await ctx.send(f"❌ Error syncing commands: {e}")
            print(f"❌ Error syncing commands: {e}")

    @commands.command(name="clear_commands")
    async def clear_commands(self, ctx):
        """Forcefully removes all slash commands from Discord."""
        try:
            self.bot.tree.clear_commands(guild=None)  # Wipe all global commands
            await self.bot.tree.sync()  # Apply the changes
            await ctx.send("✅ All slash commands have been cleared!")
            print("✅ Cleared all slash commands.")
        except Exception as e:
            await ctx.send(f"❌ Failed to clear commands: {e}")
            print(f"❌ Failed to clear commands: {e}")

async def setup(bot):
    print("🔍 Debug: Loading SyncCommands cog...")
    await bot.add_cog(SyncCommands(bot))  
    print("✅ SyncCommands cog loaded!")