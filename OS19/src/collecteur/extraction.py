from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import logging
import re

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
        """Extrait les champs complémentaires depuis la page de détail.
        
        Gère différentes structures HTML dynamiques:
        - <b>Brand:</b> H&M
        - Brand: H&M (même nœud texte)
        - <td>Brand:</td><td>H&M</td>
        """
        soup = BeautifulSoup(html, "lxml")
        details = {"brand": None, "category": None}

        def get_value_for_label(label_text):
            """Extrait la valeur qui suit un label, quel que soit le format HTML."""
            # Trouver tous les éléments contenant le label
            label_elements = soup.find_all(string=lambda t: t and label_text in t)
            if not label_elements:
                return None

            for label_el in label_elements:
                # Ignorer les labels dans les titres (sidebar Categories/Brands)
                if label_text == "Brand:" and label_el.parent and label_el.parent.name in ["h2", "h3"]:
                    continue

                # Stratégie 1: Le label et la valeur sont dans le même nœud texte
                # Format: "Brand: H&M"
                text_node = str(label_el).strip()
                if label_text in text_node:
                    pattern = re.escape(label_text) + r"\s*:?\s*(.+?)$"
                    match = re.search(pattern, text_node)
                    if match:
                        val = match.group(1).strip()
                        if val and len(val) < 100:
                            return val

                # Stratégie 2: Le label est dans un élément (ex: <b>Brand:</b>) et la valeur suit
                # Format: <b>Brand:</b> H&M
                parent = label_el.parent
                if parent:
                    # Chercher le prochain frère du parent (le label est dans un tag comme <b>)
                    # et la valeur est après ce tag
                    next_sibling = parent.next_sibling
                    while next_sibling:
                        if isinstance(next_sibling, str):
                            val = str(next_sibling).strip()
                            if val and len(val) < 100 and val not in [":", ""]:
                                return val
                        elif hasattr(next_sibling, 'get_text'):
                            text = next_sibling.get_text(strip=True)
                            if text and len(text) < 100:
                                first_line = text.split("\n")[0].strip()
                                if first_line:
                                    return first_line
                        # S'arrête après le premier élément non-vide
                        if next_sibling and not (isinstance(next_sibling, str) and next_sibling.strip() == ""):
                            break
                        next_sibling = next_sibling.next_sibling

                    # Stratégie 3: Valeur dans le frère suivant du parent
                    # Format: <td>Brand:</td><td>H&M</td>
                    parent_next = parent.find_next_sibling()
                    if parent_next:
                        val = parent_next.get_text(strip=True)
                        first_line = val.split("\n")[0].strip() if val else None
                        if first_line and len(first_line) < 100 and first_line != label_text:
                            return first_line

                    # Stratégie 4: Structure de tableau
                    td = parent.find_parent("td")
                    if td:
                        next_td = td.find_next_sibling("td")
                        if next_td:
                            val = next_td.get_text(strip=True)
                            first_line = val.split("\n")[0].strip() if val else None
                            if first_line and len(first_line) < 100:
                                return first_line

            return None

        details["category"] = get_value_for_label("Category:")
        details["brand"] = get_value_for_label("Brand:")

        # Nettoie les chaînes vides et décode les entités HTML
        for k, v in details.items():
            if v == "":
                details[k] = None
            elif v and isinstance(v, str):
                # Décoder les entités HTML (ex: H&amp;M -> H&M)
                from html import unescape
                details[k] = unescape(v)

        return details
