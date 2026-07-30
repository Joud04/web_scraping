"""Journalisation et compteurs.

Deux besoins distincts, volontairement portes par le meme module :

  - des traces horodatees, lisibles pendant l'execution ;
  - des compteurs qui remplissent la rubrique 7 du rapport.

La notice du formateur est explicite : « Si vos traces d'execution ne donnent
pas ces compteurs, la vraie correction est d'ajouter les compteurs, pas
d'inventer les valeurs. » D'ou `Compteurs`, qui produit le tableau du rapport
et verifie que les nombres se raccordent.
"""

from __future__ import annotations

import logging
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

LOGGER = logging.getLogger("collecteur")


def configurer(niveau: str = "INFO", fichier: Path | None = None) -> logging.Logger:
    """Installe le format horodate sur la sortie standard, et sur un fichier."""
    LOGGER.handlers.clear()
    LOGGER.setLevel(getattr(logging, niveau.upper(), logging.INFO))
    LOGGER.propagate = False

    format_ = logging.Formatter(
        fmt="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(format_)
    LOGGER.addHandler(console)

    if fichier is not None:
        fichier.parent.mkdir(parents=True, exist_ok=True)
        disque = logging.FileHandler(fichier, encoding="utf-8")
        disque.setFormatter(format_)
        LOGGER.addHandler(disque)

    return LOGGER


@dataclass
class Compteurs:
    """Compteurs d'une execution, source unique du tableau de la rubrique 7."""

    pages: int = 0
    requetes: int = 0
    vus: int = 0
    exportes: int = 0
    rejetes: int = 0
    doublons: int = 0
    erreurs_reseau: int = 0
    # Detail des motifs de rejet, pour ne pas avoir a relire rejets.jsonl.
    motifs_rejet: Counter[str] = field(default_factory=Counter)
    # Detail des champs obligatoires absents, champ par champ.
    champs_manquants: Counter[str] = field(default_factory=Counter)

    def rejeter(self, motif: str, champ: str | None = None) -> None:
        self.rejetes += 1
        self.motifs_rejet[motif] += 1
        if champ:
            self.champs_manquants[champ] += 1

    @property
    def coherents(self) -> bool:
        """Vus doit se decomposer exactement en exportes + rejetes + doublons.

        Une somme fausse signale un chemin de code qui compte deux fois, ou pas
        du tout. Le rapport demande d'expliquer l'ecart plutot que de l'ajuster :
        encore faut-il le voir.
        """
        return self.vus == self.exportes + self.rejetes + self.doublons

    def resume(self) -> str:
        """Tableau pret a recopier dans la rubrique 7 du compte rendu."""
        lignes = [
            ("Pages ou requetes traitees", f"{self.pages} pages / {self.requetes} requetes"),
            ("Objets vus", str(self.vus)),
            ("Objets exportes", str(self.exportes)),
            ("Objets rejetes", str(self.rejetes)),
            ("Doublons detectes", str(self.doublons)),
            (
                "Champs obligatoires manquants",
                ", ".join(f"{c}={n}" for c, n in sorted(self.champs_manquants.items())) or "aucun",
            ),
            ("Erreurs reseau", str(self.erreurs_reseau)),
        ]
        largeur = max(len(cle) for cle, _ in lignes)
        corps = "\n".join(f"  {cle.ljust(largeur)} | {valeur}" for cle, valeur in lignes)
        if not self.coherents:
            corps += (
                f"\n  {'INCOHERENCE'.ljust(largeur)} | "
                f"vus={self.vus} != exportes+rejetes+doublons="
                f"{self.exportes + self.rejetes + self.doublons}"
            )
        return corps
