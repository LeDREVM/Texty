#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Traducteur français <-> créole guadeloupéen.

Deux modes :
  1. MODÈLE (si disponible) : un modèle NLLB affiné, chargé depuis le dossier
     indiqué par la variable d'environnement TRANSLATION_MODEL_DIR. Nécessite
     `transformers` + `torch` (voir training/). Utilisé automatiquement s'il est là.
  2. REPLI dictionnaire + règles : traduction mot à mot via CreoleDictionary,
     disponible partout (bibliothèque standard). Approximatif — pas une vraie
     traduction de phrases.

Le mode modèle est chargé paresseusement pour ne rien casser si les dépendances
ML ne sont pas installées (cas de l'environnement web du projet).
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Codes de langue NLLB (le créole gwada réutilise le code haïtien par transfert)
_NLLB_LANG = {"fr": "fra_Latn", "cr": "hat_Latn"}
_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class Translator:
    """Traducteur avec modèle NLLB optionnel et repli dictionnaire+règles."""

    def __init__(self, dictionary, model_dir: Optional[str] = None):
        self.dictionary = dictionary
        self.model_dir = model_dir or os.getenv("TRANSLATION_MODEL_DIR")
        self._model = None
        self._tokenizer = None
        self._model_tried = False  # évite de retenter un chargement qui a échoué

    # ------------------------------------------------------------------ modèle
    def _ensure_model(self) -> bool:
        """Charge le modèle NLLB si possible. Retourne True si utilisable."""
        if self._model is not None:
            return True
        if self._model_tried or not self.model_dir:
            return False
        self._model_tried = True
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM  # lazy
            logger.info("🌐 Chargement du modèle de traduction: %s", self.model_dir)
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_dir)
            return True
        except Exception as e:
            logger.warning("Modèle de traduction indisponible (%s) — repli dictionnaire", e)
            return False

    def _translate_model(self, text: str, src: str, tgt: str) -> str:
        tokenizer, model = self._tokenizer, self._model
        tokenizer.src_lang = _NLLB_LANG[src]
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
        bos = tokenizer.convert_tokens_to_ids(_NLLB_LANG[tgt])
        generated = model.generate(**inputs, forced_bos_token_id=bos, max_length=256)
        return tokenizer.batch_decode(generated, skip_special_tokens=True)[0]

    # -------------------------------------------------------------- repli dico
    def _translate_dictionary(self, text: str, direction: str) -> Dict[str, Any]:
        out_tokens: List[str] = []
        unknown: List[str] = []

        for token in _TOKEN_RE.findall(text):
            if not token.isalnum() and not token.isalpha():
                out_tokens.append(token)  # ponctuation
                continue
            matches = self.dictionary.lookup(token, direction)
            if matches:
                target = matches[0]["cr"] if direction == "fr-cr" else matches[0]["fr"]
                out_tokens.append(_match_case(token, target))
            else:
                out_tokens.append(token)
                unknown.append(token)

        translation = _detokenize(out_tokens)
        return {
            "translation": translation,
            "method": "dictionary",
            "unknown": unknown,
            "note": "Traduction mot à mot approximative (dictionnaire). "
                    "Entraînez un modèle pour de vraies phrases (voir training/).",
        }

    # ------------------------------------------------------------------ public
    def translate(self, text: str, direction: str = "fr-cr") -> Dict[str, Any]:
        """
        Traduit `text`. direction: 'fr-cr' (français->créole) ou 'cr-fr'.
        Utilise le modèle si disponible, sinon le dictionnaire.
        """
        if direction not in ("fr-cr", "cr-fr"):
            raise ValueError("direction doit être 'fr-cr' ou 'cr-fr'")
        text = (text or "").strip()
        if not text:
            return {"translation": "", "method": "none", "unknown": []}

        if self._ensure_model():
            src, tgt = direction.split("-")
            try:
                return {
                    "translation": self._translate_model(text, src, tgt),
                    "method": "model",
                    "unknown": [],
                }
            except Exception as e:
                logger.warning("Échec du modèle, repli dictionnaire: %s", e)

        return self._translate_dictionary(text, direction)


def _match_case(source: str, target: str) -> str:
    """Reporte la casse (Majuscule initiale / TOUT EN MAJUSCULE) de source sur target."""
    if source.isupper() and len(source) > 1:
        return target.upper()
    if source[:1].isupper():
        return target[:1].upper() + target[1:]
    return target


def _detokenize(tokens: List[str]) -> str:
    """Recolle les tokens en gérant les espaces autour de la ponctuation."""
    text = ""
    for tok in tokens:
        if not tok:
            continue
        if re.match(r"^[^\w\s]$", tok) and tok not in "([{«":
            text = text.rstrip() + tok + " "
        else:
            text += tok + " "
    return re.sub(r"\s+", " ", text).strip()
