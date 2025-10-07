import json
import os

INPUT_FILE = "network_full_capture.json"
OUTPUT_FILE = "filtered_responses.json"

# Define what fields you want to keep from each response
# Note: The extraction logic below is tailored to pull 'content-type' 
# from headers and the full 'body' object, as requested.
REQUIRED_KEYS = ["url", "status", "mimeType", "encodedDataLength", "timestamp", "headers"]

def extract_response_data(event):
    """
    Extracts only the 'content-type' header and the full 'body' object 
    from a network response event, plus 'url' and 'timestamp' for context.
    Returns the filtered dictionary if it's a 'response' event, otherwise returns None.
    """
    # 1. Filter by event type
    if event.get("event_type") != "response":
        return None

    # Dictionary to hold the filtered key/value pairs
    filtered = {}
    
    # Include URL and Timestamp for context
    if event.get("url") is not None:
        filtered["url"] = event["url"]
    if event.get("timestamp") is not None:
        filtered["timestamp"] = event["timestamp"]

    # 2. Extract the entire 'body' object
    body = event.get("body")
    if body is not None:
        filtered["body"] = body

    # 3. Extract the 'content-type' from the 'headers' dictionary
    headers = event.get("headers")
    if isinstance(headers, dict):
        # Check both common capitalizations
        content_type = headers.get("content-type") or headers.get("Content-Type") 
        if content_type is not None:
            filtered["content-type"] = content_type
    
    # Only return data if at least a body or content-type was successfully extracted
    if "body" in filtered or "content-type" in filtered:
        return filtered

    return None # Return None if no meaningful data was found in a response event

def main():
    # Load the raw capture data
    print(f"Loading data from {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{INPUT_FILE}' not found. Please ensure the file exists.")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from '{INPUT_FILE}': {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    # The script now handles both nested (list of objects) and flat (single object) structures.
    network_events = []
    
    if isinstance(raw_data, list):
        # Flatten the list of lists of network requests from the typical nested format
        for entry in raw_data:
            if isinstance(entry, dict) and 'network_requests' in entry and isinstance(entry['network_requests'], list):
                network_events.extend(entry['network_requests'])
    elif isinstance(raw_data, dict) and 'network_requests' in raw_data and isinstance(raw_data['network_requests'], list):
        # Handle the case where the entire file is one large dictionary wrapping all events
        network_events = raw_data['network_requests']
    else:
        print("Warning: Input JSON structure is unexpected. Expected a list of objects or an object with 'network_requests'.")

    print(f"Total candidate network events found: {len(network_events)}")

    # Filter only responses and ensure all events are dictionaries before processing
    responses = [extract_response_data(event) for event in network_events if isinstance(event, dict)]
    responses = [r for r in responses if r]  # Remove None (non-response events or responses with no body/content-type)

    print(f"✅ Found {len(responses)} valid response events")

    # Save filtered data
    try:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(responses, f, indent=2)
        print(f"🎯 Saved filtered responses to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error saving file '{OUTPUT_FILE}': {e}")

if __name__ == "__main__":
    main()
