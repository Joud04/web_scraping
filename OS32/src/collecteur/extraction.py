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
        soup = BeautifulSoup(html, "lxml")

        details = {"brand": None, "category": None}

        def get_value_for_label(label_text):
            el = soup.find(string=lambda t: t and label_text in t)
            if not el:
                return None

            # On remonte jusqu'à un élément contenant la valeur
            current = el
            while current and current.name not in ["body", "html"]:
                text = current.get_text(strip=True)
                if len(text) > len(label_text):
                    # On utilise une regex pour capturer uniquement ce qui suit le label
                    # jusqu'au prochain label connu ou la fin de la ligne
                    import re
                    pattern = re.escape(label_text) + r"\s*([^:\n\r\t]+)"
                    match = re.search(pattern, text)
                    if match:
                        val = match.group(1).strip()
                        # On vérifie que la valeur n'est pas juste un label suivant
                        if val and "Quantity:" not in val and "Availability:" not in val:
                            return val
                current = current.parent

            td = el.find_parent("td")
            if td:
                next_td = td.find_next_sibling("td")
                if next_td:
                    return next_td.get_text(strip=True)

            return None

        details["category"] = get_value_for_label("Category:")
        details["brand"] = get_value_for_label("Brand:")

        for k, v in details.items():
            if v == "":
                details[k] = None

        return details
