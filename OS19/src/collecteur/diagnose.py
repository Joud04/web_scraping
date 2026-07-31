import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup

async def diagnose():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://automationexercise.com/products",
            config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        )
        html = result.html
        soup = BeautifulSoup(html, "lxml")

        print("--- ALL LINKS ---")
        for a in soup.find_all("a", href=True):
            print(f"Text: {a.text.strip()} | Href: {a['href']}")

        print("\n--- ALL DIVS WITH CLASSES ---")
        for div in soup.find_all("div", class_=True):
            print(f"Div Class: {div['class']}")

        print("\n--- ALL P TAGS ---")
        for p in soup.find_all("p"):
            print(f"P Text: {p.text.strip()}")

asyncio.run(diagnose())
