"""Modele de donnees -- socle commun, independant de la cible.

`ObjetCollecte` porte les trois champs que l'enonce exige quelle que soit la
cible : un identifiant stable, l'URL source, et la date de collecte avec son
fuseau. L'objet metier concret (Product, Destination, Artwork, Book...) herite
de ce socle et ajoute les champs minimaux de la fiche de cible.

    ATTENDRE L'ATTRIBUTION DE LA CIBLE avant d'ecrire la classe concrete :
    les champs minimaux different d'une cible a l'autre, et un schema devine
    a l'avance est un schema qu'on justifie mal a l'oral.

Convention de valeur absente, tenue dans tout le projet :

    None   le champ n'existe pas sur la page. Information a part entiere.
    ""     le champ existe et la page le laisse vide.
    0      le champ existe et vaut zero.

Les trois sont distincts, et le rapport le demande explicitement. Un
`prix = None` (non affiche) et un `prix = 0` (gratuit) ne se confondent pas.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


def horodatage() -> datetime:
    """Date de collecte en UTC, toujours avec fuseau.

    `datetime.now()` sans fuseau produit une donnee inexploitable des qu'elle
    change de machine : rien n'indique si 14:00 est une heure de Paris ou de
    New York. L'enonce demande le fuseau, ce n'est pas une formalite.
    """
    return datetime.now(UTC)


class ObjetCollecte(BaseModel):
    """Socle de tout objet collecte. Ne s'instancie pas directement."""

    model_config = ConfigDict(
        # Un champ inattendu venant de l'extraction est une erreur, pas un extra
        # a conserver : il signale un decalage entre extraction et modele.
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    item_id: str = Field(
        ...,
        min_length=1,
        description="Identifiant stable. Regle de construction documentee dans le rapport.",
    )
    source_url: HttpUrl = Field(..., description="URL exacte de la page dont vient l'objet.")
    scraped_at: datetime = Field(
        default_factory=horodatage,
        description="Date et heure de collecte, avec fuseau.",
    )

    @field_validator("scraped_at")
    @classmethod
    def _exiger_fuseau(cls, valeur: datetime) -> datetime:
        if valeur.tzinfo is None:
            raise ValueError("scraped_at doit porter un fuseau horaire.")
        return valeur

    @property
    def cle_dedup(self) -> str:
        """Cle de deduplication. A redefinir si l'identifiant ne suffit pas.

        Par defaut, deux objets de meme `item_id` sont le meme objet. Sur une
        cible ou l'identifiant se reconstruit depuis l'URL, un changement de
        structure d'URL casserait cette regle : le rapport doit dire lequel des
        deux cas s'applique.
        """
        return self.item_id


class Rejet(BaseModel):
    """Objet ecarte, avec son motif. Ecrit dans data/rejets.jsonl.

    Un rejet n'est pas une erreur a masquer : c'est la trace qui permet de
    remplir la ligne « objets rejetes » du rapport et de la defendre.
    """

    model_config = ConfigDict(extra="forbid")

    source_url: str
    motif: str
    champ: str | None = None
    brut: dict[str, object] = Field(default_factory=dict)
    horodatage: datetime = Field(default_factory=horodatage)
