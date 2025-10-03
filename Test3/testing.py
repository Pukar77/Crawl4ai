import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

async def main():
    browser_conf = BrowserConfig(headless=True)

    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        deep_crawl_strategy =  BFSDeepCrawlStrategy(
            max_pages = 20,
            max_depth = 2
            
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
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
