import google.generativeai as genai
# Removed: from google.generativeai.types import Part # Import Part for multimodal content
import pandas as pd
import json
import re
from dotenv import load_dotenv
import os
import html
from bs4 import BeautifulSoup
from PIL import Image # Library for image processing
from PIL.Image import Image as PILImage # Import specific PIL Image type for type hinting

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
# Helper function to load image
# ----------------------------------------------------------------------
# FIX: Uses PILImage type hint instead of the problematic 'Part'
def load_image_part(image_path: str) -> PILImage:
    """Loads a local image file and returns a PIL Image object."""
    try:
        img = Image.open(image_path)
        return img
    except FileNotFoundError:
        raise FileNotFoundError(f"Image file not found at path: {image_path}")
    except Exception as e:
        raise ValueError(f"Could not load image file: {e}")

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

# Load the image once outside the loop
try:
    image_part = load_image_part("image.png")
except Exception as e:
    # If the image fails to load, we cannot proceed with the requested multimodal task
    print(f"FATAL ERROR: {e}. Please ensure 'image.png' exists and is readable.")
    exit(1)


for idx, table_html in enumerate(tables, start=1):
    print(f"📤 Sending Table {idx} to Gemini for structured normalization (Multimodal)...")

    soup = BeautifulSoup(table_html, 'html.parser')
    table_content = str(soup.find('table') or table_html)
    
    # RESTORED PROMPT: Removed the "a/b/c" rule.
    prompt_text = f"""
    Convert the following HTML table into a strict JSON array based on the provided schema.
    
    **IMPORTANT:** Use the provided IMAGE (image.png) as the ground truth reference for all cell values and merging decisions. The final JSON output must match the visual layout shown in the image exactly, especially for merged cells.

    **CRITICAL NORMALIZATION RULES FOR MISUMI DATA:**
    1.  **Header Mapping:** The output columns must map exactly to the provided schema keys.
    2.  **Rowspan Filling (Fill Down):** If a cell has a rowspan, its value must be copied down to all rows it covers (referencing the IMAGE for correct span size).
    3.  **Specific Cell Groups:** Pay close attention to the columns under 'D', 'D - g6', and 'D - h5'. The image shows exactly how these values are meant to align across rows.
    4.  **Strict Output:** The output MUST be a JSON array of objects conforming exactly to the response schema.
    
    HTML Table:
    {table_content}
    """
    
    # Create the multimodal content list
    content_parts = [
        image_part,
        prompt_text
    ]

    try:
        generation_config_dict = {
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA
        }
        
        response = model.generate_content(
            content_parts, # Pass the list of image and text parts
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
        # Using utf-8-sig for better compatibility with Excel/spreadsheet software
        df.to_csv(csv_file, index=False, encoding="utf-8-sig") 
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