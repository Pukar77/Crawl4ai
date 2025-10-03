import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    browser_conf = BrowserConfig(headless=True)

    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS
        
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        results = await crawler.arun(
            url="https://www.daraz.com.np/#?",
            config=run_conf
        )

        # Since results is a list
        for idx, res in enumerate(results):
            print(f"\n===== Page {idx+1} =====\n")
            print(res.markdown)   # print markdown for each crawled page

if __name__ == "__main__":
    asyncio.run(main())
