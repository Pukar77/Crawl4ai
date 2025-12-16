import asyncio
import csv
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# --- 1. Define the Structured Data Schema ---
product_schema = {
    "name": "Daraz Products",
    "baseSelector": "div.RfADt",
    "fields": [
        {
            "name": "product_url",
            "selector": "a",
            "attribute": "href",
            "type": "attribute" 
        },
        {
            "name": "product_name",
            "selector": "a",
            "attribute": "title",
            "type": "attribute"
        }
    ]
}

# --- 2. Helper Function to Process and Save Data ---
def process_data(json_content: str, filename: str) -> bool:
    """Parses JSON content and writes product data to a CSV file."""
    try:
        products = json.loads(json_content)
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON content.")
        return False

    if not products:
        return False

    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for item in products:
            raw_link = item.get('product_url', '')
            full_link = f"https:{raw_link}" if raw_link.startswith("//") else raw_link
            writer.writerow([item.get('product_name', 'N/A'), full_link])
    
    print(f"✅ Saved {len(products)} items.")
    return True

# --- 3. Helper Function to Check if Pagination Ended ---
def is_last_page(html_content: str) -> bool:
    """Check if we've reached the last page by examining the HTML."""
    if not html_content:
        return False
    
    # Check if the next button has both the disabled class and aria-disabled="true"
    if 'ant-pagination-next ant-pagination-disabled' in html_content and 'aria-disabled="true"' in html_content:
        return True
    
    return False

# --- 4. Main Asynchronous Crawling Function ---
async def crawl_products():
    browser_conf = BrowserConfig(
        headless=False,
        verbose=False,
    )

    url = "https://www.daraz.com.np/laptops/"
    session_id = "daraz_pagination_session"
    filename = "daraz_products.csv"
    
    page_number = 1
    current_url = url
    
    # JS code to click the next button
    js_next_page_click = """
    (async () => {
        const nextButton = document.querySelector('li.ant-pagination-next:not([aria-disabled="true"]) button.ant-pagination-item-link');
        if (nextButton) {
            nextButton.click();
            return true;
        } else {
            return false;
        }
    })();
    """
    
    # Setup CSV file with headers
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Link"])

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        
        # --- STEP 1: INITIAL NAVIGATION (Page 1) ---
        print(f"--- Loading Page {page_number} ---")
        
        initial_run_conf = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(product_schema),
            cache_mode=CacheMode.BYPASS,
            session_id=session_id,
            wait_for="div.RfADt" 
        )
        
        result = await crawler.arun(url=current_url, config=initial_run_conf)
        
        if result.success:
            process_data(result.extracted_content, filename)
        else:
            print(f"Initial load failed: {result.error_message}")
            return
            
        # --- STEP 2: LOOP FOR SUBSEQUENT PAGES ---
        page_number += 1
        
        pagination_run_conf = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(product_schema),
            cache_mode=CacheMode.BYPASS,
            session_id=session_id,
            js_code=js_next_page_click,
            js_only=True, 
            wait_for="div.RfADt",
            delay_before_return_html=3.0
        )
        
        while True:
            print(f"--- Executing JS click for Page {page_number} ---")

            result = await crawler.arun(url=current_url, config=pagination_run_conf)

            if not result.success:
                print(f"❌ Failed to retrieve data for page {page_number}. Stopping.")
                break
            
            # CRITICAL FIX: Check HTML content directly for disabled button
            if is_last_page(result.html):
                print("🛑 Pagination ended: Reached the last page (Next button is disabled).")
                break

            # Process the content
            products_found = process_data(result.extracted_content, filename)
            
            if not products_found:
                print("⚠️ No products extracted. Stopping.")
                break
                
            page_number += 1
            

    print(f"\n✅ Crawling completed. Total pages scraped: {page_number}")
    print(f"📁 Data saved to {filename}")

if __name__ == "__main__":
    asyncio.run(crawl_products())
