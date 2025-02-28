import discord
from discord import app_commands
from discord.ext import commands
import logging
import time
import os
import asyncio
import traceback 
import random
from bot_logging import logger
from data_manager import ensure_file_exists, load_json
from dotenv import load_dotenv

# ✅ Ensure logs directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# ✅ Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG for more details
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/basil_bot.log"),  # ✅ Save logs to a file
        logging.StreamHandler()  # ✅ Show logs in the terminal
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
GUILD_ID = int(GUILD_ID) if GUILD_ID and GUILD_ID.isdigit() else None

# ✅ Ensure Required Files Exist Before Bot Starts
REQUIRED_FILES = [
    "gold_data.json",
    "player_stats.json",
    "basil_inventory.json"
]
for file in REQUIRED_FILES:
    ensure_file_exists(file)

# Define bot intents and setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

COGS = [
    "admin_commands", 
    "alchemy", 
    "basil_craft", 
    "economy", 
    "herbalism", 
    "inventory_commands",
    "player_stats",
    "responses"
    ]

PRESENCE_MESSAGES = [
    "Brewing Potions...",
    "Exploring the Herbal Archives...",
    "Experimenting with Alchemy...",
    "Collecting Rare Ingredients...",
]

def split_text(text, max_length=1024):
    """Splits a long text into chunks that fit Discord's limit."""
    return [text[i : i + max_length] for i in range(0, len(text), max_length)]

@bot.event
async def on_ready():
    """Runs when Basil is online."""
    logger.info(f"🌿 Basil is online! Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(name=random.choice(PRESENCE_MESSAGES)))

    # Track setup timing
    start_time = time.time()

    for cog in COGS:
        try:
            await bot.load_extension(cog)
            logger.info(f"✅ Loaded {cog}.py")
        except Exception as e:
            logger.error(f"❌ Failed to load {cog}.py:\n{traceback.format_exc()}")  # ✅ Logs full error trace
    
    logger.info("🔄 Syncing bot commands...")
    try:
        if GUILD_ID:
            bot.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
            synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        else:
            synced = await bot.tree.sync()
   
        logger.info(f"✅ Synced {len(synced)} commands successfully!")
    
        elapsed_time = time.time() - start_time
        logger.info(f"🚀 Basil fully loaded in {elapsed_time:.2f} seconds!")
    except Exception as e:
        logger.error(f"❌ Error syncing commands:\n{traceback.format_exc()}")
        
@bot.tree.command(name="basil_help", description="Displays Basil's available commands.")
async def basil_help(interaction: discord.Interaction):
    """Dynamically displays all available bot commands."""
    embed = discord.Embed(title="📜 Basil's Commands", color=discord.Color.green())

    admin_commands = []
    regular_commands = []

    # Retrieve and categorize commands
    for cmd in bot.tree.walk_commands():
        cmd_entry = f"**/{cmd.name}** - {cmd.description}"

        # Check if it's an admin command
        if isinstance(cmd, app_commands.Command) and cmd.default_permissions and cmd.default_permissions.administrator:
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

@bot.tree.command(name="sync", description="Manually sync bot commands (Admin only).")
@commands.has_permissions(administrator=True) 
async def sync(interaction: discord.Interaction):
    """Manually sync slash commands (Admin only)."""
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        await interaction.response.send_message(f"✅ Synced `{len(synced)}` commands successfully!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error syncing commands: {e}", ephemeral=True)

if __name__ == "__main__":
    try:
        logger.info("🚀 Starting Basil...")
        bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"🔥 Critical error on startup:\n{traceback.format_exc()}")  # ✅ Logs full traceback