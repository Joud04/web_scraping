"""Configuration -- separee du code, comme l'exige la grille.

Priorite, du plus fort au plus faible :

    1. arguments de ligne de commande
    2. fichier config.toml
    3. valeurs par defaut definies ici

Aucun secret n'est lu ici : la cible du TP est publique et ne demande aucune
authentification. Si une cible en demandait une, la regle de l'enonce est de
s'arreter, pas de stocker un identifiant.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class Cible:
    id: str = "S__"
    nom: str = ""
    url_depart: str = ""


@dataclass(frozen=True, slots=True)
class Collecte:
    max_objets: int = 20
    max_pages: int = 5
    delai_secondes: float = 1.0
    concurrence: int = 1
    suivre_detail: bool = True
    # Numeros d'accession servant de points d'entree au parcours. La recherche
    # du site passant par un chemin interdit (voir la fiche descriptive), le
    # front de collecte est amorce par ces graines puis etendu de proche en
    # proche. Elles vivent dans la configuration, pas dans le code.
    graines: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Http:
    user_agent: str = "TP-Scraping-Collecteur/0.1 (formation Semifir)"
    timeout_secondes: float = 20.0
    max_tentatives: int = 3
    backoff_max_secondes: float = 60.0


@dataclass(frozen=True, slots=True)
class Sortie:
    fichier_jsonl: Path = Path("data/sortie.jsonl")
    fichier_echantillon: Path = Path("samples/sample_output.jsonl")
    taille_echantillon: int = 10
    fichier_rejets: Path = Path("data/rejets.jsonl")


@dataclass(frozen=True, slots=True)
class Journal:
    niveau: str = "INFO"
    fichier: Path = Path("logs/collecte.log")


@dataclass(frozen=True, slots=True)
class Config:
    cible: Cible = field(default_factory=Cible)
    collecte: Collecte = field(default_factory=Collecte)
    http: Http = field(default_factory=Http)
    sortie: Sortie = field(default_factory=Sortie)
    journal: Journal = field(default_factory=Journal)

    def valider(self) -> None:
        """Rejette une configuration incoherente AVANT la premiere requete.

        Echouer ici coute une seconde ; echouer au milieu d'une collecte
        ralentie a une requete par seconde coute la collecte entiere.
        """
        erreurs: list[str] = []
        if not self.cible.url_depart:
            erreurs.append("cible.url_depart est vide")
        elif not self.cible.url_depart.startswith(("http://", "https://")):
            erreurs.append(
                f"cible.url_depart n'est pas une URL absolue : {self.cible.url_depart!r}"
            )
        if self.collecte.max_objets < 1:
            erreurs.append("collecte.max_objets doit valoir au moins 1")
        if self.collecte.delai_secondes < 0:
            erreurs.append("collecte.delai_secondes ne peut pas etre negatif")
        if self.collecte.concurrence < 1:
            erreurs.append("collecte.concurrence doit valoir au moins 1")
        if erreurs:
            raise ValueError("Configuration invalide :\n  - " + "\n  - ".join(erreurs))


_SECTIONS: dict[str, type] = {
    "cible": Cible,
    "collecte": Collecte,
    "http": Http,
    "sortie": Sortie,
    "journal": Journal,
}


def _construire_section(classe: type, brut: dict[str, Any]) -> Any:
    """Instancie une section en ignorant les cles inconnues, avec un avertissement.

    Une cle mal orthographiee dans config.toml est ainsi visible, au lieu de
    provoquer un TypeError opaque ou, pire, d'etre silencieusement perdue.
    """
    attendus = {f.name: f.type for f in fields(classe)}
    connus, inconnus = {}, []
    for cle, valeur in brut.items():
        if cle not in attendus:
            inconnus.append(cle)
            continue
        connus[cle] = Path(valeur) if attendus[cle] in ("Path", Path) else valeur
    if inconnus:
        raise ValueError(
            f"Cles inconnues dans la section [{classe.__name__.lower()}] : {', '.join(inconnus)}"
        )
    return classe(**connus)


def charger(chemin: Path | str | None = None, **surcharges: Any) -> Config:
    """Charge la configuration : fichier TOML puis surcharges de ligne de commande.

    `chemin` a None cherche config.toml a la racine du projet ; son absence
    n'est pas une erreur, les valeurs par defaut s'appliquent.

    Les `surcharges` utilisent la notation `section_champ`, par exemple
    `collecte_max_objets=5`, ce qui evite de faire remonter la structure
    imbriquee jusqu'a l'analyseur d'arguments.
    """
    chemin = Path(chemin) if chemin else RACINE / "config.toml"
    brut: dict[str, Any] = {}
    if chemin.exists():
        brut = tomllib.loads(chemin.read_text(encoding="utf-8"))

    sections = {
        nom: _construire_section(classe, brut.get(nom, {})) for nom, classe in _SECTIONS.items()
    }
    config = Config(**sections)

    for cle, valeur in surcharges.items():
        if valeur is None:
            continue
        nom_section, _, nom_champ = cle.partition("_")
        if nom_section not in sections:
            raise ValueError(f"Surcharge inconnue : {cle}")
        section = getattr(config, nom_section)
        if not any(f.name == nom_champ for f in fields(section)):
            raise ValueError(f"Surcharge inconnue : {cle}")
        config = replace(config, **{nom_section: replace(section, **{nom_champ: valeur})})
        sections[nom_section] = getattr(config, nom_section)

    return config
