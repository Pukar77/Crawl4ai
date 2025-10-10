import google.generativeai as genai
import pandas as pd
import json
import re
from dotenv import load_dotenv
import os
import html
from bs4 import BeautifulSoup
from PIL import Image
from PIL.Image import Image as PILImage
from typing import List, Dict, Any

# Load API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file.")

genai.configure(api_key=api_key)

# ----------------------------------------------------------------------
# Enhanced Table Normalizer - Handles rowspan and colspan
# ----------------------------------------------------------------------

def normalize_table_with_spans(table_html: str) -> List[List[str]]:
    """
    Parse HTML table and expand all rowspan/colspan into a normalized 2D grid.
    Each cell is duplicated across its span range.
    """
    soup = BeautifulSoup(table_html, 'html.parser')
    table = soup.find('table')
    if not table:
        return []
    
    rows = table.find_all('tr')
    if not rows:
        return []
    
    # First pass: determine grid dimensions
    max_cols = 0
    for row in rows:
        cells = row.find_all(['th', 'td'])
        col_count = sum(int(cell.get('colspan', 1)) for cell in cells)
        max_cols = max(max_cols, col_count)
    
    # Initialize grid with None values
    grid = []
    
    for row_idx, row in enumerate(rows):
        if row_idx >= len(grid):
            grid.append([None] * max_cols)
        
        cells = row.find_all(['th', 'td'])
        col_idx = 0
        
        for cell in cells:
            # Find next available column (skip already filled cells from previous rowspans)
            while col_idx < max_cols and grid[row_idx][col_idx] is not None:
                col_idx += 1
            
            if col_idx >= max_cols:
                break
            
            # Get cell value and clean it
            cell_text = cell.get_text(strip=True)
            cell_text = html.unescape(cell_text)
            
            # Get span values
            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))
            
            # Fill the grid for this cell's span
            for r_offset in range(rowspan):
                target_row = row_idx + r_offset
                
                # Ensure grid has enough rows
                while len(grid) <= target_row:
                    grid.append([None] * max_cols)
                
                for c_offset in range(colspan):
                    target_col = col_idx + c_offset
                    if target_col < max_cols:
                        grid[target_row][target_col] = cell_text
            
            col_idx += colspan
    
    # Convert None to empty strings
    normalized = [[cell if cell is not None else "" for cell in row] for row in grid]
    
    return normalized


def extract_schema_with_llm(model, table_html: str, image_part: PILImage = None) -> List[str]:
    """
    Use LLM to dynamically extract column schema from the table.
    """
    print("    🔍 Detecting schema with LLM...")
    
    # Prepare content for LLM
    content_parts = []
    if image_part:
        content_parts.append(image_part)
    
    prompt = f"""
Analyze this HTML table and identify ALL column headers/names in order from left to right.

IMPORTANT RULES:
1. Look at the table structure carefully, especially merged header cells (rowspan/colspan)
2. Combine multi-level headers into single descriptive column names
3. Return ONLY a JSON array of column names as strings
4. The number of columns should match the actual data columns in the table
5. Use clear, descriptive names that capture the column meaning

Example output format:
["Column1", "Column2", "Column3", ...]

HTML Table:
{table_html[:3000]}
"""
    
    content_parts.append(prompt)
    
    try:
        schema_config = {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            }
        }
        
        response = model.generate_content(content_parts, generation_config=schema_config)
        schema = json.loads(response.text.strip())
        
        if isinstance(schema, list) and len(schema) > 0:
            print(f"    ✓ Detected {len(schema)} columns: {schema}")
            return schema
        else:
            print("    ⚠️ Invalid schema format, using fallback")
            return []
            
    except Exception as e:
        print(f"    ⚠️ Schema detection failed: {e}")
        return []


def process_table_with_llm(model, table_html: str, normalized_grid: List[List[str]], 
                           schema: List[str], image_part: PILImage = None) -> List[Dict[str, Any]]:
    """
    Use LLM to convert normalized grid to structured data with dynamic schema.
    """
    print("    🤖 Processing table with LLM...")
    
    # Create dynamic response schema
    response_schema = {
        "type": "ARRAY",
        "description": "Array of table rows as structured objects",
        "items": {
            "type": "OBJECT",
            "properties": {
                col: {"type": "STRING", "description": f"Value for column: {col}"}
                for col in schema
            },
            "required": schema
        }
    }
    
    # Prepare content
    content_parts = []
    if image_part:
        content_parts.append(image_part)
    
    # Convert grid to readable format for LLM
    grid_text = "\n".join(["\t".join(row) for row in normalized_grid])
    
    prompt = f"""
Convert this normalized table data into structured JSON based on the detected schema.

SCHEMA (column names in order):
{json.dumps(schema, indent=2)}

NORMALIZED TABLE DATA:
{grid_text}

INSTRUCTIONS:
1. The table has been pre-normalized - all rowspan/colspan have been expanded
2. Map each row to the schema columns IN ORDER
3. Skip header rows and process only data rows
4. If the image is provided, use it to verify correctness
5. Preserve all values exactly as they appear
6. Return a JSON array of objects matching the schema

HTML Table (for reference):
{table_html[:2000]}
"""
    
    content_parts.append(prompt)
    
    try:
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": response_schema
        }
        
        response = model.generate_content(content_parts, generation_config=generation_config)
        json_text = response.text.strip()
        data = json.loads(json_text)
        
        # Clean up HTML entities
        for row in data:
            for key in row:
                if isinstance(row[key], str):
                    row[key] = html.unescape(row[key]).strip()
        
        print(f"    ✓ Extracted {len(data)} rows")
        return data
        
    except json.JSONDecodeError as e:
        print(f"    ❌ JSON decode error: {e}")
        return []
    except Exception as e:
        print(f"    ❌ Processing error: {e}")
        return []


def fallback_structured_data(normalized_grid: List[List[str]]) -> List[Dict[str, Any]]:
    """
    Fallback method: Use first row as headers and convert grid to structured data.
    """
    if len(normalized_grid) < 2:
        return []
    
    # Use first row as headers (or generate generic column names)
    headers = normalized_grid[0]
    if not any(headers):  # If first row is empty, generate column names
        headers = [f"Column_{i+1}" for i in range(len(normalized_grid[0]))]
    
    structured_data = []
    
    # Process remaining rows
    for row in normalized_grid[1:]:
        row_dict = {}
        for idx, (header, value) in enumerate(zip(headers, row)):
            col_name = header if header else f"Column_{idx+1}"
            row_dict[col_name] = value
        structured_data.append(row_dict)
    
    return structured_data


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

def main():
    # Read HTML file
    with open("output.md", "r", encoding="utf-8") as f:
        html_content = f.read()

    tables = re.findall(r"<table.*?>.*?</table>", html_content, re.DOTALL)
    print(f"🔍 Found {len(tables)} tables in output.md\n")

    all_json = []
    json_file = "output_combined.json"
    
    # Initialize model
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # Try to load reference image
    image_part = None
    try:
        image_part = load_image_part("image.png")
        print("✓ Reference image loaded\n")
    except Exception as e:
        print(f"⚠️ No reference image available ({e})\n")

    for idx, table_html in enumerate(tables, start=1):
        print(f"{'='*60}")
        print(f"📊 Processing Table {idx}/{len(tables)}")
        print(f"{'='*60}")
        
        # Step 1: Normalize the table structure
        print("  Step 1: Normalizing table structure...")
        normalized_grid = normalize_table_with_spans(table_html)
        
        if not normalized_grid:
            print(f"  ❌ Table {idx} could not be parsed\n")
            continue
        
        print(f"  ✓ Normalized to {len(normalized_grid)} rows × {len(normalized_grid[0])} columns")
        
        # Step 2: Extract schema using LLM
        print("  Step 2: Extracting schema...")
        schema = extract_schema_with_llm(model, table_html, image_part)
        
        if not schema:
            print("  ⚠️ Using fallback method for schema detection")
            structured_data = fallback_structured_data(normalized_grid)
        else:
            # Step 3: Process table with detected schema
            print("  Step 3: Converting to structured data...")
            structured_data = process_table_with_llm(
                model, table_html, normalized_grid, schema, image_part
            )
            
            if not structured_data:
                print("  ⚠️ LLM processing failed, using fallback")
                structured_data = fallback_structured_data(normalized_grid)
        
        if not structured_data:
            print(f"  ❌ Table {idx} produced no structured data\n")
            continue
        
        # Save data
        all_json.append({
            "table_index": idx,
            "schema": list(structured_data[0].keys()) if structured_data else [],
            "data": structured_data
        })
        
        # Save individual CSV
        df = pd.DataFrame(structured_data)
        csv_file = f"table_{idx}.csv"
        df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        print(f"  ✅ Saved as {csv_file}")
        
        # Debug: Print preview
        print(f"\n  Preview of Table {idx}:")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Shape: {df.shape}")
        if len(df) > 0:
            print(f"\n{df.head(3).to_string(index=False)}")
        print()

    # Save combined JSON
    with open(json_file, "w", encoding="utf-8") as f_json:
        json.dump(all_json, f_json, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"🎉 Processing complete!")
    print(f"{'='*60}")
    print(f"  • Processed {len(tables)} tables")
    print(f"  • Total data rows: {sum(len(t['data']) for t in all_json)}")
    print(f"  • Combined JSON: {json_file}")
    print(f"  • Individual CSVs: table_1.csv, table_2.csv, ...")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()