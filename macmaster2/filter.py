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

    filtered_responses = []

    for res in data.get("responses", []):
        if res.get("event_type") == "response":
            content_type = res.get("headers", {}).get("content-type", "")
            
            # Skip CSS responses
            if "text/css" in content_type:
                continue

            body = res.get("body")

            # Handle body type (string, dict, list, etc.)
            if isinstance(body, (dict, list)):
                body = json.dumps(body)
            elif not isinstance(body, str):
                continue  # Skip if not a valid string or dict/list

            # Clean and check word count
            body_text = body.strip()
            if not body_text or len(body_text.split()) < 20:
                continue

            filtered_responses.append({
                "url": res.get("url"),
                "body": body_text
            })

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered_responses, f, indent=2, ensure_ascii=False)
        print(f"✅ Filtered responses saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    main()
