import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    # Enable both network request capture and console message capture
    config = CrawlerRunConfig(
        capture_network_requests=True,
        capture_console_messages=True
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://us.misumi-ec.com/?srsltid=AfmBOorCSwxHVUnPuxcSZC5-QHxRzgcZAswUfnQqbOTUAs1cRK28fESx",
            config=config
        )

        if result.success:
            # Analyze network requests
            if result.network_requests:
                print(f"Captured {len(result.network_requests)} network events")

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

            # Export all captured data to a file for detailed analysis
            with open("network_capture.json", "w") as f:
                json.dump({
                    "url": result.url,
                    "network_requests": result.network_requests or [],
                    "console_messages": result.console_messages or []
                }, f, indent=2)

            print("Exported detailed capture data to network_capture.json")

if __name__ == "__main__":
    asyncio.run(main())