"""CONTROLE 1 -- extraction d'une fiche d'oeuvre enregistree.

Tout est rejoue sur la page reelle enregistree dans tests/fixtures/page_detail.html
(oeuvre 1915.534, « Nathaniel Hurd »). Aucun test ne touche le reseau.

La cible ne servant pas de page de liste (la recherche passe par /api, interdit
-- voir docs/fiche_descriptive.md), le « nombre d'objets attendu » se lit sur les
oeuvres voisines declarees par la fiche, pas sur une grille de resultats.
"""

from __future__ import annotations

import json

import pytest

from collecteur.extraction import (
    ChampObligatoireAbsent,
    analyser,
    extraire_detail,
    extraire_liens_lies,
)
from collecteur.modele import Artwork

URL = "https://www.clevelandart.org/art/1915.534"

# Compte sur la page enregistree : la fiche declare exactement cinq oeuvres
# voisines dans artworksForSeeAlso. Retirer une entree de la fixture fait chuter
# ce nombre -- le test le remarquerait.
VOISINES_ATTENDUES = 5


def _html_next_data(charge: dict) -> str:
    """Fabrique une page minimale portant un bloc __NEXT_DATA__ donne."""
    bloc = json.dumps(charge)
    script = f'<script id="__NEXT_DATA__" type="application/json">{bloc}</script>'
    return f"<html><body>{script}</body></html>"


def test_le_parseur_fonctionne_sur_du_html_malforme() -> None:
    """Une balise non fermee ne doit pas faire tomber le parsing : c'est la
    raison pour laquelle `lxml` est retenu plutot qu'un parseur strict."""
    soupe = analyser("<div><p>Titre<span>sans fermeture</div>")
    assert soupe.get_text(strip=True) == "Titresans fermeture"


def test_extraire_detail_rend_les_cinq_champs(page_detail: str) -> None:
    brut = extraire_detail(page_detail, URL)
    assert brut["item_id"] == "1915.534"
    assert brut["title"] == "Nathaniel Hurd"
    assert brut["date_text"] == "c. 1765"
    assert brut["medium"] == "oil on canvas"
    assert "Copley" in brut["artist"]
    assert brut["url"].endswith("/art/1915.534")


def test_detail_construit_une_oeuvre_valide(page_detail: str) -> None:
    """Le contrat complet : de la page a l'objet Pydantic valide et exportable."""
    oeuvre = Artwork.depuis_brut(extraire_detail(page_detail, URL), URL)
    assert oeuvre.item_id == "1915.534"
    assert oeuvre.cle_dedup == "1915.534"
    assert oeuvre.title == "Nathaniel Hurd"
    assert str(oeuvre.url).endswith("/art/1915.534")


def test_les_oeuvres_voisines_alimentent_le_front(page_detail: str) -> None:
    liens = extraire_liens_lies(page_detail, URL)
    assert len(liens) == VOISINES_ATTENDUES
    assert all("/art/" in lien for lien in liens)
    assert "https://www.clevelandart.org/art/1966.385" in liens


def test_oeuvre_anonyme_donne_un_artiste_absent() -> None:
    """absent != vide : une oeuvre sans createur declare doit produire artist=None,
    pas une chaine vide -- c'est une information, pas un ancrage rate."""
    html = _html_next_data({"props": {"pageProps": {"artworkData": {
        "accession_number": "0000.0",
        "title": "Sans titre",
        "creators": [],
        "url": "https://clevelandart.org/art/0000.0",
    }}}})
    oeuvre = Artwork.depuis_brut(extraire_detail(html, URL), URL)
    assert oeuvre.artist is None


def test_titre_absent_produit_une_erreur_bruyante() -> None:
    """L'exigence la plus explicite de l'enonce : un champ obligatoire introuvable
    leve, il ne produit pas un enregistrement a moitie vide."""
    html = _html_next_data({"props": {"pageProps": {"artworkData": {
        "accession_number": "1915.534",
    }}}})
    with pytest.raises(ChampObligatoireAbsent):
        extraire_detail(html, URL)


def test_bloc_de_donnees_absent_produit_une_erreur_bruyante() -> None:
    with pytest.raises(ChampObligatoireAbsent):
        extraire_detail("<html><body>page sans donnees</body></html>", URL)
