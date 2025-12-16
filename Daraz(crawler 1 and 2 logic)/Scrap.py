import asyncio
import pandas as pd
import os
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup

# --- Configuration ---
CSV_FILE = 'daraz_products.csv'
OUTPUT_FILE = 'daraz_scraped_data.md'
URL_COLUMN_INDEX = 1 

async def scrape_product(html_content, url):
    """Extract product details using BeautifulSoup and CSS selectors"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract title
    title_elem = soup.select_one('.pdp-mod-product-badge-title')
    title = title_elem.get_text(strip=True) if title_elem else "N/A"
    
    # Extract price
    price_elem = soup.select('.pdp-mod-product-price span')
    price = price_elem.get_text(strip=True) if price_elem else "N/A"
    
    # Extract all feature list items
    feature_elems = soup.select('.html-content.detail-content li')
    features = [li.get_text(strip=True) for li in feature_elems]
    
    # Format features as markdown
    features_md = ""
    if features:
        for feat in features:
            features_md += f"  * {feat}\n"
    else:
        features_md = "  _No features found_\n"
    
    # Create markdown entry
    markdown_entry = f"""
## 🛍️ {title}

* **URL:** {url}
* **Price:** **{price}**
* **Product Features:**
{features_md}
---

"""
    return {
        'title': title,
        'price': price,
        'features': features,
        'markdown': markdown_entry
    }

async def process_daraz_products():
    # 1. Read URLs from CSV
    if not os.path.exists(CSV_FILE):
        print(f"❌ Error: CSV file not found at '{CSV_FILE}'")
        return

    df = pd.read_csv(CSV_FILE, header=None)
    if len(df.columns) <= URL_COLUMN_INDEX:
        print(f"❌ Error: CSV does not have column index {URL_COLUMN_INDEX}")
        return
        
    urls = df.iloc[:, URL_COLUMN_INDEX].astype(str).tolist()
    print(f"✅ Found {len(urls)} potential links to scrape.\n")

    # 2. Create/Clear Output File
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Daraz Product Scraping Results\n\n")
        f.write(f"*Total Products: {len(urls)}*\n\n")
        f.write("---\n\n")

    # 3. Configure Browser Settings
    browser_config = BrowserConfig(
        headless=False,  # Show browser window
        verbose=True,
        extra_args=['--disable-blink-features=AutomationControlled'],  # Avoid bot detection
    )
    
    # 4. Start Crawling
    success_count = 0
    failed_count = 0
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
                                                                  
        for i, url in enumerate(urls, 1):
            if not url.startswith('http'):
                print(f"⏭️  Skipping invalid URL: {url}\n")
                continue

            print(f"🔄 Scraping ({i}/{len(urls)}): {url}")

            try:
                # Enhanced JavaScript for content loading
                

                # Configure crawler run settings
                crawl_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    page_timeout=50000,
                    wait_for="css:.pdp-mod-product-badge-title, .pdp-mod-product-price span, .html-content.detail-content li",  # Wait for title
                    wait_for_timeout=30000,
                    delay_before_return_html=3.0,  # Wait 3 seconds
                    scroll_delay=5,
                    scan_full_page=True,
                    simulate_user=True
                    
                    # js_only = True
                )

                # Crawl the page
                result = await crawler.arun(
                    url=url,
                    config=crawl_config
                )

                if result.success and result.html:
                    # Extract data using CSS selectors
                    product_data = await scrape_product(result.html, url)
                    
                    # Check if we got valid data
                    if product_data['title'] == "N/A" and product_data['price'] == "N/A":
                        print(f"   ⚠️  No product data found - selectors may not match")
                        failed_count += 1
                        
                        # Save debug HTML
                        debug_file = f"debug_failed_{i}.html"
                        with open(debug_file, 'w', encoding='utf-8') as df:
                            df.write(result.html)
                        print(f"   📄 Saved HTML to {debug_file} for inspection\n")
                        continue
                    
                    # Write to markdown file
                    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                        f.write(product_data['markdown'])
                    
                    success_count += 1
                    print(f"   ✅ Success! Title: {product_data['title'][:50]}...")
                    print(f"   💰 Price: {product_data['price']}")
                    print(f"   📋 Features: {len(product_data['features'])} items\n")
                    
                else:
                    print(f"   ❌ Failed to load page")
                    failed_count += 1
                    print()

            except Exception as e:
                print(f"   🚨 Error: {type(e).__name__}: {e}")
                failed_count += 1
                print()

            # Politeness delay between requests
            await asyncio.sleep(3)

    # Final summary
    print("\n" + "="*60)
    print(f"✨ Scraping Complete!")
    print(f"📊 Results: {success_count} successful, {failed_count} failed")
    print(f"💾 Data saved to: {OUTPUT_FILE}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(process_daraz_products())
