import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
import re

async def debug_product():
    async with AsyncWebCrawler() as crawler:
        # Get product 35 detail page
        url = "https://automationexercise.com/product_details/35"
        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        )

        if not result or not result.success:
            print(f"Failed to fetch {url}")
            return

        html = result.html
        soup = BeautifulSoup(html, "lxml")

        # Find all text nodes containing "Brand:" and "Category:"
        print("=== Searching for Brand: ===")
        brand_elements = soup.find_all(string=lambda t: t and "Brand:" in str(t))
        for elem in brand_elements:
            print(f"Found text: {repr(elem[:100])}")
            parent = elem.parent
            print(f"Parent tag: {parent.name}, class: {parent.get('class', 'None')}")
            print(f"Parent text: {repr(parent.get_text()[:200])}")

            # Print siblings
            next_sibling = parent.find_next_sibling()
            if next_sibling:
                print(f"Next sibling: {next_sibling.name}, text: {repr(next_sibling.get_text()[:100])}")

            print("---")

        print("\n=== Searching for Category: ===")
        category_elements = soup.find_all(string=lambda t: t and "Category:" in str(t))
        for elem in category_elements:
            print(f"Found text: {repr(elem[:100])}")
            parent = elem.parent
            print(f"Parent tag: {parent.name}, class: {parent.get('class', 'None')}")
            print(f"Parent text: {repr(parent.get_text()[:200])}")

            # Print siblings
            next_sibling = parent.find_next_sibling()
            if next_sibling:
                print(f"Next sibling: {next_sibling.name}, text: {repr(next_sibling.get_text()[:100])}")

            print("---")

        # Let's also look for table rows with this info
        print("\n=== Looking for table structure ===")
        all_tables = soup.find_all("table")
        print(f"Found {len(all_tables)} tables")

        for i, table in enumerate(all_tables):
            rows = table.find_all("tr")
            print(f"\nTable {i}: {len(rows)} rows")
            for row in rows[:5]:  # First 5 rows
                cells = row.find_all(["td", "th"])
                row_text = " | ".join([cell.get_text(strip=True) for cell in cells])
                if "Brand" in row_text or "Category" in row_text:
                    print(f"  {row_text}")

asyncio.run(debug_product())
