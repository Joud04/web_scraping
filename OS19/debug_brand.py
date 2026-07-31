import asyncio
import sys
sys.path.insert(0, 'src')

from collecteur.config import load_config
from collecteur.acquisition import Acquisition
from bs4 import BeautifulSoup

async def debug():
    config = load_config("config.toml")
    
    async with Acquisition(config) as acq:
        # Get product 6 detail page
        url = "https://automationexercise.com/product_details/6"
        html = await acq.fetch_html(url)
        
        soup = BeautifulSoup(html, "lxml")
        
        # Find all instances of "Brand"
        print("=== Looking for 'Brand' text ===")
        brand_elements = soup.find_all(string=lambda t: t and "Brand" in t)
        for i, elem in enumerate(brand_elements[:5]):  # First 5 occurrences
            print(f"\n[{i}] Found text: {repr(elem[:80])}")
            parent = elem.parent
            print(f"    Parent: <{parent.name}>")
            
            # Show context: prev/next siblings
            prev_sib = parent.find_previous_sibling()
            next_sib = parent.find_next_sibling()
            print(f"    Prev sibling: {prev_sib.name if prev_sib else 'None'} - {prev_sib.get_text(strip=True)[:50] if prev_sib else 'None'}")
            print(f"    Next sibling: {next_sib.name if next_sib else 'None'} - {next_sib.get_text(strip=True)[:50] if next_sib else 'None'}")
            
            # Show the parent's context
            print(f"    Parent text: {parent.get_text(strip=True)[:100]}")
            
            # Show grandparent structure
            gp = parent.parent
            if gp:
                children = list(gp.children)
                parent_idx = None
                for j, child in enumerate(children):
                    if hasattr(child, 'name'):
                        if child == parent:
                            parent_idx = j
                print(f"    Grandparent <{gp.name}> has {len(children)} children, parent is at index {parent_idx}")
                if parent_idx is not None and parent_idx + 1 < len(children):
                    next_child = children[parent_idx + 1]
                    print(f"    Next child in grandparent: {next_child.name if hasattr(next_child, 'name') else 'text'} = {repr(str(next_child)[:60])}")

asyncio.run(debug())
