import logging
from datetime import UTC
from pathlib import Path

def setup_journal(config: any):
    """Configure le logging selon le fichier config.toml."""
    # Assure que le dossier de logs existe
    log_file = Path(config.journal.fichier)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, config.journal.niveau.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(config.journal.fichier, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

def get_logger(name: str):
    return logging.getLogger(name)
