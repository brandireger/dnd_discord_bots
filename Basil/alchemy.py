import discord
from discord import app_commands
from discord.ext import commands
import random
import os
from data_manager import load_json
from inventory_functions import add_item, remove_item, remove_ingredients, get_inventory
from bot_logging import logger

logger.info("✅ Alchemy module initialized")

# ✅ Load required data files
INGREDIENTS = load_json("ingredients.json") or {}
RECIPES = load_json("recipes.json") or {}
ENHANCED_RECIPES = load_json("enhanced_recipes.json") or {}
STATS_FILE = load_json("player_stats.json") or {}

class CraftConfirmationView(discord.ui.View):
    """Confirmation UI for crafting items."""
    def __init__(self, recipe_name, recipe_data, player_id, roll, interaction, cog):
        super().__init__(timeout=30)
        self.recipe_name = recipe_name
        self.recipe_data = recipe_data
        self.player_id = player_id
        self.roll = roll
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

    @staticmethod
    def get_player_stats():
        return load_json("player_stats.json") or {}

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
        embed.add_field(name="How to Craft", value="Use `/craft_item` with the correct ingredients.", inline=False)
        embed.add_field(name="View Recipes", value="Use `/alchemy [recipe]` to view specific recipes.", inline=False)
        embed.add_field(name="Available Recipes", value=", ".join(RECIPES.keys()) if RECIPES else "No recipes found!", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="craftable", description="Check which potions and poisons you can craft based on your ingredients.")
    async def craftable(self, interaction: discord.Interaction):
        """Lists the potions and poisons the player can craft based on their available ingredients."""
        player_id = str(interaction.user.id)
        inventory = get_inventory(player_id)  # ✅ Get shared inventory

        if not inventory:
            await interaction.response.send_message("❌ Your inventory is empty! Gather some ingredients first.")
            return

        craftable_recipes = []
        
        for recipe_name, recipe_data in RECIPES.items():
            base_ingredient = recipe_data.get("base")
            modifiers = recipe_data.get("modifiers", [])

            # ✅ Check if player has base ingredient
            if inventory.get(base_ingredient, 0) > 0:
                missing_modifiers = [mod for mod in modifiers if inventory.get(mod, 0) == 0]

                # ✅ Allow crafting even if some modifiers are missing
                if len(missing_modifiers) < len(modifiers):
                    craftable_recipes.append((recipe_name, missing_modifiers))

        if not craftable_recipes:
            await interaction.response.send_message("🧪 You don’t have enough ingredients to craft any potions or poisons yet.")
            return

        embed = discord.Embed(title="🧪 Craftable Potions & Poisons", color=discord.Color.purple())
        
        for recipe_name, missing_mods in craftable_recipes:
            missing_text = f"\n⚠️ Missing: {', '.join(missing_mods)}" if missing_mods else ""
            embed.add_field(name=f"• **{recipe_name}**", value=f"✅ Craftable!{missing_text}", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="craft_item", description="Attempt to craft a potion or poison with your own d20 roll.")
    async def craft_item(self, interaction: discord.Interaction, recipe: str, roll: int = None, auto: bool = False):
        """Handles crafting attempts where players roll their own d20."""
        player_id = str(interaction.user.id)
        inventory = get_inventory(player_id)

        roll = roll or random.randint(1, 20) 

        recipe_name = recipe.capitalize()
        if recipe_name not in RECIPES:
            await interaction.response.send_message("❌ That recipe does not exist!")
            return

        recipe_data = RECIPES[recipe_name]
        base = recipe_data["base"]
        modifiers = recipe_data.get("modifiers", [])

        # Make sure the roll is valid (between 1 and 20)
        if roll < 1 or roll > 20:
            await interaction.response.send_message("❌ Invalid roll! Please provide a d20 roll between 1 and 20.")
            return

        # Ensure player has ingredients
        if inventory.get(base, 0) < 1 or any(inventory.get(mod, 0) < 1 for mod in modifiers):
            missing = [mod for mod in modifiers if inventory.get(mod, 0) == 0]
            await interaction.response.send_message(f"❌ You lack the required ingredients: {', '.join(missing)}.")
            return

        # Process crafting with player's roll
        if auto:
            # ✅ Skip confirmation and process crafting immediately
            success, message = self.process_crafting(player_id, recipe_name, recipe_data, roll)
            await interaction.response.send_message(message)
        else:
            # ✅ Require confirmation before crafting
            view = CraftConfirmationView(recipe_name, recipe_data, player_id, interaction, self)
            await interaction.response.send_message(
                f"🛠️ **You rolled {roll}.** Do you want to craft **{recipe_name}**? This will use your materials.",
                view=view,
                ephemeral=True
            )

    def process_crafting(self, player_id, recipe_name, recipe_data, d20_roll):
        """Processes the crafting attempt, handles failures and successes."""
        stats = self.get_player_stats().get(player_id, {})
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
        final_roll = d20_roll + total_bonus

        # ✅ Handle crafting outcomes
        if d20_roll == 1:
            # ❌ **Critical Failure** - Ingredients wasted, bad result created
            failed_result = random.choice(["Toxic Sludge", "Explosive Mixture", "Weak Poison"])
            remove_ingredients(player_id, base, modifiers)  # 🚨 Ingredients are **consumed** on critical failure!
            logger.warning(f"Critical Failure! Player {player_id} botched {recipe_name} and created {failed_result} instead.")
            return False, f"💀 **Critical Failure!** You messed up and created **{failed_result}** instead of {recipe_name}!"

        elif final_roll < dc:
            # ❌ **Failure** - Ingredients wasted, but nothing gained
            remove_ingredients(player_id, base, modifiers)  # 🚨 Ingredients are **wasted** on failure!
            logger.info(f"Player {player_id} failed to craft {recipe_name}.")
            return False, f"❌ **Crafting Failed!** The potion failed to form correctly."

        elif d20_roll == 20 and f"Enhanced {recipe_name}" in ENHANCED_RECIPES:
            # 🌟 **Critical Success** - Enhanced potion with extra effect
            enhanced_name = f"Enhanced {recipe_name}"
            remove_ingredients(player_id, base, modifiers)
            add_item(player_id, enhanced_name, 2)
            logger.info(f"🌟 Critical Success! Player {player_id} crafted **{enhanced_name}**.")
            return True, f"🌟 **Critical Success!** You crafted **{enhanced_name}**!"
        
        else:
            remove_ingredients(player_id, base, modifiers)
            add_item(player_id, recipe_name, 1)
            logger.info(f"Player {player_id} successfully crafted {recipe_name}.")
            return True, f"✅ **Crafting Success!** You crafted **{recipe_name}** successfully."

async def setup(bot):
    cog = Alchemy(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")