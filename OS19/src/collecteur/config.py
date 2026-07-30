import tomllib
from pathlib import Path
from pydantic import BaseModel, Field

class CibleConfig(BaseModel):
    id: str
    nom: str
    url_depart: str

class CollecteConfig(BaseModel):
    max_objets: int
    max_pages: int
    delai_secondes: float
    concurrence: int
    suivre_detail: bool

class HttpConfig(BaseModel):
    user_agent: str
    timeout_secondes: float
    max_tentatives: int
    backoff_max_secondes: float

class SortieConfig(BaseModel):
    fichier_jsonl: str
    fichier_echantillon: str
    taille_echantillon: int
    fichier_rejets: str

class JournalConfig(BaseModel):
    niveau: str
    fichier: str

class AppConfig(BaseModel):
    cible: CibleConfig
    collecte: CollecteConfig
    http: HttpConfig
    sortie: SortieConfig
    journal: JournalConfig

def load_config(path: str = "config.toml") -> AppConfig:
    """Lit et valide la configuration TOML."""
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return AppConfig(**data)
