import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")  # Ensure your token is stored in .env

# Define bot intents and setup
intents = discord.Intents.all()
intents.guilds = True  # Required for handling guild data

# Create the bot with proper prefix handling
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("/"),
    intents=intents,
    tree_cls=discord.app_commands.CommandTree  # ✅ Ensures bot supports slash commands
)

BOT_NAME = "Stanley CoinMancer"

COGS = ["economy", "shop_transactions", "shop_browse", "shop_requests"]  # ✅ Ensure all cogs are loaded

async def load_cogs():
    for cog in COGS:
        try:
            if cog in bot.extensions:  # ✅ Prevent duplicate loading
                print(f"⚠️ {cog} is already loaded, skipping...")
                continue

            print(f"🔍 Debug: Attempting to load {cog}...")
            await bot.load_extension(cog)  # ✅ No need for "cogs." anymore
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog}: {e}")
            traceback.print_exc()

@bot.command()
@commands.is_owner()
async def sync(ctx):
    """Manually syncs commands with Discord."""
    try:
        synced = await bot.tree.sync()  # ✅ Force re-sync
        await ctx.send(f"✅ Synced {len(synced)} commands!")
    except Exception as e:
        await ctx.send(f"❌ Error syncing commands: {e}")

@bot.event
async def on_ready():
    print(f"{BOT_NAME} is now online!")
    await bot.change_presence(activity=discord.Game(name="Making Deals..."))

    # Print all registered commands
    print("🔍 Debug: Current registered commands:")
    for cmd in bot.tree.walk_commands():
        print(f" - {cmd.name}")

@bot.event
async def setup_hook():
    """Runs at bot startup to load all cogs and sync slash commands."""
    print("🔄 Running setup_hook()...")  

    await load_cogs()  # ✅ Load cogs first

    print("🔍 Debug: Loaded cogs:", bot.cogs.keys())

    # Debug: Print all registered commands BEFORE syncing
    command_list = list(bot.tree.walk_commands())  # Convert to list to debug
    print(f"🔍 Debug: Found {len(command_list)} commands before syncing:")
    for cmd in command_list:
        print(f" - {cmd.name}")

    try:
        print("🔄 Syncing commands with Discord...")
        synced = await bot.tree.sync()  # ✅ Ensure sync
        print(f"✅ Synced {len(synced)} commands successfully!")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
        
@bot.event
async def on_shutdown():
    """Handles cleanup when the bot is shutting down."""
    print("📜 Stanley's Bazaar is closing... Cleaning up!")
    await bot.close()

# Run the bot
try:
    bot.run(TOKEN)
except discord.errors.LoginFailure:
    print("❌ Error: Invalid bot token! Check your `.env` file.")
except KeyboardInterrupt:
    print(f"\n❌ {BOT_NAME} is shutting down gracefully...")
except Exception as e:
    print(f"❌ Critical Error: {e}")
finally:
    print("📜 All transactions closed. Stanley's Bazaar is now closed.")