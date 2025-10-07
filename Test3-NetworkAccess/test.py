import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

async def main():
    # Configure browser with network tracking
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )

    # Enable network capture WITHOUT networkidle (it times out)
    config = CrawlerRunConfig(
        capture_network_requests=True,
        capture_console_messages=True,
        
        # REMOVED: wait_for="networkidle" - this causes timeout
        # Instead use fixed delay
        page_timeout=60000,  # 60 second timeout
        delay_before_return_html=8.0,  # Wait 8 seconds (enough for most requests)
        
        # Simulate user interaction to trigger lazy-loaded requests
        js_code=[
            "window.scrollTo(0, document.body.scrollHeight / 4);",
            "await new Promise(r => setTimeout(r, 1500));",
            "window.scrollTo(0, document.body.scrollHeight / 2);",
            "await new Promise(r => setTimeout(r, 1500));",
            "window.scrollTo(0, document.body.scrollHeight);",
            "await new Promise(r => setTimeout(r, 2000));",
            "window.scrollTo(0, 0);",
            "await new Promise(r => setTimeout(r, 1000));",
        ],
        
        verbose=True
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        print("🕷️  Starting crawl with 8 second delay + scrolling...")
        print("⏳ This will take ~15 seconds to complete...\n")
        
        result = await crawler.arun(
            url="https://www.daraz.com.np/#?",
            config=config
        )

        if result.success:
            print("✅ Page loaded successfully\n")
            
            # Analyze network requests
            if result.network_requests:
                print(f"📊 Captured {len(result.network_requests)} network events\n")

                # Count event types
                event_types = {}
                for req in result.network_requests:
                    evt = req.get("event_type", "unknown")
                    event_types[evt] = event_types.get(evt, 0) + 1
                
                print("Event breakdown:")
                for evt, count in sorted(event_types.items()):
                    print(f"  {evt}: {count}")
                print()

                # Filter only requests (not responses with binary errors)
                requests = [r for r in result.network_requests if r.get("event_type") == "request"]
                responses = [r for r in result.network_requests if r.get("event_type") == "response"]
                
                print(f"Requests: {len(requests)}")
                print(f"Responses: {len(responses)}\n")

                # Analyze request types (from request events)
                resource_types = {}
                for req in requests:
                    rtype = req.get("resourceType", "unknown")
                    resource_types[rtype] = resource_types.get(rtype, 0) + 1
                
                print("📦 Resource types:")
                for rtype, count in sorted(resource_types.items(), key=lambda x: x[1], reverse=True):
                    print(f"   {rtype}: {count}")
                print()

                # Find API/XHR/Fetch calls
                api_calls = [r for r in requests
                            if r.get("resourceType") in ["xhr", "fetch"] or 
                            "api" in r.get("url", "").lower() or
                            "graphql" in r.get("url", "").lower() or
                            "/search" in r.get("url", "").lower()]
                
                print(f"🔌 Detected {len(api_calls)} potential API/data calls:")
                if api_calls:
                    for call in api_calls[:15]:
                        url = call.get('url', '')
                        method = call.get('method', 'GET')
                        # Truncate long URLs
                        if len(url) > 100:
                            url = url[:97] + "..."
                        print(f"   {method:6} {url}")
                    if len(api_calls) > 15:
                        print(f"   ... and {len(api_calls) - 15} more")
                else:
                    print("   (None found - site might use server-side rendering)")
                print()

                # Find document/HTML requests (main page + iframes)
                documents = [r for r in requests if r.get("resourceType") == "document"]
                print(f"📄 Document requests: {len(documents)}")
                for doc in documents:
                    print(f"   {doc.get('url')}")
                print()

            # Analyze console messages
            if result.console_messages:
                print(f"💬 Captured {len(result.console_messages)} console messages")

                # Group by type
                message_types = {}
                for msg in result.console_messages:
                    msg_type = msg.get("type", "unknown")
                    message_types[msg_type] = message_types.get(msg_type, 0) + 1

                print("Message types:", message_types)

                # Show errors if any
                errors = [msg for msg in result.console_messages if msg.get("type") == "error"]
                if errors:
                    print(f"\n⚠️  Found {len(errors)} console errors:")
                    for err in errors[:5]:
                        print(f"   - {err.get('text', '')[:120]}")
                print()

            # Export data (only request events to avoid binary response errors)
            export_data = {
                "url": result.url,
                "total_events": len(result.network_requests or []),
                "requests": requests,  # Only request events
                "responses": [r for r in responses if not any(
                    r.get('url', '').endswith(ext) 
                    for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2', '.ttf']
                )],  # Exclude binary responses
                "console_messages": result.console_messages or [],
                "statistics": {
                    "total_requests": len(requests),
                    "total_responses": len(responses),
                    "api_calls": len(api_calls),
                    "documents": len(documents),
                    "resource_types": resource_types
                }
            }

            with open("network_capture.json", "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print("💾 Exported detailed capture data to network_capture.json")
            print("\n💡 Tip: If you need more requests, increase delay_before_return_html")
            
        else:
            print(f"❌ Crawl failed: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())