import discord
from discord import Intents, Client, Message
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

from responses import get_response

from data_manager import gold_data, inventory_data, ensure_currency, save_json, SHOP_ITEMS, config
from economy import balance, givegold, takegold
bot.add_command(balance)
bot.add_command(givegold)
bot.add_command(takegold)

AUDIT_CHANNEL_ID = 1341793679416889467

def load_shop_items():
    """Loads shop items from the CSV file into a dictionary with structured prices."""
    try:
        df = pd.read_csv(CSV_FILE)
        shop = {}

        for _, row in df.iterrows():
            item_name = row["Name"].strip().lower()
            price = str(row["Value"]).replace(",", "").strip().lower()

            # Convert price to gp/sp/cp
            if "sp" in price:
                item_price_cp = int(float(price.replace(" sp", "")) * 10)
            elif "cp" in price:
                item_price_cp = int(float(price.replace(" cp", "")))
            elif "gp" in price:
                item_price_cp = int(float(price.replace(" gp", "")) * 100)
            else:
                continue  # Skip invalid price formats

            # Store item price in copper for easier conversion later
            shop[item_name] = item_price_cp

        return shop

    except Exception as e:
        print(f"Error loading shop data: {e}")
        return {}

def load_gold():
    try:
        with open(GOLD_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}  # Empty dictionary if file doesn't exist

def save_gold(gold_data):
    with open(GOLD_FILE, "w") as f:
        json.dump(gold_data, f, indent=4)

INVENTORY_FILE = "inventory_data.json"

def load_inventory():
    try:
        with open(INVENTORY_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}  # Empty inventory if file doesn't exist

def save_inventory(inventory_data):
    with open(INVENTORY_FILE, "w") as f:
        json.dump(inventory_data, f, indent=4)

inventory_data = load_inventory()

# load token
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix= "/", intents=intents)

@bot.command(name="shop")
async def shop(ctx):
    """Lists available shop items with their prices dynamically loaded from CSV."""
    if not SHOP_ITEMS:
        await ctx.send("🛒 The shop is currently empty. Stanley CoinMancer must have misplaced his inventory!")
        return

    item_list = []
    for item, price_cp in SHOP_ITEMS.items():
        gp, sp, cp = price_cp // 100, (price_cp % 100) // 10, price_cp % 10
        price_str = f"{gp} gp, {sp} sp, {cp} cp".replace(" 0 gp,", "").replace(" 0 sp,", "").replace(" 0 cp", "")
        item_list.append(f"• {item.capitalize()} - {price_str}")

    shop_message = "\n".join(item_list)
    await ctx.send(f"🛒 **Welcome to Stanley CoinMancer’s Shop!**\n{shop_message}")

# Command: Buy an item from the shop
@bot.command(name="buy")
async def buy(ctx, item: str):
    """Allows a player to buy an item if they have enough money."""
    item = item.lower()
    user_id = str(ctx.author.id)

    if item not in SHOP_ITEMS:
        await ctx.send(f"❌ {ctx.author.name}, '{item}' is not available in the shop.")
        return

    item_price_cp = SHOP_ITEMS[item]  # Get price in copper

    if not convert_currency(user_id, item_price_cp):
        await ctx.send(f"💸 {ctx.author.name}, you lack the coin for that! Come back when your pockets are heavier.")
        return

    # Add item to inventory
    if user_id not in inventory_data:
        inventory_data[user_id] = []
    
    inventory_data[user_id].append(item)
    save_inventory(inventory_data)
    save_gold(gold_data)

    gp, sp, cp = gold_data[user_id]["gp"], gold_data[user_id]["sp"], gold_data[user_id]["cp"]
    await ctx.send(f"✅ {ctx.author.name} has purchased {item.capitalize()}! Your new balance: {gp} gp, {sp} sp, {cp} cp.")
    await log_transaction(ctx, f"🛒 **{ctx.author.name} bought** {item.capitalize()} **for** {item_price_cp // 100} gp.** New balance: {gp} gp, {sp} sp, {cp} cp.")

@bot.command(name="sell")
async def sell(ctx, item: str):
    """Allows a player to sell an item for half its value."""
    item = item.lower()
    user_id = str(ctx.author.id)

    if user_id not in inventory_data or item not in inventory_data[user_id]:
        await ctx.send(f"❌ {ctx.author.name}, you don't own a '{item}' to sell.")
        return

    if item not in SHOP_ITEMS:
        await ctx.send(f"❌ {ctx.author.name}, '{item}' is not a recognized shop item.")
        return

    item_price_cp = SHOP_ITEMS[item]  # Get original price in copper
    sell_price_cp = item_price_cp // 2  # Selling is half price

    # Remove item from inventory
    inventory_data[user_id].remove(item)
    save_inventory(inventory_data)

    # Add earnings properly
    add_gold(user_id, sell_price_cp)
    save_gold(gold_data)

    gp, sp, cp = gold_data[user_id]["gp"], gold_data[user_id]["sp"], gold_data[user_id]["cp"]
    await ctx.send(f"💰 {ctx.author.name} sold {item.capitalize()} for {sell_price_cp // 100} gp. New balance: {gp} gp, {sp} sp, {cp} cp.")
    await log_transaction(ctx, f"💰 **{ctx.author.name} sold** {item.capitalize()} **for** {sell_price_cp // 100} gp.** New balance: {gp} gp, {sp} sp, {cp} cp.")

@bot.command(name="inventory")
async def inventory(ctx):
    user_id = str(ctx.author.id)

    if user_id not in inventory_data or not inventory_data[user_id]:
        await ctx.send(f"🎒 {ctx.author.name}, you own absolutely nothing. Not even a rusty dagger. How tragic.")
        return

    items = "\n".join([f"• {item.capitalize()}" for item in inventory_data[user_id]])
    await ctx.send(f"🎒 **{ctx.author.name}'s Inventory:**\n{items}")

@bot.command(name="resetall")
@commands.has_permissions(administrator=True)  # Only admins can reset
async def resetall(ctx):
    """Resets all player inventories and balances to default values after confirmation."""
    
    confirmation_message = await ctx.send(
        "⚠️ **WARNING:** This will **erase all inventories and reset all player balances**. "
        "Type `CONFIRM RESET` (case insensitive) to proceed or `CANCEL` to abort."
    )

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=30)  # Wait for response
    except asyncio.TimeoutError:
        await ctx.send("⏳ Reset timed out. No changes made.")
        return

    if msg.content.strip().lower() == "confirm reset":
        global gold_data, inventory_data

        gold_data = {}  # Reset all gold
        inventory_data = {}  # Reset all inventories

        save_gold(gold_data)
        save_inventory(inventory_data)

        await ctx.send("✅ **All player inventories and balances have been reset.**")
        await log_transaction(ctx, "🚨 **ADMIN RESET:** All inventories and balances were wiped.")
    else:
        await ctx.send("❌ Reset canceled. No changes made.")

async def log_transaction(ctx, message: str):
    """Send a transaction log to the audit channel and debug issues."""
    audit_channel = bot.get_channel(AUDIT_CHANNEL_ID)
    
    if audit_channel:
        await audit_channel.send(message)
    else:
        print(f"❌ ERROR: Audit channel with ID {AUDIT_CHANNEL_ID} not found. Is the bot in the right server?")
        await ctx.send("❌ Audit log error: Could not find the audit channel. Please check the bot's permissions.")

async def send_message(message: Message, user_message: str) -> None:
    if not user_message:
        print("Message was empty cuz of intents probly")
        return

    if is_private := user_message[0] == '?':
        user_message = user_message[1:]

    try:
        response: str = get_response(user_message)
        await message.author.send(response) if is_private else await message.channel.send(response)
    except Exception as e:
        print(e)

@bot.event
async def on_ready():
    print(f'{bot.user} is now running!')


@bot.event
async def on_message(message: Message):
    if message.author == bot.user:
        return

    # Ignore commands
    if message.content.startswith("/"):
        await bot.process_commands(message)
        return  
    
    print(f'[{message.channel}] {message.author}: "{message.content}"')

    await bot.process_commands(message)

    await send_message(message, message.content)

# Run the bot
def main():
    bot.run(TOKEN)

if __name__ == '__main__':
    main()