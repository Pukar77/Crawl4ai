import asyncio
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key="AIzaSyBlgz-Vz9tEs3J8slz_Kw4oZUVOdDHMC_w")

async def clean_markdown():
    # Load your saved markdown
    with open("output.md", "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Create model
    model = genai.GenerativeModel("gemini-2.5-flash")  # use valid model name

    # Send cleaning instruction
    response = model.generate_content(
        f"""
        Clean the following markdown. 
    Remove navigation, ads, and irrelevant text.
    Keep only product details such as:
    - Title
    - Price
    - Location
    - Description
    - Image URL (if available)

    Markdown:
    {raw_text}
        """
    )

    cleaned = response.text

    # Save cleaned text
    with open("output_cleaned.md", "w", encoding="utf-8") as f:
        f.write(cleaned)

    print("✅ Cleaned markdown saved to output_cleaned.md")

if __name__ == "__main__":
    asyncio.run(clean_markdown())
