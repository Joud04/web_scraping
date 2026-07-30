"""Fixtures partagees.

Regle non negociable de ce dossier : AUCUN TEST NE FAIT DE REQUETE RESEAU.
L'enonce l'exige (« votre logique doit etre rejouable sans reseau ») et c'est
aussi la seule facon d'avoir une verification qui passe encore le jour ou la
cible est en panne, en maintenance, ou simplement modifiee.

Les tests lisent donc des pages enregistrees dans tests/fixtures/.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def dossier_fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def page_liste() -> str:
    """HTML d'une page de liste enregistree. A creer apres attribution de la cible."""
    chemin = FIXTURES / "page_liste.html"
    if not chemin.exists():
        pytest.skip("tests/fixtures/page_liste.html absent : cible non attribuee.")
    return chemin.read_text(encoding="utf-8")


@pytest.fixture
def page_detail() -> str:
    """HTML d'une page de detail enregistree. A creer apres attribution de la cible."""
    chemin = FIXTURES / "page_detail.html"
    if not chemin.exists():
        pytest.skip("tests/fixtures/page_detail.html absent : cible non attribuee.")
    return chemin.read_text(encoding="utf-8")
