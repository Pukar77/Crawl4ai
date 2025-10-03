import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from pathlib import Path

async def main():
    # Configure a 2-level deep crawl
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2, 
            include_external=False, # ensures crawler remains in daraz.com
            max_pages=100
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://www.daraz.com.np/#?", config=config)
       

        print(f"Crawled {len(results)} pages in total")

        # Show first 3 results
        for result in results[:3]:
            print(f"URL: {result.url}")
            print(f"Depth: {result.metadata.get('depth', 0)}")
        
        # Collect all URLs
        urls = [r.url for r in results if "pvid" in r.url]

        # Save URLs to file
        out_file = Path("crawlLink.txt")
        out_file.write_text("\n".join(urls))
        print(f"{len(urls)} URLs are saved in the file {out_file.resolve()}")

if __name__ == "__main__":
    asyncio.run(main())
