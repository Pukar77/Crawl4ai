import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy


async def main():
    browser_conf = BrowserConfig(headless=False)

    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_pages=5,
            max_depth=2
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        results = await crawler.arun(
            url="https://hamrobazaar.com/",
            config=run_conf
        )

        # Combine all markdown outputs into one file
        with open("output.md", "w", encoding="utf-8") as f:
            for idx, res in enumerate(results):
                f.write(f"\n\n# Page {idx+1}: {res.url}\n\n")
                f.write(res.markdown or "")
                f.write("\n" + "="*80 + "\n")

    print("✅ Markdown saved to output.md")

if __name__ == "__main__":
    asyncio.run(main())
