"""Modele de donnees -- socle commun, independant de la cible.

`ObjetCollecte` porte les trois champs que l'enonce exige quelle que soit la
cible : un identifiant stable, l'URL source, et la date de collecte avec son
fuseau. L'objet metier concret (Product, Destination, Artwork, Book...) herite
de ce socle et ajoute les champs minimaux de la fiche de cible.

Deux classes concretes cohabitent, une par cible du groupe :

    Artwork   oeuvre du Cleveland Museum of Art        (site 1, S32)
    Product   produit d'Automation Exercise            (site 2, S19)

Elles ne partagent aucun champ metier -- les fiches de cible n'en exigent pas
les memes -- mais elles partagent l'identifiant, l'URL source et l'horodatage,
qui sont les trois colonnes que l'enonce impose quelle que soit la cible.

Convention de valeur absente, tenue dans tout le projet :

    None   le champ n'existe pas sur la page. Information a part entiere.
    ""     le champ existe et la page le laisse vide.
    0      le champ existe et vaut zero.

Les trois sont distincts, et le rapport le demande explicitement. Un
`prix = None` (non affiche) et un `prix = 0` (gratuit) ne se confondent pas.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from . import normalisation
from .extraction import ChampObligatoireAbsent


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


class Artwork(ObjetCollecte):
    """Une oeuvre du Cleveland Museum of Art (cible S32).

    Les cinq champs minimaux de la fiche de cible sont `title`, `artist`,
    `date_text`, `medium`, `url`. Seul `title` est obligatoire : une oeuvre sans
    titre n'existe pas dans le catalogue du musee, alors qu'une oeuvre sans
    auteur connu (anonyme) est frequente. La distinction absent / vide de
    `ObjetCollecte` porte ici tout son sens : `artist = None` signale une oeuvre
    que le musee n'attribue a personne, pas un ancrage rate.
    """

    title: str = Field(..., min_length=1, description="Titre de l'oeuvre, tel qu'affiche.")
    artist: str | None = Field(
        None, description="Ligne d'attribution complete. None si l'oeuvre est anonyme."
    )
    date_text: str | None = Field(
        None, description="Date de creation en toutes lettres, ex. « c. 1765 »."
    )
    medium: str | None = Field(None, description="Technique et materiaux, ex. « oil on canvas ».")
    url: HttpUrl = Field(..., description="URL de la fiche de l'oeuvre sur le site du musee.")

    @property
    def cle_dedup(self) -> str:
        """Le numero d'accession identifie l'oeuvre de facon stable.

        Il est grave dans l'objet physique et ne change pas quand le musee
        reorganise ses URL ; il est donc une meilleure cle que l'URL elle-meme.
        """
        return self.item_id

    @classmethod
    def depuis_brut(cls, brut: dict[str, Any], source_url: str) -> Artwork:
        """Construit une oeuvre validee a partir du dictionnaire brut d'extraction.

        L'extraction ne rend que des chaines telles que la page les porte ; la
        normalisation du texte (blancs Unicode, accents composes) se fait ici,
        au seul endroit qui assemble l'objet metier.
        """
        titre = normalisation.normaliser_texte(brut.get("title"))
        if titre is None:
            raise ChampObligatoireAbsent("title", source_url)
        url = normalisation.normaliser_url(brut.get("url"), source_url)
        if url is None:
            raise ChampObligatoireAbsent("url", source_url)
        return cls(
            item_id=brut["item_id"],
            source_url=source_url,
            title=titre,
            artist=normalisation.normaliser_texte(brut.get("artist")),
            date_text=normalisation.normaliser_texte(brut.get("date_text")),
            medium=normalisation.normaliser_texte(brut.get("medium")),
            url=url,
        )


class Product(ObjetCollecte):
    """Un produit du catalogue Automation Exercise (cible S19).

    Les six champs minimaux de la fiche de cible sont `name`, `price`,
    `currency`, `category`, `brand`, `url`. Seul `name` est obligatoire : un
    produit sans nom n'existe pas, alors qu'un produit dont le prix n'est pas
    affiche reste un produit. La convention absent / vide / zero de
    `ObjetCollecte` porte ici tout son sens, et plus encore que sur S32 :
    `price = None` signale un prix non affiche, `price = 0` un article gratuit.
    Les confondre fausserait toute moyenne calculee ensuite.

    `price` est un `Decimal` et non un `float` : 0.1 + 0.2 != 0.3 en binaire, et
    un montant qui derive au centieme est un defaut de donnee.
    """

    name: str = Field(..., min_length=1, description="Nom du produit, tel qu'affiche.")
    price: Decimal | None = Field(
        None, description="Montant en Decimal. None si la page n'affiche pas de prix."
    )
    currency: str | None = Field(
        None, description="Code ISO 4217 deduit du symbole affiche, ex. « Rs. » -> INR."
    )
    category: str | None = Field(None, description="Categorie, ex. « Women > Tops ».")
    brand: str | None = Field(None, description="Marque, ex. « Polo ».")
    url: HttpUrl = Field(..., description="URL de la fiche du produit.")

    @property
    def cle_dedup(self) -> str:
        """L'identifiant numerique du produit, porte par la page elle-meme.

        Il vient de `data-product-id` sur la liste et de `input#product_id` sur
        la fiche : c'est la meme valeur des deux cotes, ce qui permet de
        reconnaitre un produit deja collecte AVANT de redemander sa fiche. Un
        produit atteint par deux chemins -- sa categorie et sa marque -- n'est
        ainsi telecharge qu'une fois.
        """
        return self.item_id

    @classmethod
    def depuis_brut(cls, brut: dict[str, Any], source_url: str) -> Product:
        """Construit un produit valide a partir du dictionnaire brut d'extraction.

        L'extraction ne rend que des chaines telles que la page les porte ; la
        conversion du prix et la deduction de la devise se font ici, au seul
        endroit qui assemble l'objet metier. Prix et devise se lisent dans la
        MEME chaine (« Rs. 500 ») : les separer plus tot obligerait l'extraction
        a interpreter, ce que son contrat lui interdit.
        """
        nom = normalisation.normaliser_texte(brut.get("name"))
        if nom is None:
            raise ChampObligatoireAbsent("name", source_url)
        url = normalisation.normaliser_url(brut.get("url"), source_url)
        if url is None:
            raise ChampObligatoireAbsent("url", source_url)

        prix_affiche = brut.get("prix_affiche")
        return cls(
            item_id=brut["item_id"],
            source_url=source_url,
            name=nom,
            price=normalisation.normaliser_prix(prix_affiche),
            currency=normalisation.detecter_devise(prix_affiche),
            category=normalisation.normaliser_texte(brut.get("category")),
            brand=normalisation.normaliser_texte(brut.get("brand")),
            url=url,
        )


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
