import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import logging
from logging import getLogger
from logging.handlers import RotatingFileHandler
import sys
import os
from data_manager import load_json, save_json
from inventory_functions import add_item, remove_item, get_inventory

# Configure logging
logger = getLogger(__name__)
handler = RotatingFileHandler("logs/basil_bot.log", maxBytes=5000000, backupCount=2)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ✅ Load required data files
INGREDIENTS = load_json("ingredients.json") or {}
RECIPES = load_json("recipes.json") or {}
ENHANCED_RECIPES = load_json("enhanced_recipes.json") or {}
STATS_FILE = os.path.join("shared_inventories", "player_stats.json")

class CraftConfirmationView(discord.ui.View):
    """Confirmation UI for crafting items."""
    def __init__(self, recipe_name, recipe_data, player_id, interaction, cog):
        super().__init__(timeout=30)
        self.recipe_name = recipe_name
        self.recipe_data = recipe_data
        self.player_id = player_id
        self.interaction = interaction
        self.cog = cog

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ This isn't your crafting session!", ephemeral=True)
            return

        success, message = self.cog.process_crafting(self.player_id, self.recipe_name, self.recipe_data)
        await self.interaction.followup.send(message)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.interaction.followup.send("❌ Crafting cancelled.")
        self.stop()

class Alchemy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="alchemy", description="Provides alchemy-related help and lists available recipes.")
    async def alchemy(self, interaction: discord.Interaction, recipe: str = None):
        """Provides alchemy guidance and recipe lookup."""
        if recipe:
            recipe = recipe.capitalize()
            if recipe in RECIPES:
                recipe_data = RECIPES[recipe]
                ingredients = ", ".join(recipe_data.get("modifiers", [])) or "None"
                embed = discord.Embed(title=f"Recipe: {recipe}", color=discord.Color.green())
                embed.add_field(name="Base Ingredient", value=recipe_data["base"], inline=False)
                embed.add_field(name="Modifiers", value=ingredients, inline=False)
                embed.add_field(name="Difficulty (DC)", value=str(recipe_data["DC"]), inline=False)
                embed.add_field(name="Effect", value=recipe_data["effect"], inline=False)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("That recipe does not exist.")
            return

        embed = discord.Embed(title="Alchemy Guide", color=discord.Color.blue())
        embed.add_field(name="How to Craft", value="Use `/craft_potion` or `/craft_poison` with the correct ingredients.", inline=False)
        embed.add_field(name="View Recipes", value="Use `/alchemy [recipe]` to view specific recipes.", inline=False)
        embed.add_field(name="Available Recipes", value=", ".join(RECIPES.keys()) if RECIPES else "No recipes found!", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="craft_item", description="Attempt to craft a potion or poison.")
    async def craft_item(self, interaction: discord.Interaction, recipe: str):
        """Handles crafting attempts with confirmation."""
        player_id = str(interaction.user.id)
        stats = load_json(STATS_FILE).get(player_id, {})
        inventory = get_inventory(player_id)

        recipe_name = recipe.capitalize()
        if recipe_name not in RECIPES:
            await interaction.response.send_message("❌ That recipe does not exist!")
            return

        recipe_data = RECIPES[recipe_name]
        base = recipe_data["base"]
        modifiers = recipe_data.get("modifiers", [])

        # Ensure player has all ingredients **and enough of them**
        if inventory.get(base, 0) < 1 or any(inventory.get(mod, 0) < 1 for mod in modifiers):
            await interaction.response.send_message("❌ You lack the required ingredients.")
            return

        # Ask for confirmation
        view = CraftConfirmationView(recipe_name, recipe_data, player_id, interaction, self)
        await interaction.response.send_message(f"🛠️ Do you want to craft **{recipe_name}**?", view=view, ephemeral=True)

    def process_crafting(self, player_id, recipe_name, recipe_data):
        """Processes the crafting attempt, handles failures and successes."""
        stats = load_json(STATS_FILE).get(player_id, {})
        inventory = get_inventory(player_id)

        base = recipe_data["base"]
        modifiers = recipe_data.get("modifiers", [])
        dc = recipe_data["DC"]

        # ✅ Calculate bonuses
        wis_mod = stats.get("wisdom", 0)
        int_mod = stats.get("intelligence", 0)
        best_mod = max(wis_mod, int_mod)  # Use the best of Wisdom or Intelligence
        proficiency_bonus = stats.get("proficiency", 0) if stats.get("proficient", False) else 0
        tools_bonus = 2 if stats.get("alchemist_tools", False) else 0
        total_bonus = best_mod + proficiency_bonus + tools_bonus

        # ✅ Roll crafting attempt
        d20_roll = random.randint(1, 20)
        final_roll = d20_roll + total_bonus

        # ✅ Ingredient Removal Logic
        def remove_ingredients():
            remove_item(player_id, base, 1)
            for mod in modifiers:
                remove_item(player_id, mod, 1)

        # ✅ Handle crafting outcomes
        if d20_roll == 1:
            # ❌ **Critical Failure** - Ingredients wasted, bad result created
            failed_result = random.choice(["Toxic Sludge", "Explosive Mixture", "Weak Poison"])
            remove_ingredients()  # 🚨 Ingredients are **consumed** on critical failure!
            logger.warning(f"Critical Failure! Player {player_id} botched {recipe_name} and created {failed_result} instead.")
            return False, f"💀 **Critical Failure!** You messed up and created **{failed_result}** instead of {recipe_name}!"

        elif final_roll < dc:
            # ❌ **Failure** - Ingredients wasted, but nothing gained
            remove_ingredients()  # 🚨 Ingredients are **wasted** on failure!
            logger.info(f"Player {player_id} failed to craft {recipe_name}.")
            return False, f"❌ **Crafting Failed!** The potion failed to form correctly."

        elif d20_roll == 20:
            # 🌟 **Critical Success** - Enhanced potion with extra effect
            enhanced_recipe_name = f"Enhanced {recipe_name}"
            
            if enhanced_recipe_name in enhanced_recipes:
                enhanced_recipe = enhanced_recipes[enhanced_recipe_name]
                chosen_enhancement = random.choice(enhanced_recipe["enhancements"])

                # Get player's Alchemy Modifier
                alchemy_modifier = best_mod + proficiency_bonus + tools_bonus

                # Dynamically adjust chosen enhancement
                if "Alchemy Modifier" in chosen_enhancement:
                    chosen_enhancement = chosen_enhancement.replace("Alchemy Modifier", f"{alchemy_modifier}")

                # ✅ Remove ingredients **before** adding new item
                remove_ingredients()

                # Add the enhanced potion to inventory
                add_item(player_id, enhanced_recipe_name, 2)
                logger.info(f"Critical Success! Player {player_id} crafted **{enhanced_recipe_name}** with effect: {chosen_enhancement}")

                return True, f"🌟 **Critical Success!** You crafted **{enhanced_recipe_name}**! 🎉\n\n**Effect:** {chosen_enhancement}"
            
            else:
                # If no enhanced version exists, default to crafting the normal recipe but with a bonus quantity
                remove_ingredients()
                add_item(player_id, recipe_name, 2)
                logger.info(f"Critical Success! Player {player_id} crafted **{recipe_name}** and received an extra dose.")
                
                return True, f"🌟 **Critical Success!** You crafted **{recipe_name}** with extra precision and gained an additional dose!"
        else:
            # ✅ Normal Success
            remove_ingredients()
            add_item(player_id, recipe_name, 1)
            logger.info(f"Player {player_id} successfully crafted {recipe_name}.")
            return True, f"✅ **Crafting Success!** You crafted **{recipe_name}** successfully."

    @app_commands.command(name="craftable", description="Check which potions and poisons you can craft based on your ingredients.")
    async def craftable(self, interaction: discord.Interaction):
        """Lists the potions and poisons the player can craft based on their available ingredients."""
        player_id = str(interaction.user.id)
        inventory = get_inventory(player_id)  # ✅ Get shared inventory

        if not inventory:
            await interaction.response.send_message("❌ Your inventory is empty! Gather some ingredients first.")
            return

        craftable_recipes = [
            recipe_name for recipe_name, recipe_data in RECIPES.items()
            if inventory.get(recipe_data["base"], 0) > 0 and 
               all(inventory.get(mod, 0) > 0 for mod in recipe_data.get("modifiers", []))
        ]

        if not craftable_recipes:
            await interaction.response.send_message("🧪 You don’t have enough ingredients to craft any potions or poisons yet.")
            return

        embed = discord.Embed(title="🧪 Craftable Potions & Poisons", color=discord.Color.purple())
        embed.add_field(name="You can craft:", value="\n".join(f"• **{r}**" for r in craftable_recipes), inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    cog = Alchemy(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")