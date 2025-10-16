import pytest
from unittest.mock import AsyncMock, patch
import asyncio


from Hamrobazar_Scrap import testing

@pytest.mark.asyncio
@patch("Hamrobazar_Scrap.testing.AsyncWebCrawler")  # Mock the crawler class
async def test_main(mock_crawler_class):
    # Mock the async context manager behavior
    mock_crawler = AsyncMock()
    mock_crawler.__aenter__.return_value = mock_crawler
    mock_crawler.arun.return_value = [
        AsyncMock(url="https://hamrobazaar.com/page1", markdown="Page 1 content"),
        AsyncMock(url="https://hamrobazaar.com/page2", markdown="Page 2 content")
    ]
    mock_crawler_class.return_value = mock_crawler

    # Run your main function
    await testing.main()

    # Assertions
    mock_crawler.arun.assert_called_once()
    called_args, called_kwargs = mock_crawler.arun.call_args
    assert called_kwargs["url"] == "https://hamrobazaar.com/"
