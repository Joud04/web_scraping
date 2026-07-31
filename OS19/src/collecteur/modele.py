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
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


def horodatage() -> datetime:
    """Date de collecte en UTC, toujours avec fuseau."""
    return datetime.now(UTC)


class ObjetCollecte(BaseModel):
    """Socle de tout objet collecte. Ne s'instancie pas directement."""

    model_config = ConfigDict(
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
        return self.item_id


class Product(ObjetCollecte):
    """Objet Produit pour la cible S19 (Automation Exercise)."""

    name: str = Field(..., min_length=1)
    price: Decimal | None = Field(default=None, description="Prix normalise en Decimal.")
    currency: str | None = Field(default=None, description="Devise (ex: Rs, $, €).")
    category: str | None = Field(default=None)
    brand: str | None = Field(default=None)

    @field_validator("price", mode="before")
    @classmethod
    def _normaliser_prix(cls, v: any) -> Decimal | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None

        # Nettoyage : on garde chiffres, points et virgules
        s = str(v).replace(",", ".")
        import re
        match = re.search(r"(\d+[\.,]?\d*)", s)
        if not match:
            return None

        try:
            return Decimal(match.group(1))
        except InvalidOperation:
            return None

    @field_validator("currency", mode="before")
    @classmethod
    def _extraire_devise(cls, v: any, info) -> str | None:
        # Si on a le prix brut en entrée, on pourrait extraire la devise ici
        # Mais on s'attend à ce que l'extracteur passe la devise séparément
        return v if v else None


class Rejet(BaseModel):
    """Objet ecarte, avec son motif. Ecrit dans data/rejets.jsonl."""

    model_config = ConfigDict(extra="forbid")

    source_url: str
    motif: str
    champ: str | None = None
    brut: dict[str, object] = Field(default_factory=dict)
    horodatage: datetime = Field(default_factory=horodatage)
