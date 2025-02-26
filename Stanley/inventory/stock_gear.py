import json
import os

# Define file paths
input_file = "fixed_advGear.json"  # Ensure the file exists
output_file = "stocked_advGear.json"

# Default stock values (adjust as needed)
DEFAULT_STOCK = 3

# Load the existing JSON file and add stock values
try:
    with open(input_file, "r") as f:
        data = json.load(f)

    # Ensure stock values are added to each item
    for category, items in data.items():
        for item_name, details in items.items():
            if isinstance(details, dict):
                details.setdefault("stock", DEFAULT_STOCK)  # Add stock if missing
            else:
                data[category][item_name] = {"price_cp": details, "stock": DEFAULT_STOCK}

    # Save the updated JSON file
    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)

    print(f"✅ Stock values added and saved to {output_file}")

except FileNotFoundError:
    print(f"❌ Error: File {input_file} not found. Ensure it exists in the correct folder.")
except json.JSONDecodeError:
    print(f"❌ Error: Could not parse {input_file}. Check for formatting issues.")