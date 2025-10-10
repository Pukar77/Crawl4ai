import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from bs4 import BeautifulSoup

async def main():
    browser_conf = BrowserConfig(headless=True)

    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_pages=1,
            max_depth=1
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        results = await crawler.arun(
            url="https://us.misumi-ec.com/vona2/detail/221005242985/?list=PageCategory&Tab=codeList&curSearch=%7B%22field%22%3A%22%40search%22%2C%22seriesCode%22%3A%22221005242985%22%2C%22innerCode%22%3A%22%22%2C%22sort%22%3A1%2C%22specSortFlag%22%3A0%2C%22allSpecFlag%22%3A0%2C%22page%22%3A1%2C%22pageSize%22%3A%2260%22%7D",
            config=run_conf
        )

        # Extract tables inside <div class="pad_b15">
        with open("output.md", "w", encoding="utf-8") as f:
            for idx, res in enumerate(results):
                html_content = res.html or res.content_as_text()
                if not html_content:
                    continue

                soup = BeautifulSoup(html_content, "html.parser")
                
                # Find all divs with class pad_b15
                divs = soup.find_all("div", class_="pad_b15")
                if not divs:
                    f.write(f"# No div.pad_b15 found in page {idx+1}\n")
                    continue

                table_count = 0
                for div in divs:
                    tables = div.find_all("table")  # no class filtering
                    for table in tables:
                        table_count += 1
                        f.write(f"\n\n# Table {table_count} from page {idx+1}: {res.url}\n\n")
                        f.write(str(table))
                        f.write("\n" + "="*80 + "\n")

                if table_count == 0:
                    f.write(f"# No table inside div.pad_b15 found in page {idx+1}\n")

    print("✅ Extracted tables inside div.pad_b15 saved to output.md")

if __name__ == "__main__":
    asyncio.run(main())
