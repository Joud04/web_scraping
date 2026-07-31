"""Controle : conversion des prix et deduction de la devise.

Ces regles avaient ete retirees du projet quand le site 1 (S32, oeuvres d'art)
s'est revele n'avoir aucun prix a traiter. Le site 2 (S19, catalogue produit)
les rend a nouveau necessaires : `price` et `currency` sont deux des six champs
minimaux de sa fiche de cible.

Elles sont testees ici sans HTML et sans reseau, ce qui est precisement l'objet
de la separation entre extraction (ou lire) et normalisation (comment
interpreter).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from collecteur.normalisation import ESPACE_INSECABLE, detecter_devise, normaliser_prix


@pytest.mark.parametrize(
    ("affiche", "attendu"),
    [
        ("Rs. 500", Decimal("500")),
        ("Rs. 1500", Decimal("1500")),
        ("500", Decimal("500")),
        ("12.99", Decimal("12.99")),
        ("12,99", Decimal("12.99")),
        ("1 299", Decimal("1299")),
        ("1,299", Decimal("1299")),
        ("1.299", Decimal("1299")),
        ("1 299,50", Decimal("1299.50")),
        ("0", Decimal("0")),
    ],
)
def test_prix_reconnus(affiche: str, attendu: Decimal) -> None:
    assert normaliser_prix(affiche) == attendu


@pytest.mark.parametrize(
    ("affiche", "attendu"),
    [
        ("Rs. 1000", Decimal("1000")),
        ("Rs. 1500", Decimal("1500")),
        ("1500", Decimal("1500")),
        ("15000", Decimal("15000")),
        ("1500.75", Decimal("1500.75")),
    ],
)
def test_nombre_long_sans_separateur(affiche: str, attendu: Decimal) -> None:
    """Regression : « 1500 » ne doit pas etre tronque en 150.

    Le motif essayait d'abord la forme a separateurs de milliers, dont la tete
    `\\d{1,3}` capturait « 150 » ; faute de groupe suivant, elle rendait 150 et
    les chiffres restants etaient perdus sans erreur. La forme a separateurs
    exige desormais au moins un groupe de trois chiffres et refuse d'etre suivie
    d'un chiffre, ce qui renvoie ces nombres vers la forme simple.

    Le cas est frequent sur S19, dont plusieurs articles depassent 999 roupies.
    """
    assert normaliser_prix(affiche) == attendu


def test_prix_avec_espace_insecable() -> None:
    """« 1 299 » sur un site francais porte souvent une espace insecable.

    `str.strip` ne la voit pas et la comparaison de textes echoue en silence.
    Le caractere est ecrit par sa constante nommee plutot qu'en litteral : a
    l'oeil il est indiscernable d'une espace ordinaire, et un relecteur de
    bonne foi le « corrigerait » en cassant ce test.
    """
    assert normaliser_prix(f"1{ESPACE_INSECABLE}299") == Decimal("1299")


@pytest.mark.parametrize("entree", [None, "", "   ", "Indisponible", "Sur devis"])
def test_prix_illisible_devient_none(entree: str | None) -> None:
    """Aucune valeur inventee : ce qui ne se lit pas vaut None, pas zero.

    Un prix absent traduit en 0 ferait passer un article non tarife pour un
    article gratuit, et fausserait toute moyenne calculee ensuite.
    """
    assert normaliser_prix(entree) is None


def test_zero_n_est_pas_absent() -> None:
    """0 et None sont deux informations differentes, comme l'exige le rapport."""
    assert normaliser_prix("0") == Decimal("0")
    assert normaliser_prix("0") is not None


@pytest.mark.parametrize(
    ("affiche", "attendu"),
    [
        ("Rs. 500", "INR"),
        ("Rs 500", "INR"),
        ("₹500", "INR"),
        ("12,99 €", "EUR"),
        ("$19.99", "USD"),
        ("US$ 19.99", "USD"),
        ("£10", "GBP"),
    ],
)
def test_devises_reconnues(affiche: str, attendu: str) -> None:
    assert detecter_devise(affiche) == attendu


def test_symbole_le_plus_long_gagne() -> None:
    """« us$ » doit l'emporter sur « $ », sans quoi USD serait devine au hasard."""
    assert detecter_devise("US$ 19.99") == "USD"


def test_texte_sans_symbole_ne_devine_pas_de_devise() -> None:
    """Regression : un « r » isole ne doit pas etiqueter le prix en rand.

    La table des devises comportait « r » -> ZAR. Comme la recherche se fait par
    inclusion dans le texte en minuscules, tout prix accompagne d'un mot
    contenant un « r » -- « Prix », « Price », « From » -- etait etiquette ZAR.
    Les symboles d'une seule lettre ont donc ete retires de la table.
    """
    assert detecter_devise("Prix 12,50") is None
    assert detecter_devise("Price 12.50") is None
    assert detecter_devise("From 40") is None


def test_devise_par_defaut_est_explicite() -> None:
    """Une devise qui ne vient pas de la page est une hypothese, elle se declare."""
    assert detecter_devise("500", defaut="INR") == "INR"
    assert detecter_devise(None, defaut="INR") == "INR"
    assert detecter_devise("500") is None
