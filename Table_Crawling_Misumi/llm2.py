import google.generativeai as genai
import pandas as pd
import json
import re
from dotenv import load_dotenv
import os
import html  # for decoding HTML entities

# Load API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Read HTML file
with open("output.md", "r", encoding="utf-8") as f:
    html_content = f.read()

# Extract all tables
tables = re.findall(r"<table.*?>.*?</table>", html_content, re.DOTALL)
print(f"🔍 Found {len(tables)} tables in output.md")

# Use Gemini model
model = genai.GenerativeModel("gemini-2.5-flash")  # safe fallback

# JSON file to store all tables
json_file = "output_combined.json"
all_json = []

for idx, table_html in enumerate(tables, start=1):
    print(f"📤 Sending Table {idx} to Gemini...")

    prompt = f"""
    Convert this HTML table into JSON.
    Each <tr> is one row.
    Use <th> as keys.
    If a cell is empty, use "".
    Do not merge columns.
    Preserve all special characters exactly.

    HTML:
    {table_html}
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Extract JSON array safely
        json_match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
        if not json_match:
            print(f"⚠️ Gemini did not return valid JSON for Table {idx}")
            continue

        json_text = json_match.group(0)

        # Fix minor JSON issues
        json_text = re.sub(r",\s*([\]}])", r"\1", json_text)
        json_text = json_text.replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")

        # Load JSON
        data = json.loads(json_text)

        # Decode HTML entities in all cells
        for row in data:
            for key in row:
                if isinstance(row[key], str):
                    row[key] = html.unescape(row[key]).strip()

        # Ensure all rows have the same keys
        all_keys = set()
        for row in data:
            all_keys.update(row.keys())
        for row in data:
            for key in all_keys:
                if key not in row:
                    row[key] = ""  # fill missing columns

        # Save JSON
        all_json.append(data)

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Save to CSV (fully editable)
        csv_file = f"table_{idx}.csv"
        df.to_csv(csv_file, index=False, encoding="utf-8")
        print(f"✅ Table {idx} processed and saved as {csv_file}")

    except json.JSONDecodeError as e:
        print(f"❌ JSON error on Table {idx}: {e}")
        print("Gemini output snippet:", text[:500])
        continue
    except Exception as e:
        print(f"❌ Other error on Table {idx}: {e}")
        continue

# Save all JSON in one file
with open(json_file, "w", encoding="utf-8") as f_json:
    json.dump(all_json, f_json, ensure_ascii=False, indent=4)

print(f"\n🎉 All tables processed. Individual CSVs saved.")
print(f"🎉 All JSON data saved as {json_file}")
