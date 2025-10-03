import asyncio
from pathlib import Path
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy


# Save scraped content into a clean markdown file
def save_to_markdown(content: str, url: str, filename: str = "scraped_output.md"):
    output_path = Path(filename)
    with output_path.open("a", encoding="utf-8") as f:
        f.write(f"# URL: {url}\n\n")
        f.write(content.strip())
        f.write("\n\n---\n\n")
    print(f"✅ Saved: {url} → {filename}")


# Scrape a single URL
async def scrape_single_url(crawler, url: str):
    config = CrawlerRunConfig(
        scraping_strategy=LXMLWebScrapingStrategy(),  # extracts text content
        crawler_strategy=AsyncPlaywrightCrawlerStrategy(),  # JS rendering
        deep_crawl_strategy=None,  # no deep crawl
    )

    try:
        results = await crawler.arun(url, config=config)

        # Ensure results is a list
        if not results:
            print(f"❌ No results for {url}")
            return
        if not isinstance(results, list):
            results = [results]

        for res in results:
            if getattr(res, "success", False):
                content = getattr(res, "extracted_content", None) or getattr(res, "html", None)
                if content:
                    save_to_markdown(content, url)
                else:
                    print(f"⚠️ No content extracted for {url}")
            else:
                print(f"❌ Failed to scrape {url}")

    except Exception as e:
        print(f"🚨 Error scraping {url}: {e}")


# Main function
async def main():
    link_file = Path("crawlLink.txt")
    if not link_file.exists():
        print("❌ crawlLink.txt not found.")
        return

    with link_file.open("r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print("⚠️ No URLs found in crawlLink.txt")
        return

    print(f"🔗 Found {len(urls)} URLs in crawlLink.txt")

    async with AsyncWebCrawler() as crawler:
        for url in urls:
            await scrape_single_url(crawler, url)


if __name__ == "__main__":
    asyncio.run(main())
