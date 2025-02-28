import discord
from discord import app_commands
from discord.ext import commands
import os
from data_manager import load_json, save_json
from bot_logging import logger

logger.info("✅ PlayerStats module initialized")

class PlayerStats(commands.Cog):
    """Handles player stat tracking for Basil's crafting system."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_basil_stats", description="Set your intelligence, wisdom, proficiency bonus, and tool proficiencies.")
    async def set_basil_stats(
        self,
        interaction: discord.Interaction,
        intelligence: int,
        wisdom: int,
        proficiency: int,
        proficient: bool,
        herbalism_kit: bool,
        alchemist_tools: bool
    ):
        """Players set their intelligence & wisdom modifiers, proficiency bonus, and tool proficiencies."""
        user_id = str(interaction.user.id)
        stats = load_json("player_stats.json")

        # ✅ Update player's stats
        stats[user_id] = {
            "intelligence_mod": intelligence,
            "wisdom_mod": wisdom,
            "proficiency_bonus": proficiency,
            "proficient": proficient,  # Covers both Herbalism & Alchemy
            "herbalism_kit": herbalism_kit,
            "alchemist_tools": alchemist_tools
        }

        # ✅ Save to file
        save_json("player_stats.json", stats)

        # ✅ Confirm update
        await interaction.response.send_message(
            f"✅ **Stats updated!**\n"
            f"📜 **Intelligence Modifier:** `{intelligence}`\n"
            f"🧠 **Wisdom Modifier:** `{wisdom}`\n"
            f"🎖️ **Proficiency Bonus:** `{proficiency}`\n"
            f"🔬 **Proficient in Herbalism & Alchemy:** `{proficient}`\n"
            f"🌿 **Herbalism Kit Proficiency:** `{herbalism_kit}`\n"
            f"⚗️ **Alchemist Tools Proficiency:** `{alchemist_tools}`"
        )

async def setup(bot):
    cog = PlayerStats(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")