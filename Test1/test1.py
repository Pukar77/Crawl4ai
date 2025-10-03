import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

async def main():
    async with AsyncWebCrawler() as crawler:
        # Configure Crawl
        config = CrawlerRunConfig(
            scraping_strategy=LXMLWebScrapingStrategy(),
            deep_crawl_strategy=BFSDeepCrawlStrategy(
                max_depth=1,
                max_pages=2,
                allowed_domains=["quotes.toscrape.com"]   # keep crawler inside domain
            )
        )

        # Crawl and get results
        results = await crawler.run(
            url="https://quotes.toscrape.com/",
            config=config
        )

        for page in results.pages:   # ✅ iterate through crawled pages
            print(f"\n--- Processing URL: {page.url} ---")

            if page.success:
                print("✅ Crawl Successful for this page")

                # Use raw_html or parsed
                raw_html = page.raw_html       # ✅ raw HTML text
                soup = page.parsed             # ✅ BeautifulSoup object (already parsed)

                # Extract quotes and authors
                quotes = [q.text for q in soup.select("span.text")]
                authors = [a.text for a in soup.select("small.author")]

                for q, a in zip(quotes, authors):
                    print(f"Quote: {q}\nAuthor: {a}\n{'-'*50}")
            else:
                print(f"❌ Crawl failed on {page.url}: {page.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
