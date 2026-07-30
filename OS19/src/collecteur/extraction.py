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

        # On cherche les conteneurs de produits
        # Sur automationexercise.com/products, les produits sont souvent dans .product-pod ou similaire
        # On utilise des sélecteurs stables
        items = soup.select(".product-pod") # A vérifier avec le diagnostic réel

        for item in items:
            try:
                # 1. Nom
                name_el = item.select_one(".product-name a")
                if not name_el:
                    raise ChampObligatoireAbsent("Nom du produit absent")
                name = name_el.get_text(strip=True)

                # 2. Prix
                price_el = item.select_one(".product-price")
                price = price_el.get_text(strip=True) if price_el else None

                # 3. URL
                url_el = item.select_one("a")
                url = url_el["href"] if url_el else None
                if not url:
                    raise ChampObligatoireAbsent("URL du produit absente")

                # 4. Catégorie / Marque (souvent absentes de la liste, à chercher en détail)
                category = None
                brand = None

                products.append({
                    "name": name,
                    "price": price,
                    "currency": None, # À extraire via normalisation
                    "category": category,
                    "brand": brand,
                    "url": url
                })
            except ChampObligatoireAbsent as e:
                logger.warning(f"Produit ignoré : {e}")
                continue

        return products

    def extract_product_details(self, html: str) -> Dict[str, any]:
        """Extrait les champs complémentaires depuis la page de détail."""
        soup = BeautifulSoup(html, "lxml")

        # Exemple de sélecteurs pour S19 (à affiner après diagnostic)
        brand_el = soup.select_one(".product-brand")
        category_el = soup.select_one(".product-category")

        return {
            "brand": brand_el.get_text(strip=True) if brand_el else None,
            "category": category_el.get_text(strip=True) if category_el else None,
        }
