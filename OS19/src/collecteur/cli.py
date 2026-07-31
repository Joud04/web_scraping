import asyncio
import argparse
from urllib.parse import urljoin
from .config import load_config
from .journal import setup_journal, get_logger
from .acquisition import Acquisition
from .extraction import Extraction
from .normalisation import Normalisateur
from .modele import Product, Rejet
from .export import ExportateurJSONL

logger = get_logger("collecteur")

async def _collecte(config):
    export = ExportateurJSONL(config.sortie.fichier_jsonl, config.sortie.fichier_rejets)
    extracteur = Extraction()
    norm = Normalisateur()

    vus = 0
    exportes = 0

    # On utilise une file pour gérer la navigation (BFS)
    urls_to_visit = asyncio.Queue()
    await urls_to_visit.put(config.cible.url_depart)
    visited_urls = set()

    async with Acquisition(config) as acq:
        while not urls_to_visit.empty() and vus < config.collecte.max_objets:
            current_url = await urls_to_visit.get()

            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)

            logger.info(f"Visite de la page : {current_url}")
            try:
                html = await acq.fetch_html(current_url)
                if not html:
                    continue
            except Exception as e:
                logger.error(f"Erreur acquisition {current_url} : {e}")
                continue

            # 1. Extraction des produits depuis la page actuelle
            produits_bruts = extracteur.extract_products_from_list(html)

            for pb in produits_bruts:
                if vus >= config.collecte.max_objets:
                    break
                vus += 1

                try:
                    # On complète avec la page de détail si besoin
                    if config.collecte.suivre_detail and pb["url"]:
                        # On s'assure que l'URL est absolue
                        detail_url = urljoin(current_url, pb["url"])
                        html_detail = await acq.fetch_html(detail_url)
                        if html_detail:
                            details = extracteur.extract_product_details(html_detail)
                            pb.update(details)

                    # Normalisation
                    final_url = urljoin(current_url, pb["url"]) if pb["url"] else current_url
                    final_data = {
                        "item_id": final_url, # On utilise l'URL comme ID stable
                        "source_url": final_url,
                        "name": norm.nettoyer_texte(pb["name"]),
                        "price": norm.normaliser_prix(pb["price"]),
                        "currency": norm.extraire_devise(pb["price"]),
                        "category": norm.nettoyer_texte(pb["category"]),
                        "brand": norm.nettoyer_texte(pb["brand"]),
                    }

                    # Validation via Pydantic
                    produit = Product(**final_data)
                    export.ecrire_objet(produit)
                    exportes += 1

                except Exception as e:
                    logger.warning(f"Rejet du produit {pb.get('name')}: {e}")
                    export.ecrire_rejet(Rejet(
                        source_url=pb.get("url", "unknown"),
                        motif=str(e),
                        brut=pb
                    ))

            # 2. Gestion de la navigation (Pagination et Catégories)
            # Pagination
            next_page = extracteur.extract_next_page_url(html)
            if next_page:
                next_url = urljoin(current_url, next_page)
                if next_url not in visited_urls:
                    await urls_to_visit.put(next_url)

            # Catégories
            categories = extracteur.extract_category_links(html)
            for cat_link in categories:
                cat_url = urljoin(current_url, cat_link)
                if cat_url not in visited_urls:
                    await urls_to_visit.put(cat_url)

        logger.info(f"Collecte terminée : {vus} vus, {exportes} exportés.")
        export.generer_echantillon(config.sortie.fichier_jsonl, config.sortie.fichier_echantillon, config.sortie.taille_echantillon)

def main():
    parser = argparse.ArgumentParser(description="Collecteur Web S19")
    parser.add_argument("--config", default="config.toml", help="Chemin du fichier config")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_journal(config)

    try:
        asyncio.run(_collecte(config))
    except KeyboardInterrupt:
        logger.info("Interruption par l'utilisateur.")

if __name__ == "__main__":
    main()
