import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

async def get_network_response():
    browser_cfg = BrowserConfig(
        viewport_height = 720,
        viewport_width= 1280
    )
    config = CrawlerRunConfig(
        exclude_external_links=True,
        scan_full_page = True,
        exclude_social_media_links = True,
        scroll_delay=0.8,
        wait_for_images = True,
        verbose= False,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        capture_network_requests=True,
        capture_console_messages=True,
        page_timeout=500000,
        simulate_user = True,
        exclude_social_media_domains = True,

    )
    async with AsyncWebCrawler(config= browser_cfg) as crawler:
        result = await crawler.arun(
            url = "https://www.daraz.com.np/accessories-fashion/?from=suggest_normal&q=camera",
            config=config
        )

        if result.success:
            # Analyze network requests
            if result.network_requests:
                # Count request types
                request_count = len([r for r in result.network_requests if r.get("event_type") == "request"])
                response_count = len([r for r in result.network_requests if r.get("event_type") == "response"])
                failed_count = len([r for r in result.network_requests if r.get("event_type") == "request_failed"])

                print(f"Requests: {request_count}, Responses: {response_count}, Failed: {failed_count}")

                # Find API calls
                api_calls = [r for r in result.network_requests 
                            if r.get("event_type") == "request" and "api" in r.get("url", "")]
                if api_calls:
                    print(f"Detected {len(api_calls)} API calls:")
                    for call in api_calls[:3]:  # Show first 3
                        print(f"  - {call.get('method')} {call.get('url')}")

            # Analyze console messages
            if result.console_messages:
                print(f"Captured {len(result.console_messages)} console messages")

                # Group by type
                message_types = {}
                for msg in result.console_messages:
                    msg_type = msg.get("type", "unknown")
                    message_types[msg_type] = message_types.get(msg_type, 0) + 1

                print("Message types:", message_types)

                # Show errors (often the most important)
                errors = [msg for msg in result.console_messages if msg.get("type") == "error"]
                if errors:
                    print(f"Found {len(errors)} console errors:")
                    for err in errors[:2]:  # Show first 2
                        print(f"  - {err.get('text', '')[:100]}")
            
            data_to_return = {
                "url":result.url,
                "network_requests": result.network_requests or []
            }
            
            return data_to_return

if __name__ == "__main__":
    data = asyncio.run(get_network_response())
    if data:
        # Save to file
        with open("alteration_linear_shaft.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Saved network response to alteration_linear_shaft.json")

        # Print to stdout
        # print(json.dumps(data, indent=2))
