import discord
from discord import app_commands
from discord.ext import commands
import random
import time
import sys
import os
import json
import logging
from logging import getLogger
from logging.handlers import RotatingFileHandler
from data_manager import load_json, save_json
from bot_logging import logger

logger.info("✅ BasilCraft module initialized")

# File Paths
BASIL_INVENTORY_FILE = "market.json"
RECIPES_FILE = "recipes.json"
CRAFTED_ITEMS_FILE = "crafted_items.json"
ENHANCED_RECIPES_FILE = "enhanced_recipes.json"

# Load Recipes
RECIPES = load_json(RECIPES_FILE) or {}

class BasilCrafting(commands.Cog):
    """Handles Basil's automatic crafting system."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="basil_crafting", description="Simulate Basil crafting potions for a set number of in-game days.")
    @app_commands.default_permissions(administrator=True)
    async def basil_crafting(self, interaction: discord.Interaction, days: int):
        """Runs Basil's crafting cycle based on in-game time."""
        if days <= 0:
            await interaction.response.send_message("❌ Days must be at least 1.")
            return

        # Load Basil's ingredient inventory
        basil_inventory = load_json(BASIL_INVENTORY_FILE) or {}
        crafted_items = load_json(CRAFTED_ITEMS_FILE) or {}
        recipes = load_json(RECIPES_FILE) or {}
        enhanced_recipes = load_json(ENHANCED_RECIPES_FILE) or {}

        basil_inventory = {item: data["stock"] for item, data in basil_inventory.items() if isinstance(data, dict) and "stock" in data}

        # Determine the number of potions Basil can attempt
        craft_attempts = max(1, int(days * random.uniform(0.8, 1.2)))  # Adds slight randomness
        crafted_items_log = []
        failures = []

        for _ in range(craft_attempts):
            recipe = random.choice(list(RECIPES.keys()))
            recipe_data = RECIPES[recipe]

            # Check if Basil has the required ingredients
            base = recipe_data["base"]
            modifiers = recipe_data.get("modifiers", [])
            has_ingredients = (
                basil_inventory.get(base, 0) > 0 and
                all(basil_inventory.get(mod, 0) > 0 for mod in modifiers)
            )

            if not has_ingredients and random.random() >= 0.4:  # 30% chance Basil improvises
                logger.info(f"Basil improvises ingredients for {recipe}.")
                continue  # Skip crafting this potion

            # Simulate crafting success/failure
            dc = recipe_data["DC"]
            d20_roll = random.randint(1, 20)  # Store raw d20 roll
            total_roll = d20_roll + 8  # Basil gets a +5 crafting bonus

            def remove_ingredients():
                if base in basil_inventory:
                    basil_inventory[base] = max(0, basil_inventory[base] - 1)
                for mod in modifiers:
                    if mod in basil_inventory:
                        basil_inventory[mod] = max(0, basil_inventory[mod] - 1)
            
            if d20_roll == 1:
                # ❌ **Critical Failure:** Basil messes up horribly
                failed_result = random.choice(["Toxic Sludge", "Explosive Mixture", "Weak Poison"])
                remove_ingredients()
                failures.append(failed_result)
                logger.warning(f"Basil **critically failed** crafting {recipe}. Created {failed_result} instead!")
                continue  
            elif total_roll < dc:
                # ❌ Failure: Wastes ingredients
                remove_ingredients()
                logger.info(f"Basil failed to craft {recipe}.")
                continue  
            elif d20_roll == 20 and f"Enhanced {recipe}" in enhanced_recipes:
            # 🌟 **Critical Success: Enhanced Potion**
                enhanced_recipe_name = f"Enhanced {recipe}"
                enhanced_recipe = enhanced_recipes[enhanced_recipe_name]
                chosen_enhancement = random.choice(enhanced_recipe["enhancements"])

                # Format enhancement correctly
                chosen_enhancement = chosen_enhancement.replace("Alchemy Modifier", str(5))

                remove_ingredients()

                # Store enhanced potion with effect
                crafted_items.setdefault(enhanced_recipe_name, [])
                crafted_items[enhanced_recipe_name].append({
                    "effect": chosen_enhancement,
                    "quantity": 1
                })

                crafted_items_log.append((enhanced_recipe_name, 1, chosen_enhancement))
                logger.info(f"Basil **critically succeeded**! Crafted **{enhanced_recipe_name}** with effect: {chosen_enhancement}")

            else:
                remove_ingredients()
                crafted_items[recipe] = crafted_items.get(recipe, 0) + 1
                crafted_items_log.append((recipe, 1))
                logger.info(f"Basil successfully crafted {recipe}.")

        # Save updated inventories
        save_json(BASIL_INVENTORY_FILE, basil_inventory)
        save_json(CRAFTED_ITEMS_FILE, crafted_items)

        # ✅ Generate crafting summary
        result_text = f"🔬 **Basil crafted for {days} in-game days.**\n\n"

        if crafted_items_log:
            result_text += "**🧪 Basil has crafted:**\n"
            for item, qty, *effect in crafted_items_log:
                effect_text = f" ({effect[0]})" if effect else ""
                result_text += f"• **{item}** x{qty}{effect_text}\n"

        if failures:
            result_text += "**⚠️ Basil had some critical failures:**\n" + "\n".join(
                [f"• **{item}** (Toxic Failure!)" for item in failures]) + "\n"

        if not crafted_items_log and not failures:
            result_text += "🔬 Basil worked hard but didn't successfully finish any potions this time."
        
        logger.info(f"✅ Basil's crafting session completed for {days} in-game days.")
        await interaction.response.send_message(result_text)

async def setup(bot):
    cog = BasilCrafting(bot)
    await bot.add_cog(cog)
    print(f"✅ {cog} cog loaded!")