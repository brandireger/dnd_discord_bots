import json

# Load and display the refined JSON file
file_path = "refined_advGear.json"

try:
    with open(file_path, "r") as f:
        data = json.load(f)

    # Print categories and sample items
    for category, items in data.items():
        print(f"\n🔹 {category.replace('_', ' ').title()} ({len(items)} items):")
        for item, price in list(items.items())[:5]:  # Show only first 5 items
            print(f"  • {item.capitalize()} - {price} cp")

except FileNotFoundError:
    print("❌ Error: File not found. Ensure 'refined_advGear.json' is in the correct folder.")
except json.JSONDecodeError:
    print("❌ Error: Could not parse JSON. Ensure the file is correctly formatted.")