import google.generativeai as genai
import pandas as pd
import json
import re
from dotenv import load_dotenv
import os
import html
from bs4 import BeautifulSoup

# Load API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
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
    }
}

# ----------------------------------------------------------------------
# Main Processing Logic
# ----------------------------------------------------------------------

# Read HTML file
with open("output.md", "r", encoding="utf-8") as f:
    html_content = f.read()

tables = re.findall(r"<table.*?>.*?</table>", html_content, re.DOTALL)
print(f"🔍 Found {len(tables)} tables in output.md")

model = genai.GenerativeModel("gemini-2.5-flash")  
json_file = "output_combined.json"
all_json = []

for idx, table_html in enumerate(tables, start=1):
    print(f"📤 Sending Table {idx} to Gemini for structured normalization...")

    soup = BeautifulSoup(table_html, 'html.parser')
    table_content = str(soup.find('table') or table_html)
    
    prompt = f"""
    Convert the following HTML table into a strict JSON array based on the provided schema.

    **CRITICAL NORMALIZATION RULES FOR MISUMI DATA:**
    1.  **Header Mapping:** The output columns must map to the provided schema keys. For example, the column labeled 'D Tolerance g6' should map to 'Part Number Type', and 'D Tolerance h5' should map to 'Part Number D Tolerance'.
    2.  **Rowspan Filling (Fill Down):** If a cell has a rowspan, its value must be copied down to all rows it covers. For example, 'D Tolerance g6' spans many rows; copy that text to all corresponding rows in the final JSON under 'Part Number Type'.
    3.  **Specific Cell Groups:** Pay close attention to the columns under 'D', 'D - g6', and 'D - h5':
        * Rows for D=4, D=5, and D=6 are visually grouped. Ensure that the 'D - g6', 'D - h5', and 'D - f8' values are correctly matched to the 'D' values (4, 5, 6) on the **same HTML row**, regardless of column merging.
        * If a cell is empty or implicitly merged, use an empty string: "".
    4.  **Strict Output:** The output MUST be a JSON array of objects conforming exactly to the response schema.
    
    HTML Table:
    {table_content}
    """

    try:
        generation_config_dict = {
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA
        }
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config_dict
        )
        
        json_text = response.text.strip()
        data = json.loads(json_text)

        # Decode HTML entities
        for row in data:
            for key in row:
                if isinstance(row[key], str):
                    row[key] = html.unescape(row[key]).strip()

        # Save JSON
        all_json.extend(data)

        # Convert to DataFrame and Save to CSV
        df = pd.DataFrame(data)
        csv_file = f"table_{idx}.csv"
        df.to_csv(csv_file, index=False, encoding="utf-8")
        print(f"✅ Table {idx} processed and saved as {csv_file}")

    except json.JSONDecodeError as e:
        print(f"❌ JSON Decode Error on Table {idx}. The LLM did not return strict JSON: {e}")
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
