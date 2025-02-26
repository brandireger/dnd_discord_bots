import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

if not TOKEN:
    raise ValueError("Missing BOT_TOKEN in environment variables.")
if not GUILD_ID:
    raise ValueError("Missing GUILD_ID in environment variables.")

GUILD_ID = int(GUILD_ID)

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
    "responses"
    ]

def split_text(text, max_length=1024):
    """Splits a long text into chunks that fit Discord's limit."""
    return [text[i : i + max_length] for i in range(0, len(text), max_length)]

@bot.event
async def on_ready():
    print(f"🌿 Basil is online! Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(name="Brewing Potions"))

CLEAR_COMMANDS_ON_START = False 

@bot.event
async def setup_hook():
    """Loads all cogs and syncs commands in the current guild only."""
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

@bot.tree.command(name="sync", description="Manually sync bot commands (Admin only).")
async def sync(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need to be an admin to use this!", ephemeral=True)
        return

    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        await interaction.response.send_message(f"✅ Synced `{len(synced)}` commands successfully!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error syncing commands: {e}", ephemeral=True)

bot.run(TOKEN)