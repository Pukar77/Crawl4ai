import google.generativeai as genai
import pandas as pd
import json
import re
from dotenv import load_dotenv
import os

# Load API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Read HTML file
with open("output.md", "r", encoding="utf-8") as f:
    html_content = f.read()

# Extract all tables (no class filtering)
tables = re.findall(r"<table.*?>.*?</table>", html_content, re.DOTALL)
print(f"🔍 Found {len(tables)} tables in output.md")

# Use a valid Gemini model
model = genai.GenerativeModel("gemini-2.5-flash")  # or "gemini-2.5-flash" if available

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
    
    HTML:
    {table_html}
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Extract JSON array only
        json_match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
        if not json_match:
            print(f"⚠️ Gemini did not return valid JSON for Table {idx}")
            continue

        json_text = json_match.group(0)

        # Fix minor JSON issues
        json_text = re.sub(r",\s*([\]}])", r"\1", json_text)
        json_text = json_text.replace("“", '"').replace("”", '"')

        # Load JSON safely
        data = json.loads(json_text)
        df = pd.DataFrame(data)
        all_json.append(data)

        # Save each table to a separate CSV
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
