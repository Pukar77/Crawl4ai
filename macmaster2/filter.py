import json

INPUT_FILE = "network_capture.json"
OUTPUT_FILE = "filtered_responses.json"

def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    filtered_data = {
        "url": data.get("url", ""),
        "requests": [],
        "responses": []
    }

    # Extract request URLs
    for req in data.get("requests", []):
        if req.get("event_type") == "request":
            filtered_data["requests"].append(req.get("url"))

    # Extract response body, content-type, and timestamp
    for res in data.get("responses", []):
        if res.get("event_type") == "response":
            filtered_data["responses"].append({
                "url": res.get("url"),
                "timestamp": res.get("timestamp"),
                "content-type": res.get("headers", {}).get("content-type"),
                "body": res.get("body")
            })

    # Save filtered data
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Filtered data saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    main()
