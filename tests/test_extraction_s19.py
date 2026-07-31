"""Controle : champs extraits des pages S19 enregistrees.

Ces tests ne touchent jamais le reseau. Ils rejouent deux pages reelles
d'Automation Exercise enregistrees telles quelles :

    tests/fixtures/page_liste.html       la page /products (34 produits)
    tests/fixtures/page_detail_s19.html  la fiche /product_details/1

C'est ce qui rend la verification rejouable par le formateur sans dependre de
l'etat du site le jour de la correction.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from collecteur import extraction_s19
from collecteur.extraction import ChampObligatoireAbsent
from collecteur.modele import Product

FIXTURES = Path(__file__).parent / "fixtures"
URL_LISTE = "https://automationexercise.com/products"
URL_DETAIL = "https://automationexercise.com/product_details/1"


@pytest.fixture(scope="module")
def html_liste() -> str:
    return (FIXTURES / "page_liste.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def html_detail() -> str:
    return (FIXTURES / "page_detail_s19.html").read_text(encoding="utf-8")


def test_liste_compte_34_produits(html_liste: str) -> None:
    """34 produits, pas 68.

    Chaque produit figure deux fois dans le HTML : une fois dans `.productinfo`
    et une fois dans `.product-overlay` affiche au survol. Un selecteur pose sur
    `[data-product-id]` en compte donc 68. Ce test verrouille le fait qu'on
    n'en collecte que 34, faute de quoi chaque produit serait telecharge et
    exporte en double.
    """
    produits = extraction_s19.extraire_liste(html_liste, URL_LISTE)
    assert len(produits) == 34


def test_liste_identifiants_uniques(html_liste: str) -> None:
    produits = extraction_s19.extraire_liste(html_liste, URL_LISTE)
    identifiants = [produit["item_id"] for produit in produits]
    assert len(set(identifiants)) == len(identifiants)


def test_liste_premier_produit(html_liste: str) -> None:
    premier = extraction_s19.extraire_liste(html_liste, URL_LISTE)[0]
    assert premier["item_id"] == "1"
    assert premier["name"] == "Blue Top"
    assert premier["prix_affiche"] == "Rs. 500"
    assert premier["url"] == URL_DETAIL


def test_liste_urls_absolues(html_liste: str) -> None:
    """Le site n'ecrit que des chemins relatifs (« /product_details/1 »).

    C'est precisement ce qui faisait echouer la validation du modele dans la
    version initiale : `source_url` recevait « /product_details/1 », que
    Pydantic refuse (« relative URL without a base »). La resolution appartient
    a l'extraction, qui seule connait l'URL de la page lue.
    """
    for produit in extraction_s19.extraire_liste(html_liste, URL_LISTE):
        assert produit["url"].startswith("https://automationexercise.com/product_details/")


def test_detail_porte_categorie_et_marque(html_detail: str) -> None:
    """Categorie et marque sont deux des six champs minimaux de la fiche S19.

    Elles ne figurent PAS sur la page de liste : seul le detail les porte.
    C'est la raison d'etre de la seconde requete par produit.
    """
    detail = extraction_s19.extraire_detail(html_detail, URL_DETAIL)
    assert detail["category"] == "Women > Tops"
    assert detail["brand"] == "Polo"


def test_detail_champs_complets(html_detail: str) -> None:
    detail = extraction_s19.extraire_detail(html_detail, URL_DETAIL)
    assert detail["item_id"] == "1"
    assert detail["name"] == "Blue Top"
    assert detail["prix_affiche"] == "Rs. 500"


def test_detail_page_sans_ancrage_leve_une_erreur() -> None:
    """Une structure disparue doit etre bruyante, jamais silencieuse."""
    with pytest.raises(ChampObligatoireAbsent) as capture:
        extraction_s19.extraire_detail("<html><body>rien</body></html>", URL_DETAIL)
    assert capture.value.url == URL_DETAIL


def test_detail_sans_nom_leve_une_erreur() -> None:
    html = '<div class="product-information"><p>Category: X</p></div>'
    with pytest.raises(ChampObligatoireAbsent) as capture:
        extraction_s19.extraire_detail(html, URL_DETAIL)
    assert capture.value.champ == "name"


def test_liens_de_listes_couvrent_categories_et_marques(html_liste: str) -> None:
    """La fiche de cible exige de couvrir categories et marques.

    Le site ne pagine pas /products : les 34 produits tiennent sur une page. Ce
    sont les 7 categories et les 8 marques qui donnent acces au reste du
    catalogue, et qui tiennent donc lieu de pagination.
    """
    liens = extraction_s19.extraire_liens_listes(html_liste, URL_LISTE)
    categories = [lien for lien in liens if "/category_products/" in lien]
    marques = [lien for lien in liens if "/brand_products/" in lien]
    assert len(categories) == 7
    assert len(marques) == 8
    assert len(liens) == len(set(liens))


def test_produit_valide_depuis_le_detail(html_detail: str) -> None:
    """Bout en bout hors reseau : HTML enregistre -> objet metier valide."""
    detail = extraction_s19.extraire_detail(html_detail, URL_DETAIL)
    produit = Product.depuis_brut(detail, URL_DETAIL)

    assert produit.name == "Blue Top"
    assert produit.price == Decimal("500")
    assert produit.currency == "INR"
    assert produit.category == "Women > Tops"
    assert produit.brand == "Polo"
    assert str(produit.url) == URL_DETAIL
    assert produit.scraped_at.tzinfo is not None


def test_prix_est_un_decimal_pas_un_flottant(html_detail: str) -> None:
    """`Decimal` et non `float` : un prix qui derive au centieme est un defaut."""
    produit = Product.depuis_brut(
        extraction_s19.extraire_detail(html_detail, URL_DETAIL), URL_DETAIL
    )
    assert isinstance(produit.price, Decimal)


def test_cle_dedup_est_l_identifiant_du_site(html_detail: str) -> None:
    """La cle vient de la page, pas de l'URL.

    `data-product-id` sur la liste et `input#product_id` sur la fiche portent la
    meme valeur. C'est ce qui permet de reconnaitre un produit deja vu AVANT de
    demander sa fiche, donc de ne pas payer deux requetes pour un produit
    atteint par sa categorie puis par sa marque.
    """
    produit = Product.depuis_brut(
        extraction_s19.extraire_detail(html_detail, URL_DETAIL), URL_DETAIL
    )
    assert produit.cle_dedup == "1"


class TestReplisDeResilience:
    """Replis issus de l'implementation d'Amine Kaoutar.

    Les selecteurs decrivent la page d'aujourd'hui. Ces replis couvrent le cas
    ou le site changerait la balise sans changer ce qu'il affiche -- mode de
    panne particulierement couteux ici, parce que ni le prix ni la marque ne
    sont des champs obligatoires : leur disparition ne leve aucune erreur et se
    lirait seulement dans les donnees, une fois la collecte terminee.
    """

    def test_prix_lu_meme_si_la_balise_change(self) -> None:
        """Le <h2> devenu <span> : le prix reste lisible."""
        html = (
            '<div class="product-image-wrapper"><div class="productinfo">'
            '<span class="tarif">Rs. 750</span><p>Chemise</p>'
            '<a href="/product_details/42" data-product-id="42">Voir</a>'
            "</div></div>"
        )
        produit = extraction_s19.extraire_liste(html, URL_LISTE)[0]
        assert produit["prix_affiche"] == "Rs. 750"
        assert Product.depuis_brut(produit, URL_LISTE).price == Decimal("750")

    def test_selecteur_prioritaire_sur_le_repli(self, html_liste: str) -> None:
        """Le repli ne doit pas prendre la main quand le selecteur repond.

        Sans cette garantie, le repli pourrait capter un prix barre ou un prix
        promotionnel voisin au lieu du prix affiche.
        """
        produits = extraction_s19.extraire_liste(html_liste, URL_LISTE)
        assert produits[0]["prix_affiche"] == "Rs. 500"
        assert sum(1 for p in produits if p["prix_affiche"]) == 34

    def test_marque_lue_meme_sans_balise_gras(self) -> None:
        """« Brand: » hors d'un <b> : la marque reste lisible."""
        html = (
            '<div class="product-information"><h2>Chemise</h2>'
            "<p>Category: Men > Tshirts</p>"
            "<p>Brand: Allen Solly</p>"
            '<input id="product_id" value="42">'
            "</div>"
        )
        detail = extraction_s19.extraire_detail(html, URL_DETAIL)
        assert detail["brand"] == "Allen Solly"
        assert detail["category"] == "Men > Tshirts"

    def test_le_repli_ne_deborde_pas_sur_le_libelle_suivant(self) -> None:
        """« Brand: Polo » ne doit pas avaler « Availability: In Stock ».

        Les champs se suivent dans le meme bloc ; un repli trop gourmand
        produirait une marque « Polo Availability » qui casserait la
        deduplication et les regroupements par marque.
        """
        html = (
            '<div class="product-information"><h2>Chemise</h2>'
            "<p>Brand: Polo Availability: In Stock Condition: New</p>"
            '<input id="product_id" value="42">'
            "</div>"
        )
        detail = extraction_s19.extraire_detail(html, URL_DETAIL)
        assert detail["brand"] == "Polo"

    def test_la_page_reelle_passe_toujours_par_le_chemin_precis(self, html_detail: str) -> None:
        """Sur la page d'aujourd'hui, c'est bien le <b> qui repond, pas le repli."""
        detail = extraction_s19.extraire_detail(html_detail, URL_DETAIL)
        assert detail["brand"] == "Polo"
        assert detail["category"] == "Women > Tops"


def test_liste_et_detail_donnent_le_meme_identifiant(html_liste: str, html_detail: str) -> None:
    premier = extraction_s19.extraire_liste(html_liste, URL_LISTE)[0]
    detail = extraction_s19.extraire_detail(html_detail, URL_DETAIL)
    assert premier["item_id"] == detail["item_id"]
