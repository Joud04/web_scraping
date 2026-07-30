import asyncio
import logging
from pathlib import Path
from typing import Optional
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

logger = logging.getLogger(__name__)

class AcquisitionError(Exception):
    """Erreur lors de la récupération d'une page."""
    pass

class CollecteRefusee(AcquisitionError):
    """La cible a explicitement refusé l'accès (403, 451, robots.txt)."""
    pass

class Acquisition:
    def __init__(self, config: any):
        self.config = config
        self.crawler = None

    async def __aenter__(self):
        self.crawler = AsyncWebCrawler(
            user_agent=self.config.http.user_agent,
            # On peut ajouter d'autres configs crawl4ai ici
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.crawler:
            await self.crawler.aclose()

    async def fetch_html(self, url: str) -> Optional[str]:
        """Récupère le contenu HTML d'une URL avec gestion du délai et des erreurs."""
        logger.info(f"Acquisition de : {url}")

        try:
            # crawl4ai gère nativement le rendu et le cache
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS, # On veut le contenu frais pour le TP
                # On peut ajouter des filtres ou des hooks ici
            )

            result = await self.crawler.arun(url=url, config=run_config)

            if not result or not result.success:
                logger.error(f"Échec de l'acquisition pour {url}: {result.error if result else 'Inconnu'}")
                raise AcquisitionError(f"Échec HTTP pour {url}")

            # Vérification simplifiée du robots.txt (crawl4ai le fait souvent en interne,
            # mais on peut ajouter une vérification explicite ici si besoin)

            return result.html

        except Exception as e:
            logger.exception(f"Erreur critique lors de l'acquisition de {url}")
            raise AcquisitionError(f"Erreur imprévue : {e}")
