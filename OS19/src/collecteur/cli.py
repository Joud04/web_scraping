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

    async with Acquisition(config) as acq:
        # 1. Récupération de la page liste
        html_liste = await acq.fetch_html(config.cible.url_depart)
        if not html_liste:
            return

        # 2. Extraction des produits depuis la liste
        produits_bruts = extracteur.extract_products_from_list(html_liste)
        logger.info(f"Trouvé {len(produits_bruts)} produits sur la page liste.")

        vus = 0
        exportes = 0

        for pb in produits_bruts:
            if vus >= config.collecte.max_objets:
                break
            vus += 1

            try:
                # Convertir l'URL relative en URL absolue
                absolute_url = urljoin(config.cible.url_depart, pb["url"])

                # On complète avec la page de détail si besoin
                if config.collecte.suivre_detail and pb["url"]:
                    html_detail = await acq.fetch_html(absolute_url)
                    if html_detail:
                        details = extracteur.extract_product_details(html_detail)
                        pb.update(details)

                # Normalisation
                final_data = {
                    "item_id": absolute_url,  # On utilise l'URL absolue comme ID stable
                    "source_url": absolute_url,
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

        logger.info(f"Collecte terminée : {vus} vus, {exportes} exportés.")

        # Générer l'échantillon uniquement si des produits ont été exportés
        from pathlib import Path
        if Path(config.sortie.fichier_jsonl).exists() and Path(config.sortie.fichier_jsonl).stat().st_size > 0:
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
