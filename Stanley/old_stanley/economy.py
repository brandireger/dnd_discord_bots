import discord
from discord.ext import commands
from data_manager import save_json, load_json, PLAYER_INVENTORY_FILE, GOLD_FILE
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

AUDIT_LOG_CHANNEL_ID = 1341793679416889467

async def audit_log(bot, message):
    """Logs transactions to the console and an audit channel if available."""
    logging.info(message)  # Log to console for debugging
    
    channel = bot.get_channel(AUDIT_LOG_CHANNEL_ID)
    if channel is None:
        logging.warning(f"Audit log channel not found! Message: {message}")
        return  # ✅ Prevents bot from crashing
    
    await channel.send(f"📜 {message}")

class Economy(commands.Cog):
    """Cog for handling player currency transactions."""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def ensure_currency(user_id):
        """Ensures the player has a valid currency balance."""
        gold_data = load_json(GOLD_FILE, {})

        if user_id not in gold_data or not isinstance(gold_data[user_id], dict):
            gold_data[user_id] = {"gp": 10, "sp": 0, "cp": 0}  # Default starting gold
            save_json(GOLD_FILE, gold_data)  # ✅ Only save if new user was added

        for key in ["gp", "sp", "cp"]:
            gold_data[user_id].setdefault(key, 0)  # Ensure all keys exist

        return gold_data[user_id]  # Return updated data for immediate use

    @staticmethod
    def convert_currency(user_id, total_cp):
        """Handles conversion for copper, silver, and gold when making purchases."""
        gold_data = load_json(GOLD_FILE, {})  
        if user_id not in gold_data:
            return False  # ✅ Prevents error if user does not exist
        user_gold = gold_data[user_id]

        # Convert player currency into total copper
        player_cp = (user_gold["gp"] * 100) + (user_gold["sp"] * 10) + user_gold["cp"]

        if player_cp < total_cp:
            return False  # Not enough money

        # Deduct total cost from player's copper
        player_cp -= total_cp

        # Convert back to gp/sp/cp
        user_gold["gp"] = player_cp // 100
        user_gold["sp"] = (player_cp % 100) // 10
        user_gold["cp"] = player_cp % 10

        gold_data[user_id] = user_gold  # ✅ Save updated user balance
        save_json(GOLD_FILE, gold_data)
        return True  # ✅ Return success

    @staticmethod
    def add_gold(user_id, total_cp):
        """Adds gold to a player's balance, handling conversions."""
        gold_data = load_json(GOLD_FILE, {})
        if user_id not in gold_data:
            gold_data[user_id] = {"gp": 10, "sp": 0, "cp": 0}  # Default starting gold

        user_gold = gold_data[user_id]

        # Convert player currency into total copper
        player_cp = (user_gold["gp"] * 100) + (user_gold["sp"] * 10) + user_gold["cp"] + total_cp

        # Convert back to gp/sp/cp
        user_gold["gp"] = player_cp // 100
        user_gold["sp"] = (player_cp % 100) // 10
        user_gold["cp"] = player_cp % 10

        gold_data[user_id] = user_gold  # ✅ Save updated user balance
        save_json(GOLD_FILE, gold_data)

    @discord.app_commands.command(name="balance", description="Check your current gold balance.")
    async def balance(self, interaction: discord.Interaction):
        """Shows the user's current gold balance."""
        user_id = str(interaction.user.id)
        gold_data = load_json(GOLD_FILE, {})

        if user_id not in gold_data:
            gold_data[user_id] = self.ensure_currency(user_id)

        gp, sp, cp = gold_data[user_id]["gp"], gold_data[user_id]["sp"], gold_data[user_id]["cp"]
        await interaction.response.send_message(f"💰 Your balance: `{gp} gp, {sp} sp, {cp} cp`.")
        
    @discord.app_commands.command(name="givegold", description="Give a player some gold.")
    async def givegold(self, interaction: discord.Interaction, member: discord.Member, gp: int = 0, sp: int = 0, cp: int = 0):
        """Allows players to give gold to each other."""
        giver_id = str(interaction.user.id)
        receiver_id = str(member.id)

        # Convert to total copper
        total_cp = (gp * 100) + (sp * 10) + cp

        gold_data = load_json(GOLD_FILE, {})

        gold_data.setdefault(giver_id, {"gp": 10, "sp": 0, "cp": 0})  # ✅ Set default only if missing
        gold_data.setdefault(receiver_id, {"gp": 10, "sp": 0, "cp": 0}) 

        # Check if sender has enough
        if not self.convert_currency(giver_id, total_cp):
            await interaction.response.send_message("❌ You don't have enough gold!", ephemeral=True)
            return

        # Add gold to receiver
        self.add_gold(receiver_id, total_cp)

        # Audit Log Transaction
        log_message = f"💰 **{interaction.user.name} gave {member.name}** `{gp} gp, {sp} sp, {cp} cp`."
        await audit_log(self.bot, log_message)

        await interaction.response.send_message(log_message)

    @discord.app_commands.command(name="takegold", description="Remove gold from a player.")
    @commands.has_permissions(administrator=True)
    async def takegold(self, interaction: discord.Interaction, member: discord.Member, gp: int = 0, sp: int = 0, cp: int = 0):
        """Removes gold from a player."""
        user_id = str(member.id)
        
        # Convert to total copper
        total_cp = (gp * 100) + (sp * 10) + cp

        # Ensure currency exists
        user_gold = self.ensure_currency(user_id)

        # Check if the player has enough and manually deduct it
        player_cp = (user_gold["gp"] * 100) + (user_gold["sp"] * 10) + user_gold["cp"]

        if player_cp < total_cp:
            await interaction.response.send_message("❌ Player does not have enough gold!", ephemeral=True)
            return

        player_cp -= total_cp

        # Convert back to gp/sp/cp
        user_gold["gp"] = player_cp // 100
        user_gold["sp"] = (player_cp % 100) // 10
        user_gold["cp"] = player_cp % 10

        gold_data = load_json(GOLD_FILE, {})
        gold_data[user_id] = user_gold  # ✅ Save updated balance
        save_json(GOLD_FILE, gold_data)

        # Audit Log Transaction
        log_message = f"💰 **{interaction.user.name} took `{gp} gp, {sp} sp, {cp} cp` from {member.name}.**"
        await audit_log(self.bot, log_message)

        await interaction.response.send_message(log_message)

# Setup function to add the Cog to the bot
async def setup(bot):
    print(f"🔍 Debug: Loading {__name__} cog...")  # ✅ Debugging message
    await bot.add_cog(Economy(bot))  # ✅ Ensure this line is running
    print(f"✅ {__name__} cog loaded successfully!")
    
__all__ = ["add_gold", "convert_currency"]