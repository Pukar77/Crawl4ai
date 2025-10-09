import google.generativeai as genai
import pandas as pd
import json
import re
from dotenv import load_dotenv
import os
import html
from bs4 import BeautifulSoup # Still needed for initial HTML cleanup

# Load API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
# NOTE: If API key is not found, this will raise an error.
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file.")

genai.configure(api_key=api_key)

# ----------------------------------------------------------------------
# Define the target JSON structure (normalized columns)
# ----------------------------------------------------------------------

# These column names are based on your desired CSV output
TARGET_COLUMN_SCHEMA = [
    "Part Number Type",
    "Part Number D Tolerance",
    "D",
    "D - g6",
    "D - h5",
    "D - f8",
    "L - 1 mm Increment",
    "C"
]

RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "description": "An array of product data rows, where each object represents a fully normalized row of the table.",
    "items": {
        "type": "OBJECT",
        "properties": {
            col: {"type": "STRING", "description": f"Value for the column: {col}"}
            for col in TARGET_COLUMN_SCHEMA
        }
        # FIX: Removed "propertyOrdering" as it caused an "Unknown field for Schema" error
    }
}

# ----------------------------------------------------------------------
# Main Processing Logic
# ----------------------------------------------------------------------

# Read HTML file
with open("output.md", "r", encoding="utf-8") as f:
    html_content = f.read()

# Extract all tables
# Note: This regex is simple, assumes tables are always clean <table...>...</table> blocks
tables = re.findall(r"<table.*?>.*?</table>", html_content, re.DOTALL)
print(f"🔍 Found {len(tables)} tables in output.md")

# Use Gemini model
model = genai.GenerativeModel("gemini-2.5-flash")  

# JSON file to store all tables
json_file = "output_combined.json"
all_json = []

for idx, table_html in enumerate(tables, start=1):
    print(f"📤 Sending Table {idx} to Gemini for structured normalization...")

    # Clean up the HTML table slightly before sending to LLM
    # This helps remove excessive whitespace and comments.
    soup = BeautifulSoup(table_html, 'html.parser')
    table_content = str(soup.find('table') or table_html)
    
    prompt = f"""
    Convert the following HTML table into a strict JSON array based on the provided schema.
    
    The HTML table uses complex rowspans and colspans. You must normalize the data:
    1. Identify all column headers exactly as listed in the JSON schema.
    2. If a cell spans multiple rows (rowspan), copy that cell's content down to all spanned rows in the final JSON output.
    3. If a cell spans multiple columns (colspan), ensure the values are placed in the correct corresponding columns in the final JSON output.
    4. Fill any blank or implicitly merged cells with an empty string: "".
    5. The output MUST be a JSON array of objects conforming exactly to the response schema.
    
    HTML Table:
    {table_content}
    """

    try:
        # Configuration for Structured Output
        generation_config_dict = {
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA
        }
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config_dict
        )
        
        # The response text should be a valid JSON string
        json_text = response.text.strip()
        data = json.loads(json_text)

        # Decode HTML entities in all cells (keys are already clean due to schema)
        for row in data:
            for key in row:
                if isinstance(row[key], str):
                    row[key] = html.unescape(row[key]).strip()

        # Save JSON
        all_json.extend(data)

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Save to CSV (fully editable)
        csv_file = f"table_{idx}.csv"
        df.to_csv(csv_file, index=False, encoding="utf-8")
        print(f"✅ Table {idx} processed and saved as {csv_file}")

    except json.JSONDecodeError as e:
        print(f"❌ JSON Decode Error on Table {idx}. The LLM did not return strict JSON: {e}")
        # Print the raw text output from the model for debugging
        print("Gemini raw output:", response.text[:1000])
        continue
    except Exception as e:
        print(f"❌ Other error on Table {idx}: {e}")
        continue

# Save all JSON in one file
with open(json_file, "w", encoding="utf-8") as f_json:
    json.dump(all_json, f_json, ensure_ascii=False, indent=4)

print(f"\n🎉 All tables processed. Individual CSVs saved.")
print(f"🎉 All JSON data saved as {json_file}")
