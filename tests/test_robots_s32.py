"""Conformite au robots.txt de la cible S32 -- rejoue sans reseau.

La fiche de cible S32 pose une exigence complementaire explicite :

    « le robots.txt impose Crawl-delay: 10 : le volume est reduit en consequence
      et le respect du delai fait partie de l'evaluation »

Le collecteur applique bien la regle, mais rien ne le prouvait hors execution
reelle. Un delai qui cesserait d'etre releve -- une refactorisation de
`ClientHTTP.__enter__`, un `crawl_delay` mal lu -- passerait alors inapercu
jusqu'a la demonstration devant le formateur.

Ces tests rejouent donc le robots.txt REEL de la cible, enregistre tel quel dans
tests/fixtures/robots.txt, contre le mecanisme reel du client. Aucune requete
n'est emise : `Robots.charger` est remplace par une lecture de la fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from collecteur import config as module_config
from collecteur.acquisition import ClientHTTP, CollecteRefusee, Robots

FIXTURE = Path(__file__).parent / "fixtures" / "robots.txt"

URL_DEPART = "https://www.clevelandart.org/art/collection/search"
URL_FICHE = "https://www.clevelandart.org/art/1915.534"
URL_API = "https://www.clevelandart.org/api/artworks?limit=30"

# Valeur de la fiche de cible S32. Ecrite ici en clair : si le musee changeait
# son robots.txt, ce test doit echouer bruyamment plutot que s'adapter en
# silence a une contrainte differente de celle sur laquelle on est evalue.
CRAWL_DELAY_ATTENDU = 10.0


@pytest.fixture
def robots_s32() -> Robots:
    """Le robots.txt reel de la cible, parse sans passer par le reseau."""
    robots = Robots(URL_DEPART, "TP-Scraping-Collecteur/0.1")
    robots.contenu = FIXTURE.read_text(encoding="utf-8")
    robots._parser.parse(robots.contenu.splitlines())
    delai = robots._parser.crawl_delay(robots.user_agent)
    robots.crawl_delay = float(delai) if delai is not None else None
    return robots


@pytest.fixture
def config_s32() -> module_config.Config:
    """Configuration volontairement trop permissive : delai a 1 s.

    C'est le point du test. Le collecteur doit RELEVER ce delai a 10 s en lisant
    le robots.txt, sans qu'on ait a l'ecrire correctement dans la configuration.
    """
    return module_config.Config(
        cible=module_config.Cible(id="S32", nom="Cleveland", url_depart=URL_DEPART),
        collecte=module_config.Collecte(delai_secondes=1.0, max_objets=30),
    )


class TestLectureDuRobots:
    def test_crawl_delay_de_dix_secondes_est_lu(self, robots_s32: Robots) -> None:
        assert robots_s32.crawl_delay == CRAWL_DELAY_ATTENDU

    def test_les_fiches_d_oeuvre_sont_autorisees(self, robots_s32: Robots) -> None:
        assert robots_s32.autorise(URL_FICHE) is True
        assert robots_s32.autorise(URL_DEPART) is True

    def test_l_api_interne_est_interdite(self, robots_s32: Robots) -> None:
        """`/api` porte les resultats de recherche. C'est la voie la plus directe,
        et c'est celle qu'on s'interdit : le robots.txt la refuse."""
        assert robots_s32.autorise(URL_API) is False

    @pytest.mark.parametrize("chemin", ["/membership", "/orders", "/errors", "/404", "/500"])
    def test_les_autres_chemins_interdits_le_restent(self, robots_s32: Robots, chemin: str) -> None:
        assert robots_s32.autorise(f"https://www.clevelandart.org{chemin}") is False


class TestApplicationParLeClient:
    """Le mecanisme reel : `ClientHTTP.__enter__` releve le delai configure."""

    @pytest.fixture
    def client(
        self,
        config_s32: module_config.Config,
        robots_s32: Robots,
        monkeypatch: pytest.MonkeyPatch,
    ) -> ClientHTTP:
        monkeypatch.setattr(Robots, "charger", lambda self, _client: robots_s32)
        return ClientHTTP(config_s32)

    def test_le_delai_est_releve_de_1s_a_10s(self, client: ClientHTTP) -> None:
        assert client.delai == 1.0  # avant l'entree : valeur de la configuration
        with client:
            assert client.delai == CRAWL_DELAY_ATTENDU

    def test_le_delai_configure_plus_long_n_est_pas_abaisse(
        self, robots_s32: Robots, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Le Crawl-delay est un plancher, pas une consigne a appliquer telle quelle.

        Un eleve qui choisit 30 s par prudence ne doit pas voir son delai ramene
        a 10 s par la lecture du robots.txt.
        """
        monkeypatch.setattr(Robots, "charger", lambda self, _client: robots_s32)
        config = module_config.Config(
            cible=module_config.Cible(id="S32", url_depart=URL_DEPART),
            collecte=module_config.Collecte(delai_secondes=30.0),
        )
        with ClientHTTP(config) as client:
            assert client.delai == 30.0

    def test_une_url_interdite_est_refusee_avant_toute_requete(self, client: ClientHTTP) -> None:
        """La verification robots.txt precede l'appel reseau.

        Le test le prouve : le client n'a aucune connexion utilisable ici, et
        pourtant l'appel leve CollecteRefusee sans jamais atteindre le reseau.
        """
        with client, pytest.raises(CollecteRefusee, match="robots.txt"):
            client.get(URL_API)

    def test_le_refus_n_est_pas_une_erreur_temporaire(self, client: ClientHTTP) -> None:
        """CollecteRefusee ne doit jamais heriter de ReessayerPlusTard.

        Si les deux se confondaient, la boucle de reessai rattraperait un refus et
        le collecteur insisterait sur un chemin interdit -- exactement le
        contournement que l'enonce rend non evaluable.
        """
        from collecteur.acquisition import ReessayerPlusTard

        assert not issubclass(CollecteRefusee, ReessayerPlusTard)
        assert not issubclass(ReessayerPlusTard, CollecteRefusee)
