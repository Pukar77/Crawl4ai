import pytest
import os
from unittest import mock
from pathlib import Path
from Hamrobazar_Scrap import llm_scrap


@pytest.fixture
def setup_test_files(tmp_path):
    # Create a temporary markdown file
    md_path = tmp_path / "output.md"
    md_path.write_text("# Product\nPrice: $20\nLocation: NY\n", encoding="utf-8")

    # Change working directory to temp folder
    os.chdir(tmp_path)
    return md_path


@pytest.mark.asyncio
async def test_clean_markdown_creates_output_file(setup_test_files):
    # Mock model and response
    mock_model = mock.Mock()
    mock_response = mock.Mock()
    mock_response.text = "Title: Product\nPrice: $20\nLocation: NY"
    mock_model.generate_content.return_value = mock_response

    # ✅ Patch the GenerativeModel inside llm_scrap.genai
    with mock.patch.object(llm_scrap.genai, "GenerativeModel", return_value=mock_model):
        await llm_scrap.clean_markdown()

    # ✅ Assert that the cleaned file is created
    assert Path("output_cleaned.md").exists(), "Output file was not created."

    # ✅ Read the cleaned output and check contents
    cleaned_text = Path("output_cleaned.md").read_text(encoding="utf-8")
    assert "Price: $20" in cleaned_text
    assert "Location: NY" in cleaned_text

    # ✅ Ensure Gemini API (mock) was called once
    mock_model.generate_content.assert_called_once()
