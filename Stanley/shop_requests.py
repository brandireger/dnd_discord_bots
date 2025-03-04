import discord
from discord import app_commands
from discord.ext import commands
import logging
from data_manager import load_json, save_json, get_response

logger = logging.getLogger(__name__)

class ShopRequests(commands.Cog):
    """Handles item requests and broker interactions."""

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="request", description="Request an approved item from Stanley's catalog.")
    async def request_item(self, interaction: discord.Interaction, item: str):
        """Allows players to request an item, but only from pre-approved requestable items."""
        await interaction.response.defer(thinking=True)

        item = item.lower().strip()
        user_id = str(interaction.user.id)

        # Load requestable items
        requestable_items = load_json("requestable_items.json")
        valid_items = {name.lower(): category for category, items in requestable_items.items() for name in items.keys()}

        if item not in valid_items:
            await interaction.followup.send(
                f"❌ `{item}` is not a requestable item.\n"
                "📜 **Stanley flips through his catalog.**\n"
                "_\"You can only request pre-approved items. Try `/requests_available` to see the list!\"_"
            )
            return

        # Load existing requests
        requests_data = load_json("requests.json")
        requests_data.setdefault(item, [])

        if user_id in requests_data[item]:
            await interaction.followup.send(f"📜 **Stanley sighs.**\n_\"You've already requested `{item}`. Patience, adventurer!\"_")
            return

        requests_data[item].append(user_id)
        save_json("requests.json", requests_data)

        await interaction.followup.send(f"📜 **Stanley records your request.**\n_\"Give me some time, and I’ll see what I can do.\"_\nYour request for `{item}` has been added.")

    @discord.app_commands.command(name="requests_available", description="Lists all requestable items.")
    async def requests_available(self, interaction: discord.Interaction):
        """Lists all items that can be requested from Stanley."""
        await interaction.response.defer(thinking=True)

        requestable_items = load_json("requestable_items.json")

        if not requestable_items:
            await interaction.followup.send("📜 **Stanley shrugs.**\n_\"Nothing is requestable at the moment!\"_")
            return

        request_lines = ["📜 **Items Available for Request:**"]
        for category, items in requestable_items.items():
            if items:  # ✅ Skip empty categories
                item_list = ", ".join(f"`{name}`" for name in items.keys())
                request_lines.append(f"**{category.title()}**: {item_list}")

        # ✅ Ensure message doesn't exceed 2000 characters
        response_chunks = []
        chunk = ""
        for line in request_lines:
            if len(chunk) + len(line) + 1 > 2000:  # +1 for newline character
                response_chunks.append(chunk)
                chunk = ""
            chunk += line + "\n"
        if chunk:
            response_chunks.append(chunk)

        # ✅ Send messages in chunks
        for idx, chunk in enumerate(response_chunks):
            await interaction.followup.send(chunk if idx == 0 else f"🔹 {chunk}")
            
    @discord.app_commands.command(name="all_requests", description="View all pending item requests.")
    async def all_requests(self, interaction: discord.Interaction):
        """Shows all pending item requests."""
        await interaction.response.defer(thinking=True)

        requests_data = load_json("requests.json")

        if not any(requests_data.values()):
            await interaction.followup.send(get_response("requests_none"))
            return

        request_lines = ["📜 **Pending Requests:**"]
        for item, users in requests_data.items():
            if users:
                request_lines.append(f"• **{item.capitalize()}** → {', '.join(f'<@{u}>' for u in users)}")

        await interaction.followup.send("\n".join(request_lines))

    @discord.app_commands.command(name="request_add", description="(Admin) Add a new item to the requestable list.")
    @commands.has_permissions(administrator=True)  # ✅ Admins only
    async def request_add(self, interaction: discord.Interaction, item: str, price_gp: int, rarity: str, category: str):
        """Allows an admin to add an item to the requestable items list."""
        await interaction.response.defer(thinking=True)

        item = item.lower().strip()
        category = category.lower().strip()

        requestable_items = load_json("requestable_items.json")
        requestable_items.setdefault(category, {})

        if item in requestable_items[category]:
            await interaction.followup.send(f"⚠️ `{item}` is already in the requestable items list.")
            return

        requestable_items[category][item] = {"price_gp": price_gp, "rarity": rarity}
        save_json("requestable_items.json", requestable_items)

        await interaction.followup.send(f"✅ **{item.capitalize()}** has been added to the **requestable items list** under `{category}`!")

    @discord.app_commands.command(name="request_approve", description="(Admin) Approve a requested item and add it to the shop.")
    @commands.has_permissions(administrator=True)  # ✅ Admins only
    async def request_approve(self, interaction: discord.Interaction, item: str, stock: int = 1):
        """Allows an admin to approve a request and move it into the shop."""
        await interaction.response.defer(thinking=True)

        item = item.lower().strip()

        requests_data = load_json("requests.json")
        shop_data = load_json("stanley_shop.json")
        requestable_items = load_json("requestable_items.json")

        if item not in requests_data or not requests_data[item]:
            await interaction.followup.send(f"❌ `{item}` is not in the request list!")
            return
        if stock <= 0:
            await interaction.followup.send(f"❌ Cannot approve `{item}` with zero stock!")
            return

        found_category = next((cat for cat, items in requestable_items.items() if item in items), None)
        if not found_category:
            await interaction.followup.send(f"❌ `{item}` is not a valid requestable item.")
            return

        shop_data.setdefault(found_category, {})[item] = {
            "price_cp": requestable_items[found_category][item]["price_gp"] * 100,
            "stock": stock,
            "rarity": requestable_items[found_category][item]["rarity"]
        }

        del requests_data[item]  # ✅ Remove the request
        save_json("stanley_shop.json", shop_data)
        save_json("requests.json", requests_data)

        await interaction.followup.send(f"✅ **{item.capitalize()}** has been approved and added to Stanley's shop with `{stock}` in stock!")

async def setup(bot):
    """Loads the ShopRequests cog into the bot."""
    cog = ShopRequests(bot)
    await bot.add_cog(cog)  
    print(f"✅ {cog} cog loaded!")