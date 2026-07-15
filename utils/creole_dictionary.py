#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dictionnaire français <-> créole guadeloupéen (kréyòl gwadloupéyen).

Module autonome (bibliothèque standard uniquement) pour charger et interroger
le lexique `data/creole_gwada.json`. Utilisé par l'API du Transcripteur Audio Pro.

Créé pour le projet Transcripteur Audio Pro - Négus Dja.
"""

import json
import logging
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Chemin par défaut du lexique : <racine du dépôt>/data/creole_gwada.json
DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "creole_gwada.json"


def _normalize(text: str) -> str:
    """Minuscule + suppression des accents/diacritiques pour une comparaison souple."""
    if not text:
        return ""
    text = text.strip().lower()
    # Décompose puis retire les marques diacritiques (é -> e, ò -> o, etc.)
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped


class CreoleDictionary:
    """Chargement et interrogation du lexique français <-> créole guadeloupéen."""

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = Path(data_path) if data_path else DEFAULT_DATA_PATH
        self.meta: Dict[str, Any] = {}
        self.entries: List[Dict[str, Any]] = []
        # Index normalisés pour des recherches rapides et insensibles aux accents
        self._fr_index: Dict[str, List[Dict[str, Any]]] = {}
        self._cr_index: Dict[str, List[Dict[str, Any]]] = {}
        self.load()

    def load(self) -> None:
        """Charge (ou recharge) le lexique depuis le fichier JSON."""
        try:
            with open(self.data_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.meta = data.get("meta", {})
            self.entries = data.get("entries", [])
            self._build_indexes()
            logger.info(
                "📖 Dictionnaire créole chargé: %d entrées (%s)",
                len(self.entries), self.data_path.name,
            )
        except FileNotFoundError:
            logger.warning("Lexique introuvable: %s", self.data_path)
            self.meta, self.entries = {}, []
            self._build_indexes()
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Erreur de chargement du lexique: %s", e)
            self.meta, self.entries = {}, []
            self._build_indexes()

    def _build_indexes(self) -> None:
        self._fr_index = {}
        self._cr_index = {}
        for entry in self.entries:
            self._fr_index.setdefault(_normalize(entry.get("fr", "")), []).append(entry)
            self._cr_index.setdefault(_normalize(entry.get("cr", "")), []).append(entry)

    def lookup(self, term: str, direction: str = "fr-cr") -> List[Dict[str, Any]]:
        """
        Recherche exacte (insensible casse/accents).

        Args:
            term: mot à rechercher.
            direction: 'fr-cr' (français -> créole), 'cr-fr' (créole -> français)
                       ou 'auto' (cherche dans les deux sens).

        Returns:
            Liste des entrées correspondantes (vide si aucune).
        """
        key = _normalize(term)
        if not key:
            return []

        if direction == "fr-cr":
            return list(self._fr_index.get(key, []))
        if direction == "cr-fr":
            return list(self._cr_index.get(key, []))
        if direction == "auto":
            # Dédoublonne en conservant l'ordre (fr d'abord, puis cr)
            found = self._fr_index.get(key, []) + self._cr_index.get(key, [])
            seen, result = set(), []
            for entry in found:
                marker = id(entry)
                if marker not in seen:
                    seen.add(marker)
                    result.append(entry)
            return result
        raise ValueError(f"Direction inconnue: {direction!r}")

    def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Recherche partielle (sous-chaîne) côté français ET créole."""
        key = _normalize(query)
        if not key:
            return []
        results = []
        for entry in self.entries:
            if key in _normalize(entry.get("fr", "")) or key in _normalize(entry.get("cr", "")):
                results.append(entry)
                if len(results) >= limit:
                    break
        return results

    def all_entries(self) -> List[Dict[str, Any]]:
        """Toutes les entrées (copie)."""
        return list(self.entries)

    def categories(self) -> List[str]:
        """Liste triée des catégories présentes."""
        return sorted({e.get("category", "") for e in self.entries if e.get("category")})

    def by_category(self, category: str) -> List[Dict[str, Any]]:
        """Entrées d'une catégorie donnée."""
        key = _normalize(category)
        return [e for e in self.entries if _normalize(e.get("category", "")) == key]

    def get_meta(self) -> Dict[str, Any]:
        """Métadonnées du lexique (nom, version, avertissement, etc.)."""
        return dict(self.meta)

    def stats(self) -> Dict[str, Any]:
        """Statistiques utiles pour l'API/monitoring."""
        return {
            "total_entries": len(self.entries),
            "categories": self.categories(),
            "version": self.meta.get("version"),
            "language_pair": self.meta.get("language_pair"),
        }

    def add_entry(self, fr: str, cr: str, category: str = "divers",
                  notes: str = "", persist: bool = False) -> Dict[str, Any]:
        """
        Ajoute une entrée en mémoire (et éventuellement sur disque).

        Args:
            persist: si True, réécrit le fichier JSON.

        Returns:
            L'entrée ajoutée.
        """
        if not fr.strip() or not cr.strip():
            raise ValueError("Les champs 'fr' et 'cr' sont obligatoires")

        entry = {"fr": fr.strip(), "cr": cr.strip(),
                 "category": category.strip() or "divers", "notes": notes.strip()}
        self.entries.append(entry)
        self._fr_index.setdefault(_normalize(entry["fr"]), []).append(entry)
        self._cr_index.setdefault(_normalize(entry["cr"]), []).append(entry)

        if persist:
            self.save()
        return entry

    def save(self) -> None:
        """Réécrit le lexique sur disque (meta + entrées)."""
        payload = {"meta": self.meta, "entries": self.entries}
        with open(self.data_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        logger.info("💾 Lexique enregistré: %s (%d entrées)", self.data_path, len(self.entries))
