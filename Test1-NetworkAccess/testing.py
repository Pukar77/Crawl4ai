import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy


async def main():
    browser_conf = BrowserConfig(headless=True)

    run_conf = CrawlerRunConfig(
        capture_network_requests=True,
        cache_mode=CacheMode.BYPASS,
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_pages=3,
            max_depth=1
        ),
        verbose=True,
        # This is important - wait for network to be idle
        wait_for="networkidle",
        delay_before_return_html=2.0  # Wait 2 seconds for APIs to load
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        results = await crawler.arun(
            url="https://us.misumi-ec.com/?srsltid=AfmBOorCSwxHVUnPuxcSZC5-QHxRzgcZAswUfnQqbOTUAs1cRK28fESx",
            config=run_conf
        )

        # Filter out static files and keep only data requests
        IGNORE_EXTENSIONS = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', 
                            '.svg', '.woff', '.woff2', '.ttf', '.ico', '.webp']
        
        IGNORE_TYPES = ['stylesheet', 'script', 'image', 'font', 'media']
        
        API_KEYWORDS = ['api', 'json', 'data', 'graphql', 'ajax', 'xhr', 
                       'search', 'query', 'rest', 'endpoint']

        all_network_data = []
        
        for idx, res in enumerate(results):
            print(f"\n=== Page {idx+1}: {res.url} ===")
            
            if hasattr(res, 'network_requests') and res.network_requests:
                print(f"Total network requests: {len(res.network_requests)}")
                
                # Filter for meaningful data requests
                data_requests = []
                for req in res.network_requests:
                    url = req.get('url', '').lower()
                    
                    # Skip static files by extension
                    if any(url.endswith(ext) for ext in IGNORE_EXTENSIONS):
                        continue
                    
                    # Skip by resource type
                    resource_type = req.get('resourceType', '').lower()
                    if resource_type in IGNORE_TYPES:
                        continue
                    
                    # Only keep if it's XHR/Fetch or contains API keywords
                    if (resource_type in ['xhr', 'fetch', 'document'] or 
                        any(keyword in url for keyword in API_KEYWORDS)):
                        
                        # Check if response event exists
                        if req.get('event_type') == 'response':
                            data_requests.append(req)
                
                print(f"Filtered data requests: {len(data_requests)}")
                
                all_network_data.append({
                    'page_url': res.url,
                    'page_index': idx + 1,
                    'data_requests': data_requests
                })

        # Save complete data
        with open("network_responses.json", "w", encoding="utf-8") as f:
            json.dump(all_network_data, f, indent=2, ensure_ascii=False)
        
        # Create summary report
        with open("api_summary.txt", "w", encoding="utf-8") as f:
            for page_data in all_network_data:
                f.write(f"\n{'='*80}\n")
                f.write(f"Page: {page_data['page_url']}\n")
                f.write(f"Total Data Requests: {len(page_data['data_requests'])}\n")
                f.write(f"{'='*80}\n\n")
                
                for i, req in enumerate(page_data['data_requests'], 1):
                    f.write(f"{i}. {req.get('method', 'GET')} {req.get('url')}\n")
                    f.write(f"   Status: {req.get('status', 'N/A')}\n")
                    f.write(f"   Type: {req.get('resourceType', 'N/A')}\n")
                    
                    # Check for body/response content
                    if 'body' in req:
                        body_preview = str(req['body'])[:150]
                        f.write(f"   Response: {body_preview}...\n")
                    
                    f.write("\n")

    print("\n✅ Network responses saved to network_responses.json")
    print("✅ Summary saved to api_summary.txt")
    print("\n💡 If no responses captured, the site might use:")
    print("   - Server-side rendering (no API calls)")
    print("   - WebSockets for data")
    print("   - Heavy JavaScript that needs more wait time")


if __name__ == "__main__":
    asyncio.run(main())