"""Export -- ecriture JSONL incrementale.

Le JSONL est retenu parce qu'il repond a trois besoins de cette collecte :

  1. l'ecriture est incrementale : chaque objet valide est ecrit des qu'il est
     produit. Une collecte interrompue a la page 4 laisse un fichier exploitable,
     la ou un `json.dump` d'une liste complete en fin de course ne laisse rien ;
  2. une ligne = un objet = un enregistrement independant. Un objet illisible
     n'empeche pas de lire les autres ;
  3. le format se relit ligne a ligne sans charger le fichier entier.

Le prix a payer est assume : ce n'est pas un JSON valide dans son ensemble.
D'ou `ecrire_echantillon_json`, qui produit en plus un vrai tableau JSON pour
l'echantillon de 5 a 10 objets exige par l'enonce.

L'encodage est UTF-8 sans echappement (`ensure_ascii=False`) : un nom propre
accentue reste lisible a l'oeil dans le fichier produit.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import TracebackType
from typing import Any

from .journal import LOGGER


def _encoder(valeur: Any) -> Any:
    """Serialise les types que `json` ne connait pas, sans perte silencieuse.

    Le prix est un `Decimal` et non un `float` : 19.99 n'a pas de representation
    binaire exacte, et un prix qui derive au centieme dans un fichier de sortie
    est un defaut de qualite, pas un detail d'affichage. On le serialise donc en
    chaine, ce qui preserve les decimales telles que la page les affichait.
    """
    if isinstance(valeur, Decimal):
        return str(valeur)
    if isinstance(valeur, datetime | date):
        return valeur.isoformat()
    if isinstance(valeur, Path):
        return str(valeur)
    if isinstance(valeur, set | frozenset):
        return sorted(valeur)
    if hasattr(valeur, "model_dump"):  # modele Pydantic
        return valeur.model_dump(mode="json")
    raise TypeError(f"Type non serialisable en JSON : {type(valeur).__name__}")


def _en_dictionnaire(objet: Any) -> dict[str, Any]:
    if isinstance(objet, Mapping):
        return dict(objet)
    if hasattr(objet, "model_dump"):
        return objet.model_dump(mode="json")
    raise TypeError(
        f"Objet non exportable : {type(objet).__name__}. "
        "Attendu : un modele Pydantic ou un dictionnaire."
    )


class EcrivainJSONL:
    """Ecrit des objets en JSON Lines, un objet par ligne, au fil de l'eau.

    S'utilise comme gestionnaire de contexte :

        with EcrivainJSONL(Path("data/sortie.jsonl")) as sortie:
            for objet in objets:
                sortie.ecrire(objet)

    Le fichier est ouvert en ecriture (`w`) : une nouvelle collecte remplace la
    precedente. C'est voulu -- un fichier de sortie qui accumule silencieusement
    les objets de trois executions successives est un piege a doublons.
    Pour ajouter a un fichier existant, passer `ajouter=True` explicitement.
    """

    def __init__(self, chemin: Path | str, *, ajouter: bool = False) -> None:
        self.chemin = Path(chemin)
        self._mode = "a" if ajouter else "w"
        self._fichier = None
        self.lignes = 0

    def __enter__(self) -> EcrivainJSONL:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        # newline="\n" : sans cela, Python traduit \n en \r\n sous Windows et le
        # fichier produit differe selon la machine qui l'a genere.
        self._fichier = self.chemin.open(self._mode, encoding="utf-8", newline="\n")
        return self

    def __exit__(
        self,
        type_exc: type[BaseException] | None,
        valeur_exc: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        if self._fichier is not None:
            self._fichier.close()
            self._fichier = None
        if type_exc is None:
            LOGGER.info("Export JSONL : %d objets -> %s", self.lignes, self.chemin)
        else:
            # Une collecte interrompue laisse quand meme ses lignes deja ecrites.
            LOGGER.warning(
                "Export JSONL interrompu apres %d objets -> %s", self.lignes, self.chemin
            )

    def ecrire(self, objet: Any) -> None:
        """Ecrit un objet sur une ligne, et vide le tampon immediatement.

        Le `flush` par objet coute une syscall ; il garantit qu'un Ctrl-C ou une
        coupure ne perd pas les dernieres lignes. Sur une collecte ralentie a une
        requete par seconde, ce cout est invisible.
        """
        if self._fichier is None:
            raise RuntimeError("EcrivainJSONL utilise hors de son gestionnaire de contexte.")
        ligne = json.dumps(
            _en_dictionnaire(objet),
            ensure_ascii=False,
            default=_encoder,
            sort_keys=True,  # ordre stable : deux executions produisent le meme diff
        )
        self._fichier.write(ligne + "\n")
        self._fichier.flush()
        self.lignes += 1

    def ecrire_tous(self, objets: Iterable[Any]) -> int:
        for objet in objets:
            self.ecrire(objet)
        return self.lignes


def ecrire_jsonl(chemin: Path | str, objets: Iterable[Any], *, ajouter: bool = False) -> int:
    """Raccourci pour un lot deja constitue en memoire."""
    with EcrivainJSONL(chemin, ajouter=ajouter) as sortie:
        return sortie.ecrire_tous(objets)


def lire_jsonl(chemin: Path | str) -> list[dict[str, Any]]:
    """Relit un fichier JSONL. Sert aux tests et a l'inspection de la sortie.

    Une ligne illisible est signalee avec son numero et ignoree : c'est
    precisement l'interet du format de ne pas perdre le fichier entier pour une
    ligne corrompue.
    """
    objets: list[dict[str, Any]] = []
    with Path(chemin).open(encoding="utf-8") as fichier:
        for numero, ligne in enumerate(fichier, start=1):
            ligne = ligne.strip()
            if not ligne:
                continue
            try:
                objets.append(json.loads(ligne))
            except json.JSONDecodeError as erreur:
                LOGGER.error("Ligne %d illisible dans %s : %s", numero, chemin, erreur)
    return objets


def ecrire_echantillon_json(chemin: Path | str, objets: Iterable[Any], *, limite: int = 10) -> int:
    """Ecrit un vrai tableau JSON de `limite` objets au maximum.

    L'enonce demande « un echantillon de sortie de 5 a 10 objets maximum dans le
    depot ». Un tableau JSON indente se relit d'un coup d'oeil dans l'interface
    de GitHub, ce que ne fait pas une ligne JSONL de 400 caracteres.
    """
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    retenus = [_en_dictionnaire(objet) for objet in list(objets)[:limite]]
    chemin.write_text(
        json.dumps(retenus, ensure_ascii=False, default=_encoder, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    LOGGER.info("Echantillon : %d objets -> %s", len(retenus), chemin)
    return len(retenus)
