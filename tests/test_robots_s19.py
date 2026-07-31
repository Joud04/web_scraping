"""Conformite robots.txt sur la cible S19, ou le fichier est ABSENT.

Le site 1 (S32) publie un robots.txt avec « Crawl-delay: 10 » et « Disallow:
/api » ; ses tests sont dans test_robots_s32.py. Le site 2 n'en publie aucun :
/robots.txt repond 302 vers la page d'accueil.

C'est le cas le plus facile a mal traiter. Deux erreurs sont possibles :

  1. lire la page HTML renvoyee comme si c'etait un robots.txt, et appliquer
     comme regle une ligne « Disallow: » qui s'y trouverait par hasard ;
  2. conclure de l'absence de regles qu'on peut interroger le site aussi vite
     qu'on veut.

Ces tests verrouillent le comportement attendu sur les deux points. Aucun ne
touche le reseau : la reponse du serveur est simulee.
"""

from __future__ import annotations

import httpx
import pytest

from collecteur.acquisition import ClientHTTP, Robots
from collecteur.config import Cible, Collecte, Config, Http, Journal, Sortie

URL_S19 = "https://automationexercise.com/products"
AGENT = "TP-Scraping-Collecteur/0.1 (test)"


def _config(delai: float = 1.0) -> Config:
    return Config(
        cible=Cible(id="S19", nom="Automation Exercise", url_depart=URL_S19),
        collecte=Collecte(max_objets=60, max_pages=20, delai_secondes=delai),
        http=Http(user_agent=AGENT),
        sortie=Sortie(),
        journal=Journal(),
    )


def _reponse(contenu: str, type_contenu: str, statut: int = 200) -> httpx.Response:
    return httpx.Response(
        statut,
        text=contenu,
        headers={"content-type": type_contenu},
        request=httpx.Request("GET", "https://automationexercise.com/robots.txt"),
    )


class _ClientFactice:
    """Client HTTP minimal qui rend toujours la meme reponse, sans reseau."""

    def __init__(self, reponse: httpx.Response) -> None:
        self.reponse = reponse
        self.appels = 0

    def get(self, _url: str) -> httpx.Response:
        self.appels += 1
        return self.reponse


PAGE_HTML = (
    "<!DOCTYPE html><html><head><title>Automation Exercise</title></head>"
    "<body><p>This is for automation practice</p></body></html>"
)


def test_redirection_vers_une_page_html_vaut_absence_de_robots() -> None:
    """Une reponse HTML n'est pas un robots.txt, meme en statut 200."""
    robots = Robots(URL_S19, AGENT)
    robots.charger(_ClientFactice(_reponse(PAGE_HTML, "text/html; charset=utf-8")))

    assert robots.contenu is None
    assert robots.crawl_delay is None


def test_aucun_chemin_interdit_quand_le_fichier_est_absent() -> None:
    robots = Robots(URL_S19, AGENT)
    robots.charger(_ClientFactice(_reponse(PAGE_HTML, "text/html")))

    assert robots.autorise(URL_S19) is True
    assert robots.autorise("https://automationexercise.com/product_details/1") is True


def test_une_page_html_contenant_disallow_n_est_pas_appliquee() -> None:
    """Le coeur du test : pas de regle deduite d'un document qui n'en est pas un.

    Une page d'accueil peut contenir le mot « Disallow » dans un texte, un
    script ou un commentaire. Lue comme un robots.txt, cette ligne interdirait
    tout le site et la collecte s'arreterait sur une regle qui n'existe pas.
    """
    piege = "<!DOCTYPE html><html><body><pre>User-agent: *\nDisallow: /\n</pre></body></html>"
    robots = Robots(URL_S19, AGENT)
    robots.charger(_ClientFactice(_reponse(piege, "text/html")))

    assert robots.autorise("https://automationexercise.com/products") is True


def test_un_vrai_robots_txt_reste_lu() -> None:
    """La garde ne doit pas rendre le collecteur sourd aux vraies regles."""
    robots = Robots(URL_S19, AGENT)
    robots.charger(
        _ClientFactice(_reponse("User-agent: *\nDisallow: /panier\nCrawl-delay: 3\n", "text/plain"))
    )

    assert robots.crawl_delay == 3.0
    assert robots.autorise("https://automationexercise.com/panier") is False
    assert robots.autorise("https://automationexercise.com/products") is True


def test_absence_de_robots_ne_supprime_pas_le_delai(monkeypatch: pytest.MonkeyPatch) -> None:
    """L'absence de regle n'est pas une autorisation d'aller vite.

    Aucun Crawl-delai n'etant declare, rien ne releve le delai configure -- mais
    rien ne doit non plus l'abaisser. La politesse sur cette cible est
    entierement a notre charge, et c'est le point que ce test protege.
    """
    monkeypatch.setattr(Robots, "charger", lambda self, _client: (self._parser.parse([]) or self))
    with ClientHTTP(_config(delai=1.5)) as client:
        assert client.delai == 1.5


def test_crawl_delay_declare_releve_toujours_le_delai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si la cible declarait un jour un Crawl-delay, il gagnerait."""

    def _charger(self: Robots, _client: object) -> Robots:
        self._parser.parse(["User-agent: *", "Crawl-delay: 7"])
        self.crawl_delay = 7.0
        return self

    monkeypatch.setattr(Robots, "charger", _charger)
    with ClientHTTP(_config(delai=1.0)) as client:
        assert client.delai == 7.0
