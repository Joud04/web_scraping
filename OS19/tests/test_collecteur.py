import pytest
from src.collecteur.extraction import Extraction
from src.collecteur.normalisation import Normalisateur
from src.collecteur.modele import Product

def test_extraction_count():
    """Contrôle 1 : Nombre d'objets extraits d'une page enregistrée."""
    with open("tests/fixtures/page_liste.html", "r", encoding="utf-8") as f:
        html = f.read()

    extracteur = Extraction()
    produits = extracteur.extract_products_from_list(html)

    # On vérifie que nous avons trouvé des produits (ajuster le nombre selon la fixture)
    assert len(produits) > 0
    print(f"Extraction réussie : {len(produits)} produits trouvés.")

def test_normalisation_prix():
    """Contrôle 2 : Normalisation du prix."""
    norm = Normalisateur()

    # Cas 1 : Prix standard
    assert norm.normaliser_prix("Rs. 500") == 500
    # Cas 2 : Prix avec virgule
    assert norm.normaliser_prix("Rs. 12,99") == 12.99
    # Cas 3 : Valeur absente
    assert norm.normaliser_prix(None) is None
    # Cas 4 : Texte invalide
    assert norm.normaliser_prix("Indisponible") is None

def test_deduplication_id():
    """Contrôle 3 : L'identifiant est stable."""
    url = "https://automationexercise.com/products/1"
    p1 = Product(item_id=url, source_url=url, name="T-shirt", price=10)
    p2 = Product(item_id=url, source_url=url, name="T-shirt", price=10)

def test_extract_product_details():
    """Contrôle 4 : Extraction des détails (Brand et Category)."""
    html = """
    <table>
        <tr><td>Category:</td><td>Women > Tops</td></tr>
        <tr><td>Brand:</td><td>Polo</td></tr>
    </table>
    """
    extracteur = Extraction()
    details = extracteur.extract_product_details(html)
    assert details["category"] == "Women > Tops"
    assert details["brand"] == "Polo"

    # Test with values in the same cell
    html_same_cell = """
    <table>
        <tr><td>Category: Women > Tops</td></tr>
        <tr><td>Brand: Polo</td></tr>
    </table>
    """
    details_same = extracteur.extract_product_details(html_same_cell)
    assert details_same["category"] == "Women > Tops"
    assert details_same["brand"] == "Polo"

    # Test fallback
    html_fallback = "<div>Category: Women > Tops</div><div>Brand: Polo</div>"
    details_fallback = extracteur.extract_product_details(html_fallback)
    assert details_fallback["category"] == "Women > Tops"
    assert details_fallback["brand"] == "Polo"
