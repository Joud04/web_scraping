"""CONTROLE 3 -- deduplication, et rejet d'un objet incomplet."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from collecteur.modele import ObjetCollecte, Rejet
from collecteur.normalisation import Deduplicateur, normaliser_texte


class TestDeduplicateur:
    def test_premier_passage_accepte(self) -> None:
        dedup = Deduplicateur()
        assert dedup.est_nouveau("CS-1001") is True
        assert dedup.doublons == 0

    def test_deuxieme_passage_refuse_et_compte(self) -> None:
        dedup = Deduplicateur()
        dedup.est_nouveau("CS-1001")
        assert dedup.est_nouveau("CS-1001") is False
        assert dedup.doublons == 1
        assert len(dedup) == 1

    def test_cles_distinctes_ne_se_confondent_pas(self) -> None:
        dedup = Deduplicateur()
        for cle in ("A", "B", "C"):
            assert dedup.est_nouveau(cle) is True
        assert dedup.doublons == 0
        assert len(dedup) == 3

    def test_dedoublonne_apres_normalisation_du_texte(self) -> None:
        """Cas reel : le meme nom ecrit avec deux encodages Unicode differents.

        Sans passer les cles par `normaliser_texte`, ces deux objets seraient
        comptes comme distincts. C'est le cas qui a motive la normalisation NFC.
        """
        dedup = Deduplicateur()
        assert dedup.est_nouveau(normaliser_texte("Pérou")) is True
        assert dedup.est_nouveau(normaliser_texte("Pérou")) is False
        assert dedup.doublons == 1


class TestRejetObjetIncomplet:
    """Un objet auquel il manque un champ obligatoire ne doit PAS etre exporte."""

    def test_objet_complet_accepte(self) -> None:
        objet = ObjetCollecte(item_id="CS-1001", source_url="https://exemple.org/p/1")
        assert objet.cle_dedup == "CS-1001"
        assert objet.scraped_at.tzinfo is not None

    def test_identifiant_vide_rejete(self) -> None:
        with pytest.raises(ValidationError) as erreur:
            ObjetCollecte(item_id="", source_url="https://exemple.org/p/1")
        assert "item_id" in str(erreur.value)

    def test_identifiant_absent_rejete(self) -> None:
        with pytest.raises(ValidationError):
            ObjetCollecte(source_url="https://exemple.org/p/1")

    def test_url_non_absolue_rejetee(self) -> None:
        with pytest.raises(ValidationError):
            ObjetCollecte(item_id="CS-1001", source_url="/p/1")

    def test_horodatage_sans_fuseau_rejete(self) -> None:
        """L'enonce demande le fuseau. Une date naive est refusee a l'entree.

        La refuser ici plutot que de la corriger en silence evite d'inventer un
        fuseau que la donnee ne portait pas.
        """
        with pytest.raises(ValidationError):
            ObjetCollecte(
                item_id="CS-1001",
                source_url="https://exemple.org/p/1",
                scraped_at=datetime(2026, 7, 30, 14, 0),
            )

    def test_champ_inattendu_rejete(self) -> None:
        """Un champ que le modele ne connait pas signale un decalage d'extraction."""
        with pytest.raises(ValidationError):
            ObjetCollecte(
                item_id="CS-1001",
                source_url="https://exemple.org/p/1",
                prix_inattendu="42",
            )

    def test_le_rejet_conserve_son_motif(self) -> None:
        rejet = Rejet(
            source_url="https://exemple.org/p/1",
            motif="champ obligatoire absent",
            champ="price",
            brut={"name": "Clavier"},
        )
        assert rejet.champ == "price"
        assert rejet.horodatage.tzinfo == UTC
