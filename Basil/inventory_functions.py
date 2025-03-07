import json
import sys
import os
from data_manager import load_json, save_json
from bot_logging import logger

INVENTORY_FILE = "player_inventories.json"

# Get all players with an inventory
def get_all_players():
    """Returns a list of all player IDs who have an inventory."""
    inventory_data = load_json(INVENTORY_FILE) or {}
    return list(inventory_data.keys()) if inventory_data else []

def get_inventory(player_id):
    """Returns the inventory for a given player."""
    inventory_data = load_json(INVENTORY_FILE) or {}
    if player_id not in inventory_data:
        inventory_data[player_id] = {}
        save_inventory(inventory_data)
    return inventory_data.setdefault(player_id, {})

def save_inventory(inventory_data):
    """Saves the inventory data to file."""
    if not inventory_data:
        logger.error("⚠️ Attempted to save empty inventory data! Save operation aborted.")
        return
    save_json(INVENTORY_FILE, inventory_data)

def add_item(player_id, item, quantity):
    """Adds an item to a player's inventory."""
    if quantity <= 0:
        logger.warning(f"⚠️ Attempted to add {quantity} of {item} to {player_id}, but quantity must be positive.")
        return
    
    inventory_data = load_json(INVENTORY_FILE) or {}
    inventory_data.setdefault(player_id, {})
    inventory_data[player_id][item] = inventory_data[player_id].get(item, 0) + quantity
    save_inventory(inventory_data)
    logger.info(f"Added {quantity}x {item} to {player_id}'s inventory.")

def remove_ingredients(player_id, base, modifiers):
    """Removes the required ingredients from the player's inventory."""
    inventory = get_inventory(player_id)
    
    if inventory.get(base, 0) < 1:
        logger.warning(f"⚠️ {player_id} lacks {base}. Cannot proceed with crafting.")
        return

    missing_mods = [mod for mod in modifiers if inventory.get(mod, 0) < 1]
    if missing_mods:
        logger.warning(f"⚠️ {player_id} lacks required modifiers: {', '.join(missing_mods)}")
        return

    remove_item(player_id, base, 1)
    for mod in modifiers:
        remove_item(player_id, mod, 1)

def remove_item(player_id, item, quantity):
    """Removes an item from a player's inventory safely."""
    inventory_data = load_json(INVENTORY_FILE) or {}

    if player_id not in inventory_data:
        logger.warning(f"Attempted to remove {item} from {player_id}, but they have no inventory.")
        return

    if item in inventory_data[player_id]:
        if inventory_data[player_id][item] < quantity:
            logger.warning(f"⚠️ {player_id} tried to remove {quantity}x {item}, but only has {inventory_data[player_id][item]}. Removing only available amount.")
            quantity = inventory_data[player_id][item]

        inventory_data[player_id][item] -= quantity

        if inventory_data[player_id][item] == 0:
            del inventory_data[player_id][item]

    save_inventory(inventory_data)
    logger.info(f"Removed {quantity}x {item} from {player_id}'s inventory.")