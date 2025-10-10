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


def convert_grid_to_structured_data(grid: List[List[str]]) -> List[Dict[str, str]]:
    """
    Convert normalized grid to structured data based on the table format.
    Assumes first 2 rows are headers.
    """
    if len(grid) < 3:  # Need at least header rows + 1 data row
        return []
    
    # Extract headers
    header_row1 = grid[0]  # Part Number, D, L, C
    header_row2 = grid[1]  # Type, D, g6, h5, f8, 1 mm Increment
    
    # Build column mapping
    structured_data = []
    
    # Process data rows (skip first 2 header rows)
    for row_idx in range(2, len(grid)):
        row = grid[row_idx]
        
        # Map based on your target schema
        row_data = {
            "Part Number Type": row[0] if len(row) > 0 else "",
            "Part Number D Tolerance": row[1] if len(row) > 1 else "",
            "D": row[2] if len(row) > 2 else "",
            "D - g6": row[3] if len(row) > 3 else "",
            "D - h5": row[4] if len(row) > 4 else "",
            "D - f8": row[5] if len(row) > 5 else "",
            "L - 1 mm Increment": row[6] if len(row) > 6 else "",
            "C": row[7] if len(row) > 7 else "",
        }
        
        structured_data.append(row_data)
    
    return structured_data


# ----------------------------------------------------------------------
# Target Schema (kept for reference)
# ----------------------------------------------------------------------

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
    "description": "An array of product data rows",
    "items": {
        "type": "OBJECT",
        "properties": {
            col: {"type": "STRING", "description": f"Value for the column: {col}"}
            for col in TARGET_COLUMN_SCHEMA
        }
    }
}


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
    print(f"🔍 Found {len(tables)} tables in output.md")

    all_json = []
    json_file = "output_combined.json"

    # Load image if using LLM approach
    use_llm = False  # Set to True if you want to use LLM verification
    image_part = None
    
    if use_llm:
        try:
            image_part = load_image_part("image.png")
            model = genai.GenerativeModel("gemini-2.5-flash")
        except Exception as e:
            print(f"⚠️ Warning: Could not load image ({e}). Using pure parsing approach.")
            use_llm = False

    for idx, table_html in enumerate(tables, start=1):
        print(f"\n📊 Processing Table {idx}...")
        
        # Step 1: Normalize the table structure
        normalized_grid = normalize_table_with_spans(table_html)
        
        if not normalized_grid:
            print(f"❌ Table {idx} could not be parsed")
            continue
        
        print(f"  ✓ Normalized to {len(normalized_grid)} rows × {len(normalized_grid[0]) if normalized_grid else 0} columns")
        
        # Step 2: Convert to structured data
        structured_data = convert_grid_to_structured_data(normalized_grid)
        
        if not structured_data:
            print(f"❌ Table {idx} produced no structured data")
            continue
        
        print(f"  ✓ Extracted {len(structured_data)} data rows")
        
        # Optional Step 3: Use LLM to verify/refine if image is available
        if use_llm and image_part:
            try:
                # Convert current data to JSON for LLM review
                current_json = json.dumps(structured_data, indent=2)
                
                prompt_text = f"""
Review and correct this parsed table data based on the reference image.
The data has been pre-normalized from HTML. Verify:
1. All merged cells are filled correctly
2. Column mappings are accurate
3. Values match the image exactly

Current parsed data:
{current_json}

Return the corrected JSON array following the same structure.
"""
                
                generation_config_dict = {
                    "response_mime_type": "application/json",
                    "response_schema": RESPONSE_SCHEMA
                }
                
                response = model.generate_content(
                    [image_part, prompt_text],
                    generation_config=generation_config_dict
                )
                
                json_text = response.text.strip()
                refined_data = json.loads(json_text)
                
                print(f"  ✓ LLM refinement applied")
                structured_data = refined_data
                
            except Exception as e:
                print(f"  ⚠️ LLM refinement failed ({e}), using parsed data")
        
        # Save data
        all_json.extend(structured_data)
        
        # Save individual CSV
        df = pd.DataFrame(structured_data)
        csv_file = f"table_{idx}.csv"
        df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        print(f"  ✅ Saved as {csv_file}")
        
        # Debug: Print first few rows
        print(f"\n  Preview of Table {idx}:")
        print(df.head(3).to_string(index=False))

    # Save combined JSON
    with open(json_file, "w", encoding="utf-8") as f_json:
        json.dump(all_json, f_json, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"🎉 Processing complete!")
    print(f"  • Processed {len(tables)} tables")
    print(f"  • Total rows: {len(all_json)}")
    print(f"  • Combined JSON: {json_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()