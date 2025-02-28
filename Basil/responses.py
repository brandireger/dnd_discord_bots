import discord
from discord.ext import commands
from bot_logging import logger
import os
import random
from data_manager import load_json, save_json

RESPONSES = load_json("responses.json") or {}

logger.info("✅ Responses module initialized")

class Responses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def get_response(category, **kwargs):
        """Fetches a random response from the specified category."""
        if not RESPONSES:
            logger.error("⚠️ responses.json failed to load or is empty!")
            return "Error: No response file found."

        if category not in RESPONSES:
            logger.warning(f"⚠️ Response category `{category}` not found.")
            return "🤔 Stanley scratches his head. _'I wasn't prepared for that one!'_"

        return random.choice(RESPONSES[category]).format(**kwargs)

async def setup(bot):
    cog = Responses(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")