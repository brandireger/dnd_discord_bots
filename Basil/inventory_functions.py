import json
import logging
from logging import getLogger
from logging.handlers import RotatingFileHandler
import sys
import os
from data_manager import load_json, save_json

# Configure logging
logger = getLogger(__name__)

INVENTORY_FILE = "player_inventories.json"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get Basil's main directory
BASE_FOLDER = os.path.join(BASE_DIR, "inventory")
DEFAULTS_FOLDER = os.path.join(BASE_DIR, "default_game_files")
SHARED_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "..", "shared_inventories"))

# Get all players with an inventory
def get_all_players():
    """Returns a list of all player IDs who have an inventory."""
    inventory_data = load_json(INVENTORY_FILE, folder=SHARED_FOLDER) or {}
    return list(inventory_data.keys()) if inventory_data else []

def get_inventory(player_id):
    """Returns the inventory for a given player."""
    inventory_data = load_json(INVENTORY_FILE, folder=SHARED_FOLDER) or {}
    return inventory_data.get(player_id, {})

def save_inventory(inventory_data):
    """Saves the inventory data to file."""
    save_json(INVENTORY_FILE, inventory_data, folder=SHARED_FOLDER)

def add_item(player_id, item, quantity):
    """Adds an item to a player's inventory."""
    inventory_data = load_json(INVENTORY_FILE, folder=SHARED_FOLDER) or {}
    inventory_data.setdefault(player_id, {})
    inventory_data[player_id][item] = inventory_data[player_id].get(item, 0) + quantity
    save_inventory(inventory_data)
    logger.info(f"Added {quantity}x {item} to {player_id}'s inventory.")

def remove_item(player_id, item, quantity):
    """Removes an item from a player's inventory."""
    inventory_data = load_json(INVENTORY_FILE, folder=SHARED_FOLDER) or {}

    if player_id in inventory_data and item in inventory_data[player_id]:
        inventory_data[player_id][item] = max(0, inventory_data[player_id][item] - quantity)
        
    if inventory_data[player_id][item] == 0:
        del inventory_data[player_id][item]

    save_inventory(inventory_data)
    logger.info(f"Removed {quantity}x {item} from {player_id}'s inventory.")