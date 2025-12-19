import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    # 1. Browser Configuration: Global settings for the browser instance
    browser_config = BrowserConfig(
        headless=True,              # Run without a GUI
        verbose=True,               # Enable detailed logging
        browser_type="chromium"     # Default, but can be 'firefox' or 'webkit'
    )

    # 2. Crawler Run Configuration: Specific instructions for this crawl
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS, # Ensure we get fresh data, not from cache
        word_count_threshold=10,     # Exclude blocks with fewer than 10 words
        process_iframes=True,        # Crawl content inside iframes
        remove_overlay_elements=True # Clean up popups/modals automatically
    )

    # 3. Usage with Context Manager
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Perform the crawl
        result = await crawler.arun(
            url="https://www.example.com",
            config=run_config
        )

        if result.success:
            print("Crawl successful!")
            # The result object contains various formats
            print(f"Markdown snippet: {result.markdown[:200]}...")
        else:
            print(f"Crawl failed: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
