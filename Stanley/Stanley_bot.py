import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")  # Ensure your token is stored in .env

# Define bot intents and setup
intents = discord.Intents.all()
intents.guilds = True  # Required for slash commands
intents.message_content = True  # Required for prefix commands

# Create the bot
bot = commands.Bot(
    command_prefix="!",  # Simple prefix for now
    intents=intents
)

@bot.event
async def on_ready():
    """Confirms that the bot is online."""
    print(f"✅ {bot.user} is now online!")
    
# @bot.command()
# async def ping(ctx):
#     """Simple test command to check if bot is working."""
#     await ctx.send("🏓 Pong!")

@bot.tree.command(name="ping", description="Test if the bot is working")
async def slash_ping(interaction: discord.Interaction):
    """Simple test slash command."""
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="force_test", description="Force test a new slash command")
async def force_test(interaction: discord.Interaction):
    """Force test to check if new slash commands register."""
    await interaction.response.send_message("🛠️ This is a forced test command!")

@bot.event
async def setup_hook():
    """Runs at bot startup to load all cogs and sync slash commands."""
    print("🔄 Running setup_hook()...")

    # Clear all commands before syncing new ones
    print("🗑️ Clearing all slash commands...")
    bot.tree.clear_commands(guild=None)  # ✅ Wipe global commands
    await bot.tree.sync()  # ✅ Apply the wipe
    print("✅ Cleared all slash commands!")

    # Load Cogs
    try:
        await bot.load_extension("sync_commands")  
        print("✅ Successfully loaded SyncCommands cog!")
    except Exception as e:
        print(f"❌ Failed to load SyncCommands cog: {e}")

    try:
        await bot.load_extension("economy")
        print("✅ Successfully loaded Economy cog!")
    except Exception as e:
        print(f"❌ Failed to load Economy cog: {e}")

    try:
        await bot.load_extension("shop_browse")
        print("✅ Successfully loaded ShopBrowse cog!")
    except Exception as e:
        print(f"❌ Failed to load ShopBrowse cog: {e}")

    try:
        await bot.load_extension("shop_transactions")
        print("✅ Successfully loaded ShopTransactions cog!")
    except Exception as e:
        print(f"❌ Failed to load ShopTransactions cog: {e}")

    try:
        await bot.load_extension("shop_requests")
        print("✅ Successfully loaded ShopRequests cog!")
    except Exception as e:
        print(f"❌ Failed to load ShopRequests cog: {e}")

    # ✅ Manually register ping & force_test
    # bot.tree.add_command(slash_ping)
    # print("🔄 Manually adding `/ping`...")
    # bot.tree.add_command(force_test)
    # print("🔄 Manually adding `/force_test`...")

    # Debug: Print all registered commands BEFORE syncing
    command_list = list(bot.tree.walk_commands())  
    print(f"🔍 Debug: Found {len(command_list)} commands before syncing:")
    for cmd in command_list:
        print(f" - {cmd.name}")

    # Resync commands
    try:
        print("🔄 Syncing commands with Discord...")
        synced = await bot.tree.sync()  
        print(f"✅ Synced {len(synced)} commands successfully!")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

# Run the bot
try:
    bot.run(TOKEN)
except discord.errors.LoginFailure:
    print("❌ Error: Invalid bot token! Check your `.env` file.")
except Exception as e:
    print(f"❌ Critical Error: {e}")