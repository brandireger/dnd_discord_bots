import discord
from discord.ext import commands
from discord import app_commands

class AdminCommands(commands.Cog):
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

    @app_commands.command(name="audit_log", description="(Admin) View recent shop transactions.")
    @commands.has_permissions(administrator=True)  # ✅ Admins only
    async def audit_log(self, interaction: discord.Interaction, limit: int = 10):
        """Allows admins to view recent shop transactions."""
        await interaction.response.defer(thinking=True)

        # Load audit log
        audit_data = load_json("inventory_logs.json")

        if not audit_data:
            await interaction.followup.send(get_response("audit_log_empty"))
            return

        # Limit number of transactions displayed
        audit_data = audit_data[-limit:]
        log_lines = ["📜 **Recent Transactions:**"]
        for entry in reversed(audit_data):  # Reverse so latest is at the top
            log_lines.append(
                f"• `{entry['timestamp'].split('T')[0]}` - **{entry['user']}** {entry['action']} `{entry['item']}` for `{entry['price_gp']} gp`"
            )
            
        # Ensure message fits Discord limits
        message_chunks = [log_lines[i : i + 10] for i in range(0, len(log_lines), 10)]
        for chunk in message_chunks:
            await interaction.followup.send("\n".join(chunk))


async def setup(bot):
    print("🔍 Debug: Loading AdminCommands cog...")
    await bot.add_cog(AdminCommands(bot))  
    print("✅ AdminCommands cog loaded!")