import discord
from discord.ext import commands
import logging
import os
import random
import time
from data_manager import load_json, save_json
import shop_browse
import shop_transactions
import shop_requests
import economy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")  # Ensure your token is stored in .env
GUILD_ID = os.getenv("GUILD_ID")

# ✅ Define Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COGS = [
    "admin_commands", 
    "economy", 
    "shop_browse", 
    "shop_requests", 
    "shop_transactions"
    ]

CLEAR_COMMANDS_ON_START = False 

logger = logging.getLogger(__name__)

# Define bot intents and setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

def split_text(text, max_length=1024):
    """Splits a long text into chunks that fit Discord's limit."""
    return [text[i : i + max_length] for i in range(0, len(text), max_length)]

@bot.event
async def on_ready():
    """Confirms that the bot is online."""
    print("🔄 Running setup_hook()...")
    if CLEAR_COMMANDS_ON_START:
        print("🚨 Clearing all slash commands before syncing...")
        await bot.tree.clear_commands(guild=discord.Object(id=YOUR_GUILD_ID))

    # Load cogs
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded {cog}.py")
        except Exception as e:
            print(f"❌ Failed to load {cog}.py: {e}")

    print("🔄 Syncing bot commands...")
    try:
        bot.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))  # ✅ Force sync to your guild
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))  
        print(f"✅ Synced {len(synced)} commands successfully!")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

@bot.tree.command(name="ping", description="Test if the bot is working")
async def slash_ping(interaction: discord.Interaction):
    """Simple test slash command."""
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="stanley_help", description="Displays Stanley's available commands.")
async def stanley_help(interaction: discord.Interaction):
    """Dynamically displays all available bot commands."""
    embed = discord.Embed(title="📜 Stanley's Commands", color=discord.Color.green())

    admin_commands = []
    regular_commands = []

    # Retrieve and categorize commands
    for cmd in bot.tree.walk_commands():
        cmd_entry = f"**/{cmd.name}** - {cmd.description}"

        # Check if it's an admin command
        if hasattr(cmd, "default_permissions") and cmd.default_permissions and cmd.default_permissions.administrator:
            admin_commands.append(cmd_entry)
        else:
            regular_commands.append(cmd_entry)

    # **Add General Commands** (Split if too long)
    if regular_commands:
        for index, chunk in enumerate(split_text("\n".join(regular_commands))):
            embed.add_field(
                name=f"🧪 General Commands (Part {index + 1})" if index > 0 else "🧪 General Commands",
                value=chunk,
                inline=False
            )

    # **Add Admin Commands** (Split if too long)
    if admin_commands:
        for index, chunk in enumerate(split_text("\n".join(admin_commands))):
            embed.add_field(
                name=f"⚙️ Admin Commands (Part {index + 1})" if index > 0 else "⚙️ Admin Commands",
                value=chunk,
                inline=False
            )

    await interaction.response.send_message(embed=embed)

# Run the bot
try:
    bot.run(TOKEN)
except discord.errors.LoginFailure:
    print("❌ Error: Invalid bot token! Check your `.env` file.")
except Exception as e:
    print(f"❌ Critical Error: {e}")