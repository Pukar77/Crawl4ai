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
from typing import List, Dict, Any, Tuple

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


def detect_split_tables(tables: List[str], grids: List[List[List[str]]]) -> List[Tuple[int, int]]:
    """
    Detect pairs of tables that should be merged horizontally.
    Returns list of tuples (left_table_idx, right_table_idx).
    """
    merge_pairs = []
    
    for i in range(len(grids) - 1):
        grid1 = grids[i]
        grid2 = grids[i + 1]
        
        if not grid1 or not grid2:
            continue
        
        # Check if they have the same number of rows (or very close)
        row_diff = abs(len(grid1) - len(grid2))
        
        # Check if first table has significantly fewer columns (likely the left part)
        col_count1 = len(grid1[0]) if grid1 else 0
        col_count2 = len(grid2[0]) if grid2 else 0
        
        # Heuristic: Tables should be merged if:
        # 1. Same or similar row count (within 2 rows difference)
        # 2. First table has fewer columns (likely split design)
        if row_diff <= 2 and col_count1 < col_count2:
            merge_pairs.append((i, i + 1))
            print(f"  🔗 Detected split tables: Table {i+1} ({len(grid1)}×{col_count1}) + Table {i+2} ({len(grid2)}×{col_count2})")
    
    return merge_pairs


def merge_table_grids(grid1: List[List[str]], grid2: List[List[str]]) -> List[List[str]]:
    """
    Merge two table grids horizontally (side by side).
    """
    if not grid1:
        return grid2
    if not grid2:
        return grid1
    
    # Use the maximum number of rows
    max_rows = max(len(grid1), len(grid2))
    
    merged = []
    for row_idx in range(max_rows):
        # Get rows from both grids, or empty row if index out of bounds
        row1 = grid1[row_idx] if row_idx < len(grid1) else [""] * len(grid1[0])
        row2 = grid2[row_idx] if row_idx < len(grid2) else [""] * len(grid2[0])
        
        # Concatenate horizontally
        merged_row = row1 + row2
        merged.append(merged_row)
    
    return merged


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

    # Step 1: Normalize all tables first
    print("📐 Normalizing all tables...\n")
    all_grids = []
    for idx, table_html in enumerate(tables, start=1):
        grid = normalize_table_with_spans(table_html)
        all_grids.append(grid)
        if grid:
            print(f"  Table {idx}: {len(grid)} rows × {len(grid[0])} columns")
    
    # Step 2: Detect split tables that should be merged
    print("\n🔍 Detecting split tables...")
    merge_pairs = detect_split_tables(tables, all_grids)
    
    # Create a set of tables to skip (right side of merged pairs)
    skip_indices = set()
    merged_tables = {}  # Maps left_idx to merged result
    
    for left_idx, right_idx in merge_pairs:
        skip_indices.add(right_idx)
        merged_grid = merge_table_grids(all_grids[left_idx], all_grids[right_idx])
        merged_tables[left_idx] = {
            'grid': merged_grid,
            'html': tables[left_idx] + "\n<!-- MERGED WITH -->\n" + tables[right_idx],
            'original_indices': [left_idx, right_idx]
        }
        print(f"  ✓ Will merge Table {left_idx+1} + Table {right_idx+1} → {len(merged_grid)} rows × {len(merged_grid[0])} columns")
    
    print()
    
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

    output_table_idx = 1
    
    for idx in range(len(tables)):
        # Skip tables that were merged as the right side
        if idx in skip_indices:
            print(f"⏭️  Skipping Table {idx+1} (merged into previous table)\n")
            continue
        
        print(f"{'='*60}")
        print(f"📊 Processing Table {idx+1} → Output Table {output_table_idx}")
        print(f"{'='*60}")
        
        # Check if this table was merged
        if idx in merged_tables:
            merged_info = merged_tables[idx]
            normalized_grid = merged_info['grid']
            table_html = merged_info['html']
            print(f"  🔗 Using merged table (originally Table {idx+1} + Table {idx+2})")
        else:
            normalized_grid = all_grids[idx]
            table_html = tables[idx]
        
        if not normalized_grid:
            print(f"  ❌ Table could not be parsed\n")
            continue
        
        print(f"  ✓ Table size: {len(normalized_grid)} rows × {len(normalized_grid[0])} columns")
        
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
            print(f"  ❌ Table produced no structured data\n")
            continue
        
        # Save data
        all_json.append({
            "output_table_index": output_table_idx,
            "original_table_indices": merged_tables[idx]['original_indices'] if idx in merged_tables else [idx],
            "merged": idx in merged_tables,
            "schema": list(structured_data[0].keys()) if structured_data else [],
            "data": structured_data
        })
        
        # Save individual CSV
        df = pd.DataFrame(structured_data)
        csv_file = f"table_{output_table_idx}.csv"
        df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        print(f"  ✅ Saved as {csv_file}")
        
        # Debug: Print preview
        print(f"\n  Preview of Output Table {output_table_idx}:")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Shape: {df.shape}")
        if len(df) > 0:
            print(f"\n{df.head(3).to_string(index=False)}")
        print()
        
        output_table_idx += 1

    # Save combined JSON
    with open(json_file, "w", encoding="utf-8") as f_json:
        json.dump(all_json, f_json, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"🎉 Processing complete!")
    print(f"{'='*60}")
    print(f"  • Found {len(tables)} original tables")
    print(f"  • Merged {len(merge_pairs)} table pair(s)")
    print(f"  • Generated {output_table_idx - 1} output table(s)")
    print(f"  • Total data rows: {sum(len(t['data']) for t in all_json)}")
    print(f"  • Combined JSON: {json_file}")
    print(f"  • Individual CSVs: table_1.csv, table_2.csv, ...")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()