import discord
from discord.ext import commands
import json
import random

# Load responses from JSON
with open("inventory/responses.json", "r") as file:
    RESPONSES = json.load(file)

class Responses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_response(self, category, **kwargs):
        """Fetches a random response from the specified category."""
        if category not in RESPONSES:
            return "Error: No response found."
        return random.choice(RESPONSES[category]).format(**kwargs)

async def setup(bot):
    cog = Responses(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")