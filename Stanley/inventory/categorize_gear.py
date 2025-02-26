import json
import re

# Load the JSON file
input_file = "advGear2.json"  # Original JSON file
output_file = "refined_advGear.json"  # Cleaned and categorized output

# Function to clean item names
def clean_item_name(name):
    """Removes special formatting like {@item Acid|XPHB} -> Acid"""
    return re.sub(r"{@item\s([^|}]+).*?}", r"\1", name).strip().capitalize()

# Function to convert prices to copper
def convert_price_to_cp(price):
    """Converts price strings into copper (cp) values"""
    price = price.replace(",", "").strip().lower()
    if "sp" in price:
        return int(float(price.replace(" sp", "")) * 10)
    elif "cp" in price:
        return int(float(price.replace(" cp", "")))
    elif "gp" in price:
        return int(float(price.replace(" gp", "")) * 100)
    return None  # Invalid price formats will be ignored

# Function to categorize items
def categorize_item(name):
    """Assigns an item to a category based on keywords."""
    name = name.lower()
    if "ammunition" in name or "net" in name or "caltrops" in name:
        return "hazards_traps"
    elif "armor" in name or "manacles" in name:
        return "armor_restraints"
    elif any(word in name for word in ["torch", "rations", "tent", "rope", "shovel", "waterskin"]):
        return "adventuring_essentials"
    elif any(word in name for word in ["crowbar", "climber", "grappling", "block and tackle"]):
        return "utility_tools_climbing"
    elif any(word in name for word in ["lock", "thieves", "manacles"]):
        return "lockpicking_security"
    elif any(word in name for word in ["pouch", "chest", "barrel", "bottle", "sack"]):
        return "containers_storage"
    elif any(word in name for word in ["kit", "pack", "dungeoneer"]):
        return "adventurers_kits_packs"
    elif any(word in name for word in ["scroll", "potion", "holy", "arcane", "ink", "quill"]):
        return "magical_items_alchemy"
    else:
        return "miscellaneous_equipment"


# Load the original JSON file
try:
    with open(input_file, "r") as f:
        data = json.load(f)

    # Process each item
    cleaned_data = []
    for row in data["rows"]:
        item_name = clean_item_name(row[0])  # Clean item name
        price_cp = convert_price_to_cp(row[2])  # Convert price to cp
        if price_cp is None:
            continue  # Skip items with invalid prices
        category = categorize_item(item_name)  # Assign category

        # Create structured data
        cleaned_data.append({
            "Name": item_name,
            "Value_cp": price_cp,
            "Category": category
        })

    # Save the cleaned and categorized data
    with open(output_file, "w") as f:
        json.dump(cleaned_data, f, indent=4)

    print(f"✅ Cleaned and categorized items saved to {output_file}")

except FileNotFoundError:
    print(f"❌ Error: File {input_file} not found. Ensure it's in the correct folder.")
except json.JSONDecodeError:
    print(f"❌ Error: Could not parse {input_file}. Check for formatting issues.")