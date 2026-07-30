import pytest
from automation_exercise.src.collecteur.extraction import Extraction
from automation_exercise.src.collecteur.normalisation import Normalisateur
from automation_exercise.src.collecteur.modele import Product

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

    assert p1.cle_dedup == p2.cle_dedup
