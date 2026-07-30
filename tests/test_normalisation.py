"""CONTROLE 2 -- une normalisation (prix, date ou unite).

Ces tests portent sur mon code, pas sur le fonctionnement d'une bibliotheque :
c'est la condition posee par l'enonce pour qu'un controle compte.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from collecteur.normalisation import (
    detecter_devise,
    normaliser_prix,
    normaliser_texte,
    normaliser_url,
)


class TestNormaliserPrix:
    @pytest.mark.parametrize(
        ("brut", "attendu"),
        [
            ("129.90", Decimal("129.90")),
            ("129,90 €", Decimal("129.90")),
            ("$1,299.00", Decimal("1299.00")),
            ("1\u202f299,50 EUR", Decimal("1299.50")),
            ("Rs. 500", Decimal("500")),
            ("  42  ", Decimal("42")),
            # Espace insecable, tel que le produisent beaucoup de sites francais.
            ("1\u00a0234,56 €", Decimal("1234.56")),
            # Un separateur suivi de trois chiffres est un separateur de milliers.
            ("2,500", Decimal("2500")),
        ],
    )
    def test_montants_reconnus(self, brut: str, attendu: Decimal) -> None:
        assert normaliser_prix(brut) == attendu

    @pytest.mark.parametrize("brut", [None, "", "   ", "Prix sur demande", "N/A"])
    def test_absence_de_montant_donne_none(self, brut: str | None) -> None:
        """Aucun montant lisible ne devient JAMAIS 0.

        C'est le point important du controle : `None` (pas de prix affiche) et
        `Decimal("0")` (gratuit) sont deux informations differentes, et les
        confondre fausserait toute agregation faite en aval.
        """
        assert normaliser_prix(brut) is None

    def test_le_type_est_decimal_pas_float(self) -> None:
        resultat = normaliser_prix("19,99 €")
        assert isinstance(resultat, Decimal)
        # La verification qui justifie le choix : en float, cette egalite est fausse.
        assert resultat * 3 == Decimal("59.97")


class TestDetecterDevise:
    @pytest.mark.parametrize(
        ("brut", "attendu"),
        [("129,90 €", "EUR"), ("$42", "USD"), ("£10", "GBP"), ("Rs. 500", "INR")],
    )
    def test_symboles_courants(self, brut: str, attendu: str) -> None:
        assert detecter_devise(brut) == attendu

    def test_sans_symbole_renvoie_le_defaut(self) -> None:
        assert detecter_devise("129.90", defaut="EUR") == "EUR"
        assert detecter_devise("129.90") is None


class TestNormaliserTexte:
    def test_reduit_les_blancs_du_html(self) -> None:
        assert normaliser_texte("  Clavier\n\t  mecanique  ") == "Clavier mecanique"

    def test_remplace_les_espaces_insecables(self) -> None:
        assert normaliser_texte("Prix\u00a0: 42") == "Prix : 42"

    def test_normalise_les_accents_composes(self) -> None:
        """« e » + accent combinant et « e accent precompose » doivent comparer egaux.

        Sans NFC, ces deux chaines produisent deux cles de deduplication
        differentes pour le meme objet : le doublon passe inapercu.
        """
        compose = "Pérou"  # e + U+0301
        precompose = "Pérou"  # e accent aigu
        assert compose != precompose
        assert normaliser_texte(compose) == normaliser_texte(precompose)

    def test_chaine_vide_devient_none(self) -> None:
        assert normaliser_texte("   ") is None
        assert normaliser_texte("   ", vide_en_none=False) == ""


class TestNormaliserUrl:
    def test_resout_une_url_relative(self) -> None:
        assert (
            normaliser_url("/produit/12", "https://exemple.org/liste?page=2")
            == "https://exemple.org/produit/12"
        )

    def test_retire_le_fragment(self) -> None:
        """Le fragment ne designe pas une autre ressource : le garder cree des doublons."""
        assert (
            normaliser_url("https://exemple.org/p/1#avis", "https://exemple.org/")
            == "https://exemple.org/p/1"
        )

    def test_conserve_la_chaine_de_requete(self) -> None:
        assert (
            normaliser_url("?page=3", "https://exemple.org/liste")
            == "https://exemple.org/liste?page=3"
        )

    def test_rejette_les_schemas_non_http(self) -> None:
        assert normaliser_url("javascript:void(0)", "https://exemple.org/") is None
        assert normaliser_url("mailto:a@b.c", "https://exemple.org/") is None
