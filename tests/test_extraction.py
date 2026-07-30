"""CONTROLE 1 -- nombre d'objets extraits d'une page enregistree.

Ce fichier reste en attente tant que la cible n'est pas attribuee : le nombre
attendu ne peut pas etre invente, il se compte sur la page reelle.

Marche a suivre une fois la cible connue :

    1. enregistrer la page de liste, SANS la modifier :
         python -m collecteur diagnostic --url <URL>     (pour verifier l'acces)
         curl -sS "<URL>" -o tests/fixtures/page_liste.html
    2. compter les objets a la main sur cette page enregistree ;
    3. remplacer NOMBRE_ATTENDU par ce nombre, et retirer le skip ;
    4. verifier que le test echoue si l'on retire un objet de la fixture --
       un test qui passe quoi qu'il arrive ne prouve rien.
"""

from __future__ import annotations

import pytest

from collecteur.extraction import ChampObligatoireAbsent, analyser

# A renseigner apres avoir compte les objets sur la page enregistree.
NOMBRE_ATTENDU: int | None = None

besoin_de_cible = pytest.mark.skipif(
    NOMBRE_ATTENDU is None,
    reason="Cible non attribuee : renseigner NOMBRE_ATTENDU et implementer extraction.py.",
)


def test_le_parseur_fonctionne_sur_du_html_malforme() -> None:
    """Seul test executable sans cible : il porte sur le choix de `lxml`.

    Une balise non fermee ne doit pas faire tomber le parsing. C'est la raison
    pour laquelle `lxml` est retenu plutot qu'un parseur strict, et cette raison
    doit etre verifiable, pas seulement affirmee dans le rapport.
    """
    soupe = analyser("<div><p>Titre<span>sans fermeture</div>")
    assert soupe.get_text(strip=True) == "Titresans fermeture"


@besoin_de_cible
def test_nombre_d_objets_extraits(page_liste: str) -> None:
    from collecteur.extraction import extraire_liste

    objets = extraire_liste(page_liste, "https://exemple.invalid/")
    assert len(objets) == NOMBRE_ATTENDU


@besoin_de_cible
def test_chaque_objet_porte_les_champs_minimaux(page_liste: str) -> None:
    from collecteur.extraction import extraire_liste

    # A remplacer par les champs minimaux exacts de la fiche de cible.
    champs_minimaux: set[str] = set()
    for objet in extraire_liste(page_liste, "https://exemple.invalid/"):
        assert champs_minimaux <= set(objet), f"champs absents : {champs_minimaux - set(objet)}"


@besoin_de_cible
def test_ancrage_disparu_produit_une_erreur_bruyante() -> None:
    """L'exigence la plus explicite de l'enonce sur les selecteurs.

    « Un champ obligatoire qui devient introuvable doit produire un signal
    visible, pas un enregistrement silencieusement incomplet. »

    On le verifie en retirant l'ancrage de la fixture : le code doit lever, pas
    renvoyer un objet a moitie vide.
    """
    from collecteur.extraction import extraire_liste

    html_sans_ancrage = "<html><body><div class='vide'></div></body></html>"
    with pytest.raises(ChampObligatoireAbsent):
        extraire_liste(html_sans_ancrage, "https://exemple.invalid/")
