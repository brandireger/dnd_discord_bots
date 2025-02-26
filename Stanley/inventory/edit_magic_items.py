import json
import csv

# Define input and output file paths
input_file = "magic_items.txt"  # Replace with your actual text file
output_file = "requestable_items.json"

# Define category mapping (optional, can be adjusted)
CATEGORY_MAPPING = {
    "consumables": ["potion", "scroll", "philter", "dust", "oil"],
    "non_combat": ["helm", "gloves", "boots", "ring", "cloak", "amulet"],
    "combat": ["weapon", "sword", "dagger", "mace", "bow", "trident", "shield"]
}

def determine_category(item_name):
    """Determine the category of an item based on keywords."""
    item_name_lower = item_name.lower()
    for category, keywords in CATEGORY_MAPPING.items():
        if any(keyword in item_name_lower for keyword in keywords):
            return category
    return "miscellaneous"  # Default category if no match

def convert_text_to_json(input_path, output_path):
    """Converts a CSV-like text file to a structured JSON file (without page numbers)."""
    structured_data = {"consumables": {}, "non_combat": {}, "combat": {}, "miscellaneous": {}}

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 3:  # Only requires Name, Price, and Rarity
                    print(f"⚠️ Skipping invalid row: {row}")
                    continue

                item_name, price_gp, rarity = row[0], row[1], row[3]
                category = determine_category(item_name)

                structured_data[category][item_name.lower()] = {
                    "price_gp": int(price_gp),
                    "rarity": rarity
                }

        # Save structured JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4)

        print(f"✅ Successfully converted {input_path} to {output_path}")

    except FileNotFoundError:
        print(f"❌ Error: File {input_path} not found.")
    except Exception as e:
        print(f"❌ Error: {e}")

# Run the conversion
convert_text_to_json(input_file, output_file)