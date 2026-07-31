from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class ChampObligatoireAbsent(Exception):
    """Levée quand un champ minimal exigé par la fiche de cible est introuvable."""
    pass

class Extraction:
    """Sélecteurs pour la cible S19 (Automation Exercise).

    C'est le seul module qui connaît la structure HTML de la cible.
    Il doit être testable sans réseau via des fixtures HTML.
    """

    def __init__(self):
        pass

    def extract_products_from_list(self, html: str) -> List[Dict[str, any]]:
        """Extrait les informations de base des produits depuis la page liste."""
        soup = BeautifulSoup(html, "lxml")
        products = []

        # Sur Automation Exercise, chaque produit est dans un div .product-image-wrapper
        items = soup.select(".product-image-wrapper")

        for item in items:
            try:
                # Le nom est généralement dans la première balise p de .productinfo
                info_div = item.select_one(".productinfo")
                if not info_div:
                    continue

                name_el = info_div.select_one("p")
                if not name_el:
                    raise ChampObligatoireAbsent("Nom du produit absent")
                name = name_el.get_text(strip=True)

                # Le prix peut être dans un élément avec la classe .product-price
                # ou simplement contenir "Rs."
                price_el = item.select_one(".product-price")
                if not price_el:
                    # Recherche fallback : n'importe quel texte contenant "Rs."
                    price_el = item.find(string=lambda t: t and "Rs." in t)

                price = price_el.get_text(strip=True) if hasattr(price_el, 'get_text') else (price_el if price_el else None)

                # L'URL est dans le lien "View Product"
                url = None
                all_links = item.find_all("a", href=True)
                for link in all_links:
                    if "/product_details/" in link["href"]:
                        url = link["href"]
                        break

                if not url:
                    raise ChampObligatoireAbsent("URL du produit absente")

                products.append({
                    "name": name,
                    "price": price,
                    "currency": None,
                    "category": None,
                    "brand": None,
                    "url": url
                })
            except ChampObligatoireAbsent as e:
                logger.warning(f"Produit ignoré : {e}")
                continue

        return products

    def extract_category_links(self, html: str) -> List[str]:
        """Extrait les liens vers les différentes catégories de produits."""
        soup = BeautifulSoup(html, "lxml")
        links = []
        # On cherche tous les liens qui pointent vers des catégories
        all_links = soup.find_all("a", href=True)
        for link in all_links:
            href = link["href"]
            if "/category_products/" in href:
                links.append(href)
        return list(set(links)) # Supprime les doublons

    def extract_next_page_url(self, html: str) -> Optional[str]:
        """Trouve l'URL de la page suivante (pagination)."""
        soup = BeautifulSoup(html, "lxml")
        # On cherche un lien de pagination "Next" ou similaire
        next_link = soup.find("a", string=lambda t: t and "Next" in t) or \
                    soup.select_one(".pagination li.next a") or \
                    soup.select_one("a[rel='next']")
        return next_link["href"] if next_link else None

    def extract_product_details(self, html: str) -> Dict[str, any]:
        """Extrait les champs complémentaires depuis la page de détail."""
        import re
        soup = BeautifulSoup(html, "lxml")

        details = {"brand": None, "category": None}

        # Filter out form and review text
        form_keywords = {"write", "review", "submit", "thank you", "successfully", "subscribed",
                        "subscription", "recent", "updates", "copyright", "email", "text"}

        def is_form_text(text):
            """Check if text is likely from a form rather than actual data."""
            text_lower = text.lower()
            return any(kw in text_lower for kw in form_keywords)

        def get_value_for_label(label_text):
            # Find all occurrences of the label
            elements = soup.find_all(string=lambda t: t and label_text in t)
            if not elements:
                return None

            for el in elements:
                # Skip if this text itself contains form keywords (likely in a form)
                if is_form_text(el):
                    continue

                # Try to extract from the immediate text node
                direct_text = str(el).strip()
                pattern = re.escape(label_text) + r"\s*:\s*([^:\n]+?)(?:\n|$)"
                match = re.search(pattern, direct_text)
                if match:
                    val = match.group(1).strip()
                    if val and len(val) < 100 and not is_form_text(val):
                        return val

                # Look at parent and next sibling
                parent = el.parent
                if parent:
                    # Check if there's text right after the label in the same parent
                    text_after_label = re.sub(r".*?" + re.escape(label_text) + r"\s*:?\s*", "", direct_text)
                    if text_after_label and len(text_after_label) < 100 and not is_form_text(text_after_label):
                        return text_after_label

                    # Look for value in next element sibling
                    next_elem = parent.find_next_sibling()
                    if next_elem:
                        val = next_elem.get_text(strip=True).split("\n")[0].strip()
                        if val and len(val) < 100 and not is_form_text(val):
                            return val

                    # Check in table structure
                    td = parent.find_parent("td")
                    if td:
                        next_td = td.find_next_sibling("td")
                        if next_td:
                            val = next_td.get_text(strip=True).split("\n")[0].strip()
                            if val and len(val) < 100 and not is_form_text(val):
                                return val

            return None

        details["category"] = get_value_for_label("Category:")
        details["brand"] = get_value_for_label("Brand:")

        for k, v in details.items():
            if v == "":
                details[k] = None

        return details
