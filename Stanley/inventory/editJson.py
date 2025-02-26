import json

# Define file paths
input_file = "refined_advGear.json"  # Your incorrectly structured file
output_file = "fixed_advGear.json"  # The corrected version

# Load the existing JSON file
try:
    with open(input_file, "r") as f:
        data = json.load(f)

    # Ensure the JSON is a list before processing
    if not isinstance(data, list):
        print("❌ Error: JSON is already in dictionary format. No changes needed.")
        exit()

    # Create a new structured dictionary
    structured_data = {}

    for item in data:
        category = item.get("Category", "miscellaneous_equipment")  # Default category if missing
        name = item.get("Name", "").lower()
        price_cp = item.get("Value_cp", 0)

        if category not in structured_data:
            structured_data[category] = {}

        structured_data[category][name] = price_cp

    # Save the structured JSON file
    with open(output_file, "w") as f:
        json.dump(structured_data, f, indent=4)

    print(f"✅ Successfully converted JSON to dictionary format. Saved as {output_file}")

except FileNotFoundError:
    print(f"❌ Error: File {input_file} not found. Ensure it exists in the same directory.")
except json.JSONDecodeError:
    print(f"❌ Error: Could not parse {input_file}. Check for formatting issues.")