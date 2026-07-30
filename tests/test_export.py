"""Verification de l'export JSONL -- le format de sortie du projet.

Ces tests ne remplacent aucun des trois controles exiges par l'enonce : ils
verifient la brique qui ecrit le livrable, ce qui est le minimum avant de
promettre un fichier de sortie a quelqu'un.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from collecteur.export import (
    EcrivainJSONL,
    ecrire_echantillon_json,
    ecrire_jsonl,
    lire_jsonl,
)
from collecteur.modele import ObjetCollecte


def test_une_ligne_par_objet(tmp_path: Path) -> None:
    chemin = tmp_path / "sortie.jsonl"
    ecrire_jsonl(chemin, [{"a": 1}, {"a": 2}, {"a": 3}])
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    assert len(lignes) == 3
    assert [json.loads(ligne)["a"] for ligne in lignes] == [1, 2, 3]


def test_le_dossier_parent_est_cree(tmp_path: Path) -> None:
    chemin = tmp_path / "data" / "profond" / "sortie.jsonl"
    ecrire_jsonl(chemin, [{"a": 1}])
    assert chemin.exists()


def test_utf8_sans_echappement(tmp_path: Path) -> None:
    """Un nom accentue doit rester lisible a l'oeil dans le fichier produit."""
    chemin = tmp_path / "sortie.jsonl"
    ecrire_jsonl(chemin, [{"nom": "Pérou"}])
    assert "Pérou" in chemin.read_text(encoding="utf-8")
    assert "\\u" not in chemin.read_text(encoding="utf-8")


def test_fins_de_ligne_unix_meme_sous_windows(tmp_path: Path) -> None:
    """Sans newline='\\n', Python ecrirait \\r\\n et le fichier differerait par OS."""
    chemin = tmp_path / "sortie.jsonl"
    ecrire_jsonl(chemin, [{"a": 1}, {"a": 2}])
    assert b"\r\n" not in chemin.read_bytes()


def test_decimal_serialise_en_chaine(tmp_path: Path) -> None:
    """Le prix ne doit pas passer par un float : 129.90 ne s'y represente pas exactement."""
    chemin = tmp_path / "sortie.jsonl"
    ecrire_jsonl(chemin, [{"prix": Decimal("129.90")}])
    assert json.loads(chemin.read_text(encoding="utf-8"))["prix"] == "129.90"


def test_datetime_serialise_en_iso8601_avec_fuseau(tmp_path: Path) -> None:
    chemin = tmp_path / "sortie.jsonl"
    ecrire_jsonl(chemin, [{"quand": datetime(2026, 7, 30, 14, 0, tzinfo=UTC)}])
    assert json.loads(chemin.read_text(encoding="utf-8"))["quand"] == "2026-07-30T14:00:00+00:00"


def test_modele_pydantic_accepte(tmp_path: Path) -> None:
    chemin = tmp_path / "sortie.jsonl"
    objet = ObjetCollecte(item_id="CS-1001", source_url="https://exemple.org/p/1")
    ecrire_jsonl(chemin, [objet])
    relu = lire_jsonl(chemin)
    assert relu[0]["item_id"] == "CS-1001"


def test_ordre_des_cles_stable(tmp_path: Path) -> None:
    """Deux executions doivent produire des lignes comparables par diff."""
    chemin = tmp_path / "sortie.jsonl"
    ecrire_jsonl(chemin, [{"b": 2, "a": 1}])
    assert chemin.read_text(encoding="utf-8").strip() == '{"a": 1, "b": 2}'


def test_ecriture_incrementale_survit_a_une_interruption(tmp_path: Path) -> None:
    """L'argument principal en faveur du JSONL, verifie plutot qu'affirme.

    Une collecte qui tombe au troisieme objet laisse les deux premiers lisibles.
    Un `json.dump` d'une liste complete en fin de course n'aurait rien laisse.
    """
    chemin = tmp_path / "sortie.jsonl"
    with pytest.raises(RuntimeError), EcrivainJSONL(chemin) as sortie:
        sortie.ecrire({"a": 1})
        sortie.ecrire({"a": 2})
        raise RuntimeError("panne simulee au milieu de la collecte")
    assert len(lire_jsonl(chemin)) == 2


def test_ligne_corrompue_ignoree_sans_perdre_le_fichier(tmp_path: Path) -> None:
    chemin = tmp_path / "sortie.jsonl"
    chemin.write_text('{"a": 1}\nceci n\'est pas du json\n{"a": 3}\n', encoding="utf-8")
    objets = lire_jsonl(chemin)
    assert [objet["a"] for objet in objets] == [1, 3]


def test_ecriture_hors_contexte_refusee(tmp_path: Path) -> None:
    ecrivain = EcrivainJSONL(tmp_path / "sortie.jsonl")
    with pytest.raises(RuntimeError):
        ecrivain.ecrire({"a": 1})


def test_echantillon_limite_et_indente(tmp_path: Path) -> None:
    chemin = tmp_path / "sample_output.json"
    nombre = ecrire_echantillon_json(chemin, [{"n": i} for i in range(50)], limite=10)
    assert nombre == 10
    contenu = json.loads(chemin.read_text(encoding="utf-8"))
    assert len(contenu) == 10
    assert "\n  " in chemin.read_text(encoding="utf-8")


def test_objet_non_serialisable_leve(tmp_path: Path) -> None:
    """Un type inattendu doit lever, pas etre converti en chaine au petit bonheur."""
    with pytest.raises(TypeError), EcrivainJSONL(tmp_path / "s.jsonl") as sortie:
        sortie.ecrire({"objet": object()})
