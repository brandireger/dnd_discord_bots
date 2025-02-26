import discord
from discord.ext import commands
from data_manager import load_json, save_json, get_response, GOLD_FILE

class Economy(commands.Cog):
    """Handles player currency transactions."""

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="balance", description="Check your current gold balance.")
    async def balance(self, interaction: discord.Interaction):
        """Shows the user's current gold balance."""
        try:
            await interaction.response.defer(thinking=True)  # ✅ Prevents timeout issues)

            user_id = str(interaction.user.id)
            gold_data = load_json(GOLD_FILE, {})
            print(f"🔍 Debug: Loaded gold data: {gold_data}")

            if user_id not in gold_data:
                print(f"🛠️ Debug: {interaction.user.name} not found in gold data. Creating new entry.")
                gold_data[user_id] = {"gp": 10, "sp": 0, "cp": 0}
                save_json(GOLD_FILE, gold_data)

            gp, sp, cp = gold_data[user_id]["gp"], gold_data[user_id]["sp"], gold_data[user_id]["cp"]
            print(f"🛠️ Debug: {interaction.user.name} has {gp} gp, {sp} sp, {cp} cp")

            # ✅ Ensure Stanley sends a response
            await interaction.followup.send(f"💰 Your balance: `{gp} gp, {sp} sp, {cp} cp`.")
            print("✅ Debug: Sent followup message successfully.")

        except Exception as e:
            print(f"❌ Debug: `/balance` failed with error: {e}")
            await interaction.followup.send(f"❌ Error retrieving balance: {e}")

    @discord.app_commands.command(name="givegold", description="Give gold to another player.")
    async def givegold(self, interaction: discord.Interaction, member: discord.Member, gp: int = 0, sp: int = 0, cp: int = 0):
        """Allows players to give gold to each other."""
        await interaction.response.defer(thinking=True)

        giver_id = str(interaction.user.id)
        receiver_id = str(member.id)
        gold_data = load_json(GOLD_FILE, {})

        # Ensure both users have an account
        for user_id in [giver_id, receiver_id]:
            if user_id not in gold_data:
                gold_data[user_id] = {"gp": 10, "sp": 0, "cp": 0}

        # Convert to total copper
        total_cp = (gp * 100) + (sp * 10) + cp
        giver_cp = (gold_data[giver_id]["gp"] * 100) + (gold_data[giver_id]["sp"] * 10) + gold_data[giver_id]["cp"]

        if giver_cp < total_cp:
            await interaction.followup.send("❌ You don't have enough gold!")
            return

        # Deduct from giver
        giver_cp -= total_cp
        gold_data[giver_id] = {"gp": giver_cp // 100, "sp": (giver_cp % 100) // 10, "cp": giver_cp % 10}

        # Add to receiver
        receiver_cp = (gold_data[receiver_id]["gp"] * 100) + (gold_data[receiver_id]["sp"] * 10) + gold_data[receiver_id]["cp"]
        receiver_cp += total_cp
        gold_data[receiver_id] = {"gp": receiver_cp // 100, "sp": (receiver_cp % 100) // 10, "cp": receiver_cp % 10}

        save_json(GOLD_FILE, gold_data)
        await interaction.followup.send(get_response("givegold_success", user=interaction.user.name, receiver=receiver.display_name, amount=total_cp // 100))

    @discord.app_commands.command(name="takegold", description="Remove gold from a player.")
    @commands.has_permissions(administrator=True)
    async def takegold(self, interaction: discord.Interaction, member: discord.Member, gp: int = 0, sp: int = 0, cp: int = 0):
        """Removes gold from a player."""
        await interaction.response.defer(thinking=True)

        user_id = str(member.id)
        gold_data = load_json(GOLD_FILE, {})

        if user_id not in gold_data:
            await interaction.followup.send("❌ Player does not have an account.")
            return

        # Convert to total copper
        total_cp = (gp * 100) + (sp * 10) + cp
        player_cp = (gold_data[user_id]["gp"] * 100) + (gold_data[user_id]["sp"] * 10) + gold_data[user_id]["cp"]

        if player_cp < total_cp:
            await interaction.followup.send("❌ Player does not have enough gold!")
            return

        # Deduct gold
        player_cp -= total_cp
        gold_data[user_id] = {"gp": player_cp // 100, "sp": (player_cp % 100) // 10, "cp": player_cp % 10}

        save_json(GOLD_FILE, gold_data)
        await interaction.followup.send(get_response("takegold_success", user=interaction.user.name, target=member.display_name, amount=total_cp // 100))

    @discord.app_commands.command(name="admin_givegold", description="Admin-only: Give gold to a player without deducting it.")
    @commands.has_permissions(administrator=True)
    async def admin_givegold(self, interaction: discord.Interaction, member: discord.Member, gp: int = 0, sp: int = 0, cp: int = 0):
        """Admins can reward gold to players (for quests, events, etc.) without taking it from themselves."""
        await interaction.response.defer(thinking=True)

        receiver_id = str(member.id)
        gold_data = load_json(GOLD_FILE, {})

        print(f"🔍 Debug: {interaction.user.name} is giving (admin reward) {gp} gp, {sp} sp, {cp} cp to {member.name}.")

        # Ensure the receiver has an account
        if receiver_id not in gold_data:
            gold_data[receiver_id] = {"gp": 10, "sp": 0, "cp": 0}  # Default starting balance

        # Convert to total copper and add to the receiver
        total_cp = (gp * 100) + (sp * 10) + cp
        receiver_cp = (gold_data[receiver_id]["gp"] * 100) + (gold_data[receiver_id]["sp"] * 10) + gold_data[receiver_id]["cp"]
        receiver_cp += total_cp

        # Convert back to gp/sp/cp format
        gold_data[receiver_id] = {"gp": receiver_cp // 100, "sp": (receiver_cp % 100) // 10, "cp": receiver_cp % 10}

        # Save updated balance
        save_json(GOLD_FILE, gold_data)

        await interaction.followup.send(f"✨ {interaction.user.mention} **rewarded** {member.mention} `{gp} gp, {sp} sp, {cp} cp`!")

    @discord.app_commands.command(name="stanley_help", description="Displays Stanley's available commands.")
    async def stanley_help(interaction: discord.Interaction):
        """Provides a list of all available commands and their descriptions."""
        await interaction.response.defer(thinking=True)

        # Define all commands with their descriptions
        command_list = [
            "**💰 Economy Commands:**",
            "• `/balance` → Check your current gold balance.",
            "• `/givegold @player gp sp cp` → Give gold to another player.",
            "• `/takegold @player gp sp cp` → (Admin) Remove gold from a player.",
            "• `/admin_givegold @player gp sp cp` → (Admin) Reward gold to a player.",
            "",
            "**🛒 Shop Commands:**",
            "• `/shop` → Browse Stanley's shop categories.",
            "• `/buy item_name` → Buy an item from the shop.",
            "• `/sell item_name` → Sell an item back to Stanley.",
            "• `/inventory` → View your inventory.",
            "",
            "**📜 Request & Broker Commands:**",
            "• `/request item_name` → Request an approved item from Stanley.",
            "• `/requests_available` → See what items can be requested.",
            "• `/all_requests` → View all pending item requests.",
            "• `/request_add item price rarity category` → (Admin) Add a new item to the request list.",
            "• `/request_approve item stock` → (Admin) Approve a request and add it to the shop.",
            "",
            "**🔧 Admin & Debug Commands:**",
            "• `/sync` → Manually sync slash commands.",
            "• `/audit_log` → (Admin) View recent shop transactions.",
            "• `/help` → Show this help message.",
        ]

        # Format and send the message
        help_message = "\n".join(command_list)
        await interaction.followup.send(f"📜 **Stanley's Ledger of Commands:**\n{help_message}")

async def setup(bot):
    print("🔍 Debug: Loading Economy cog...")
    cog = Economy(bot)
    await bot.add_cog(cog)
    print("✅ Economy cog loaded!")

    # ✅ Manually register commands
    if not bot.tree.get_command("balance"):
        bot.tree.add_command(cog.balance)
        print("🔄 Manually adding `/balance`...")
    if not bot.tree.get_command("givegold"):
        bot.tree.add_command(cog.givegold)
        print("🔄 Manually adding `/givegold`...")
    if not bot.tree.get_command("takegold"):
        bot.tree.add_command(cog.takegold)
        print("🔄 Manually adding `/takegold`...")
    if not bot.tree.get_command("admin_givegold"):
        bot.tree.add_command(cog.admin_givegold)
        print("🔄 Manually adding `/admin_givegold`...")
    if not bot.tree.get_command("stanley_help"):
        bot.tree.add_command(cog.stanley_help)
        print("🔄 Manually adding `/stanley_help`...")

    print("🔄 Syncing economy commands...")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands successfully!")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")