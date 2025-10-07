import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

async def main():
    # Gradual scroll to trigger lazy-loaded content
    js_code = []
    for i in range(1, 11):
        js_code.append(f"window.scrollTo(0, document.body.scrollHeight * {i}/10);")
        js_code.append("await new Promise(r => setTimeout(r, 1500));")
    js_code.append("await new Promise(r => setTimeout(r, 5000));")  # final wait

    # Browser config
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )

    # Crawl config
    config = CrawlerRunConfig(
        capture_network_requests=True,
        capture_console_messages=True,
        page_timeout=120000,  # 2 minutes
        delay_before_return_html=10.0,
        js_code=js_code,
        verbose=True
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        url_to_crawl = "https://www.mcmaster.com/products/screws/socket-head-screws-2~/alloy-steel-socket-head-screws-8/"
        print(f"🕷️ Starting full capture crawl: {url_to_crawl}\n")

        result = await crawler.arun(url=url_to_crawl, config=config)

        if not result.success:
            print(f"❌ Crawl failed: {result.error_message}")
            return

        print("✅ Crawl completed successfully\n")
        
        network_events = result.network_requests or []

        print(f"📊 Total network events captured: {len(network_events)}")

        # Export full data as-is
        export_data = {
            "url": result.url,
            "total_events": len(network_events),
            "network_events": network_events,
            "console_messages": result.console_messages or []
        }

        # Save everything to JSON
        with open("network_full_capture.json", "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Full network capture saved to network_full_capture.json")

if __name__ == "__main__":
    asyncio.run(main())
