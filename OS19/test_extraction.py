import sys
sys.path.insert(0, 'src')

from collecteur.extraction import Extraction
import asyncio
from collecteur.acquisition import Acquisition
from collecteur.config import load_config

async def test():
    config = load_config("config.toml")
    async with Acquisition(config) as acq:
        html = await acq.fetch_html("https://automationexercise.com/product_details/6")
        
    extractor = Extraction()
    details = extractor.extract_product_details(html)
    
    print(f"Extracted details: {details}")
    
    # Debug: manually find Brand text
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    
    print("\n=== Manual debug ===")
    brand_els = soup.find_all(string=lambda t: t and "Brand:" in t)
    print(f"Found {len(brand_els)} 'Brand:' elements")
    
    for i, el in enumerate(brand_els):
        print(f"\n[{i}] Element text: {repr(str(el)[:60])}")
        parent = el.parent
        print(f"    Parent: <{parent.name}>")
        print(f"    Parent.get_text(strip=True): {repr(parent.get_text(strip=True)[:60])}")
        
        # Check next_sibling
        ns = el.next_sibling
        print(f"    Next sibling: {repr(ns)[:60] if ns else 'None'}")

asyncio.run(test())
