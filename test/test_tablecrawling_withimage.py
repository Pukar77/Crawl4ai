import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
import asyncio

from Tablecrawling_withimage.table import main  # adjust if your file/module path is different

@pytest.mark.asyncio
@patch("Tablecrawling_withimage.table.BeautifulSoup")
@patch("Tablecrawling_withimage.table.AsyncWebCrawler")

async def test_main(mock_crawler_class, mock_bs):
    """
    Test the main async scraping function without real network access.
    """

    # --- 1️⃣ Mock AsyncWebCrawler ---
    mock_crawler = AsyncMock()
    mock_crawler.__aenter__.return_value = mock_crawler

    # Mock a result object
    mock_result = AsyncMock()
    mock_result.url = "https://us.misumi-ec.com/vona2/detail/110302193040/?list=PageCategory"
    mock_result.html = "<html><div class='pad_b15'><table><tr><td>Test</td></tr></table></div></html>"

    mock_crawler.arun.return_value = [mock_result]
    mock_crawler_class.return_value = mock_crawler

    # --- 2️⃣ Mock BeautifulSoup behavior ---
    mock_table = "<table><tr><td>Test</td></tr></table>"
    mock_div = MagicMock()
    mock_div.find_all.return_value = [mock_table]

    mock_soup = MagicMock()
    # When searching for divs, return the mocked div
    mock_soup.find_all.side_effect = lambda tag, class_: [mock_div] if tag == "div" else [mock_table]
    mock_bs.return_value = mock_soup

    # --- 3️⃣ Run main() in a temp directory ---
    temp_file = Path("output.md")
    if temp_file.exists():
        temp_file.unlink()  # clean previous runs

    await main()

    # --- 4️⃣ Assertions ---
    # Check that crawler.arun was called once
    mock_crawler.arun.assert_called_once()
    called_args, called_kwargs = mock_crawler.arun.call_args
    assert "url" in called_kwargs
    assert called_kwargs["url"] == "https://us.misumi-ec.com/vona2/detail/110302193040/?list=PageCategory"

    # Check that output.md was created
    assert temp_file.exists(), "output.md was not created"

    # Check that the file contains a table
    content = temp_file.read_text(encoding="utf-8")
    assert "<table>" in content
    assert "Test" in content

    print("✅ Test passed: main() runs correctly with mocked crawler and writes output.md")
