"""CONTROLE 2 -- une normalisation.

L'enonce demande un controle portant sur « une normalisation -- prix, date ou
unite ». Sur une cible d'oeuvres d'art, aucune des trois ne s'applique telle
quelle : il n'y a pas de prix, et les dates sont conservees en texte a dessein
(« c. 1765 », « fin du XVIIIe siecle » -- les forcer dans un type date
inventerait une precision que la source ne porte pas).

La normalisation qui compte reellement ici est celle du TEXTE et de l'URL. Ce
sont les deux endroits ou deux ecritures d'une meme valeur produiraient deux
cles differentes et feraient echouer la deduplication.

Ces tests portent sur le code du projet, pas sur le fonctionnement d'une
bibliotheque : c'est la condition posee par l'enonce pour qu'un controle compte.
"""

from __future__ import annotations

from collecteur.normalisation import (
    ESPACE_INSEC_FINE,
    ESPACE_INSECABLE,
    normaliser_texte,
    normaliser_url,
)


class TestNormaliserTexte:
    def test_reduit_les_blancs_du_html(self) -> None:
        """Le HTML indente produit des retours a la ligne au milieu des libelles."""
        assert normaliser_texte("  John Singleton\n\t  Copley  ") == "John Singleton Copley"

    def test_remplace_les_espaces_insecables(self) -> None:
        """`str.strip` ignore l'espace insecable : sans traitement, il survit
        en fin de chaine et deux titres identiques comparent faux."""
        assert normaliser_texte(f"Nathaniel Hurd{ESPACE_INSECABLE}") == "Nathaniel Hurd"
        assert normaliser_texte(f"c.{ESPACE_INSEC_FINE}1765") == "c. 1765"

    def test_retire_le_bom_rencontre_en_milieu_de_flux(self) -> None:
        assert normaliser_texte("﻿Pilgrim") == "Pilgrim"

    def test_normalise_les_accents_composes(self) -> None:
        """« e » + accent combinant et « e accent precompose » doivent comparer egaux.

        C'est le cas qui justifie la normalisation NFC : sans elle, ces deux
        chaines produisent deux cles de deduplication differentes pour le meme
        objet, et le doublon passe inapercu.
        """
        compose = "Rodin, Musée"  # e + U+0301
        precompose = "Rodin, Musée"  # e accent aigu
        assert compose != precompose
        assert normaliser_texte(compose) == normaliser_texte(precompose)

    def test_chaine_vide_devient_none(self) -> None:
        """absent != vide : la convention du modele commence ici."""
        assert normaliser_texte("   ") is None
        assert normaliser_texte("   ", vide_en_none=False) == ""

    def test_none_reste_none(self) -> None:
        assert normaliser_texte(None) is None


class TestNormaliserUrl:
    def test_resout_une_url_relative(self) -> None:
        assert (
            normaliser_url("/art/1915.534", "https://www.clevelandart.org/art/collection/search")
            == "https://www.clevelandart.org/art/1915.534"
        )

    def test_retire_le_fragment(self) -> None:
        """Le fragment ne designe pas une autre ressource : le garder ferait
        visiter deux fois la meme fiche et gonflerait le compteur de doublons."""
        assert (
            normaliser_url(
                "https://www.clevelandart.org/art/1915.534#provenance",
                "https://www.clevelandart.org/",
            )
            == "https://www.clevelandart.org/art/1915.534"
        )

    def test_conserve_la_chaine_de_requete(self) -> None:
        """Contrairement au fragment, la chaine de requete change la ressource."""
        assert (
            normaliser_url("?page=3", "https://www.clevelandart.org/art/collection/search")
            == "https://www.clevelandart.org/art/collection/search?page=3"
        )

    def test_rejette_les_schemas_non_http(self) -> None:
        """Un `href` de navigation interne ne doit jamais entrer dans le front
        de collecte : il n'y a rien a y demander."""
        assert normaliser_url("javascript:void(0)", "https://www.clevelandart.org/") is None
        assert (
            normaliser_url("mailto:info@clevelandart.org", "https://www.clevelandart.org/") is None
        )

    def test_none_reste_none(self) -> None:
        assert normaliser_url(None, "https://www.clevelandart.org/") is None
