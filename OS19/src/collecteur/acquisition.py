import asyncio
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class AcquisitionError(Exception):
    """Erreur lors de la récupération d'une page."""
    pass


class Acquisition:
    """Acquisition asynchrone utilisant httpx sans crawl4ai."""

    def __init__(self, config):
        self.config = config
        self.client = None
        self.last_request_time = 0.0

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=self.config.http.timeout_secondes,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def fetch_html(self, url: str) -> Optional[str]:
        """Récupère le contenu HTML d'une URL avec gestion du délai."""
        logger.info(f"Acquisition de : {url}")

        try:
            # Respecte le délai configuré
            now = time.monotonic()
            elapsed = now - self.last_request_time
            if elapsed < self.config.collecte.delai_secondes:
                await asyncio.sleep(self.config.collecte.delai_secondes - elapsed)
            self.last_request_time = time.monotonic()

            # Requête HTTP asynchrone
            response = await self.client.get(
                url,
                headers={
                    "User-Agent": self.config.http.user_agent,
                    "Accept-Language": "en;q=0.9"
                }
            )

            # Gestion des codes d'erreur
            if response.status_code in {401, 403, 407, 451}:
                raise AcquisitionError(f"Accès refusé (statut {response.status_code}) : {url}")

            if response.status_code >= 400:
                logger.error(f"Erreur HTTP {response.status_code} pour {url}")
                raise AcquisitionError(f"Statut {response.status_code} pour {url}")

            return response.text

        except asyncio.CancelledError:
            raise
        except AcquisitionError:
            raise
        except Exception as e:
            logger.exception(f"Erreur lors de l'acquisition de {url}")
            raise AcquisitionError(f"Erreur: {str(e)}")
