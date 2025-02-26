import json
import os
import logging
from threading import Lock

# Configure logging for shared inventory transactions
LOG_FILE = "../Shared_Inventories/inventory_logs.log"
logging.basicConfig(
    filename=LOG_FILE,
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO
)

# File path for shared inventory
INVENTORY_FILE = "player_inventories.json"

# Thread lock to prevent concurrent file writes
inventory_lock = Lock()

# Ensure file exists
if not os.path.exists(INVENTORY_FILE):
    with open(INVENTORY_FILE, "w") as file:
        json.dump({}, file)


def load_inventory():
    """Loads the shared inventory from file."""
    with inventory_lock:
        try:
            with open(INVENTORY_FILE, "r") as file:
                return json.load(file)
        except json.JSONDecodeError:
            logging.error("Error reading inventory file, resetting to empty.")
            return {}


def save_inventory(data):
    """Saves the shared inventory to file."""
    with inventory_lock:
        with open(INVENTORY_FILE, "w") as file:
            json.dump(data, file, indent=4)


def add_item(player_id, item, quantity):
    """Adds an item to a player's inventory."""
    inventory = load_inventory()
    player_id = str(player_id)
    if player_id not in inventory:
        inventory[player_id] = {}
    
    inventory[player_id][item] = inventory[player_id].get(item, 0) + quantity
    save_inventory(inventory)
    logging.info(f"[ADD] {quantity}x {item} to {player_id}'s inventory.")


def remove_item(player_id, item, quantity):
    """Removes an item from a player's inventory."""
    inventory = load_inventory()
    player_id = str(player_id)
    
    if player_id in inventory and item in inventory[player_id]:
        inventory[player_id][item] -= quantity
        if inventory[player_id][item] <= 0:
            del inventory[player_id][item]
        save_inventory(inventory)
        logging.info(f"[REMOVE] {quantity}x {item} from {player_id}'s inventory.")
    else:
        logging.warning(f"[FAILED REMOVE] {item} not found in {player_id}'s inventory.")


def get_inventory(player_id):
    """Retrieves a player's inventory."""
    inventory = load_inventory()
    return inventory.get(str(player_id), {})
