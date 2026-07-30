"""Acquisition -- requetes HTTP, delai, robots.txt, gestion des refus.

Ce module ne connait rien de la cible. Il applique les regles de conduite de
l'enonce, qui sont les memes quel que soit le site :

  - une requete a la fois, avec un delai minimal entre deux ;
  - le `Crawl-delay` du robots.txt gagne toujours sur le delai configure ;
  - un chemin interdit par robots.txt n'est pas demande ;
  - un refus explicite (401, 403, 407, 451, page de verification) ARRETE la
    collecte. Il n'est jamais contourne, ni reessaye avec d'autres en-tetes.

Cette derniere ligne est la regle la plus lourde de l'enonce : « un
contournement d'un blocage explicite rend les elements concernes non evaluables ».
Elle est donc implementee comme une exception distincte de celle des erreurs
temporaires, pour qu'aucune boucle de reessai ne puisse l'attraper par accident.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from .config import Config
from .journal import LOGGER

# Statuts qui signifient « non », et qui arretent la collecte.
REFUS_EXPLICITES = frozenset({401, 403, 407, 451})
# Statuts qui signifient « pas maintenant », et qui autorisent un reessai.
REESSAYABLES = frozenset({408, 429, 500, 502, 503, 504})


class CollecteRefusee(RuntimeError):
    """La cible refuse l'acces. On s'arrete et on documente -- on ne contourne pas."""


class ReessayerPlusTard(RuntimeError):
    """Erreur temporaire. Un reessai est legitime, dans la limite configuree."""


@dataclass(slots=True)
class Reponse:
    url: str
    statut: int
    texte: str
    content_type: str


class Robots:
    """Lecture du robots.txt, avant toute autre requete.

    Un robots.txt absent (404) n'interdit rien : la collecte continue, et le
    rapport doit le dire ainsi. Un robots.txt illisible est traite comme absent,
    mais journalise en WARNING -- l'ignorer en silence serait une conclusion non
    prouvee.
    """

    def __init__(self, url_depart: str, user_agent: str) -> None:
        parties = urlsplit(url_depart)
        self.url = f"{parties.scheme}://{parties.netloc}/robots.txt"
        self.user_agent = user_agent
        self._parser = RobotFileParser()
        self.crawl_delay: float | None = None
        self.contenu: str | None = None

    def charger(self, client: httpx.Client) -> Robots:
        try:
            reponse = client.get(self.url)
        except httpx.HTTPError as erreur:
            LOGGER.warning(
                "robots.txt injoignable (%s) : %s -- aucune regle appliquee", self.url, erreur
            )
            self._parser.parse([])
            return self

        if reponse.status_code == 404:
            LOGGER.info("robots.txt absent (404) sur %s -- aucun chemin interdit", self.url)
            self._parser.parse([])
            return self
        if reponse.status_code >= 400:
            LOGGER.warning("robots.txt : statut %d sur %s", reponse.status_code, self.url)
            self._parser.parse([])
            return self

        self.contenu = reponse.text
        self._parser.parse(self.contenu.splitlines())
        delai = self._parser.crawl_delay(self.user_agent)
        if delai is not None:
            self.crawl_delay = float(delai)
            LOGGER.info("robots.txt declare Crawl-delay: %s", self.crawl_delay)
        return self

    def autorise(self, url: str) -> bool:
        return self._parser.can_fetch(self.user_agent, url)


class ClientHTTP:
    """Client poli : delai garanti, reessai borne, refus non contourne."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.delai = config.collecte.delai_secondes
        self._dernier_appel = 0.0
        self._client = httpx.Client(
            headers={
                "User-Agent": config.http.user_agent,
                "Accept-Language": "en;q=0.9",
            },
            timeout=config.http.timeout_secondes,
            follow_redirects=True,
        )
        self.robots: Robots | None = None

    def __enter__(self) -> ClientHTTP:
        self.robots = Robots(self.config.cible.url_depart, self.config.http.user_agent).charger(
            self._client
        )
        if self.robots.crawl_delay is not None and self.robots.crawl_delay > self.delai:
            LOGGER.info(
                "Delai releve de %.1fs a %.1fs : le Crawl-delay du robots.txt gagne.",
                self.delai,
                self.robots.crawl_delay,
            )
            self.delai = self.robots.crawl_delay
        return self

    def __exit__(self, *_: object) -> None:
        self._client.close()

    def _attendre(self) -> None:
        ecoule = time.monotonic() - self._dernier_appel
        if (reste := self.delai - ecoule) > 0:
            time.sleep(reste)
        self._dernier_appel = time.monotonic()

    def get(self, url: str) -> Reponse:
        """Recupere une URL, en respectant robots.txt, le delai et les refus.

        Leve `CollecteRefusee` sur un refus explicite -- volontairement non
        rattrapee par la boucle de reessai.
        """
        if self.robots is not None and not self.robots.autorise(url):
            raise CollecteRefusee(f"robots.txt interdit ce chemin : {url}")

        derniere: Exception | None = None
        for tentative in range(1, self.config.http.max_tentatives + 1):
            self._attendre()
            try:
                reponse = self._client.get(url)
            except httpx.HTTPError as erreur:
                derniere = erreur
                LOGGER.warning("Erreur reseau sur %s (essai %d) : %s", url, tentative, erreur)
                time.sleep(min(2.0**tentative, self.config.http.backoff_max_secondes))
                continue

            if reponse.status_code in REFUS_EXPLICITES:
                raise CollecteRefusee(
                    f"Statut {reponse.status_code} sur {url}. "
                    "Refus explicite : la collecte s'arrete, conformement a l'enonce. "
                    "Conserver l'URL, l'heure et le statut comme preuve, et prevenir le formateur."
                )

            if reponse.status_code in REESSAYABLES:
                attente = self._attente_apres(reponse, tentative)
                LOGGER.warning(
                    "Statut %d sur %s (essai %d/%d) -- pause de %.1fs",
                    reponse.status_code,
                    url,
                    tentative,
                    self.config.http.max_tentatives,
                    attente,
                )
                derniere = ReessayerPlusTard(f"Statut {reponse.status_code} sur {url}")
                time.sleep(attente)
                continue

            if reponse.status_code >= 400:
                raise ReessayerPlusTard(f"Statut {reponse.status_code} sur {url}")

            return Reponse(
                url=str(reponse.url),
                statut=reponse.status_code,
                texte=reponse.text,
                content_type=reponse.headers.get("content-type", ""),
            )

        raise ReessayerPlusTard(
            f"{self.config.http.max_tentatives} tentatives echouees sur {url}"
        ) from derniere

    def _attente_apres(self, reponse: httpx.Response, tentative: int) -> float:
        """Respecte `Retry-After` s'il est present, sinon backoff exponentiel.

        `Retry-After` est une instruction du serveur : l'ignorer pour un delai
        calcule maison est exactement le comportement qui fait bannir une IP.
        Le plafond evite qu'un serveur renvoyant `Retry-After: 3600` immobilise
        la collecte une heure.
        """
        entete = reponse.headers.get("retry-after")
        if entete:
            try:
                return min(float(entete), self.config.http.backoff_max_secondes)
            except ValueError:
                LOGGER.debug("Retry-After non numerique : %r", entete)
        return min(2.0**tentative, self.config.http.backoff_max_secondes)
