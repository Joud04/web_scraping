# Architecture du collecteur S19

## Flux de données
`Config` $\rightarrow$ `Acquisition` $\rightarrow$ `Extraction` $\rightarrow$ `Normalisation` $\rightarrow$ `Modèle` $\rightarrow$ `Export`

## Responsabilités
1. **Configuration** (`config.py`) : Chargement du TOML et validation via Pydantic.
2. **Acquisition** (`acquisition.py`) : Utilisation de `crawl4ai` pour récupérer le HTML. Gestion du User-Agent et des délais.
3. **Extraction** (`extraction.py`) : Analyse du DOM via BeautifulSoup. Utilisation de sélecteurs CSS stables.
4. **Normalisation** (`normalisation.py`) : Nettoyage des prix (conversion Decimal) et des textes.
5. **Modèle** (`modele.py`) : Validation stricte des objets via Pydantic.
6. **Export** (`export.py`) : Écriture incrémentale en JSONL pour garantir la survie des données en cas de crash.

## Choix techniques
- **crawl4ai** : Choisi pour sa capacité à gérer le rendu JavaScript et son intégration simplifiée, même si le site S19 est principalement HTML.
- **BeautifulSoup4** : Standard pour l'extraction robuste.
- **JSONL** : Format choisi pour permettre l'écriture ligne par ligne sans charger tout le fichier en mémoire.
