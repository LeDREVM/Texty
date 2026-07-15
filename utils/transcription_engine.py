#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moteur de transcription pour le Transcripteur Audio Pro
Support multiple des engines de transcription
Créé par Négus Dja pour les ingénieurs son et vidéastes
"""

import os
import json
import logging
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path
import time

# Moteurs de transcription - Support multiple pour robustesse
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

# Support pour la détection de locuteurs (optionnel)
try:
    import torch
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)

class TranscriptionEngine:
    """Moteur de transcription avec support multiple d'engines"""
    
    def __init__(self):
        self.models = {}
        self.current_model_size = None
        self.supported_languages = {
            'auto': None,
            'fr': 'fr',
            'en': 'en',
            'es': 'es',
            'de': 'de',
            'it': 'it',
            'pt': 'pt',
            'ru': 'ru',
            'zh': 'zh',
            'ja': 'ja',
            'ar': 'ar',
            'hi': 'hi',
            'ko': 'ko',
            'nl': 'nl',
            'sv': 'sv'
        }
        
        # Initialiser les moteurs disponibles
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialise les moteurs de transcription disponibles"""
        logger.info("🧠 Initialisation des moteurs de transcription...")
        
        available_engines = []
        
        if FASTER_WHISPER_AVAILABLE:
            try:
                # Faster Whisper est prioritaire (plus rapide)
                logger.info("✅ Faster Whisper disponible")
                available_engines.append("faster_whisper")
            except Exception as e:
                logger.warning(f"❌ Erreur Faster Whisper: {e}")
        
        if WHISPER_AVAILABLE:
            try:
                logger.info("✅ Whisper standard disponible")
                available_engines.append("whisper")
            except Exception as e:
                logger.warning(f"❌ Erreur Whisper: {e}")
        
        if SPEECH_RECOGNITION_AVAILABLE:
            try:
                logger.info("✅ SpeechRecognition disponible (fallback)")
                available_engines.append("speech_recognition")
            except Exception as e:
                logger.warning(f"❌ Erreur SpeechRecognition: {e}")
        
        if not available_engines:
            # On n'échoue pas au démarrage : l'interface web et les endpoints
            # d'information doivent rester disponibles. L'erreur est levée seulement
            # au moment où une transcription est réellement demandée (voir transcribe()).
            logger.warning(
                "⚠️ Aucun moteur de transcription disponible - "
                "installez faster-whisper, openai-whisper ou SpeechRecognition"
            )
        else:
            logger.info(f"🎯 Moteurs disponibles: {', '.join(available_engines)}")

        self.available_engines = available_engines
    
    def get_available_engines(self) -> Dict[str, bool]:
        """Retourne l'état des moteurs disponibles"""
        return {
            "faster_whisper": FASTER_WHISPER_AVAILABLE,
            "whisper": WHISPER_AVAILABLE,
            "speech_recognition": SPEECH_RECOGNITION_AVAILABLE,
            "torch": TORCH_AVAILABLE
        }
    
    def load_model(self, model_size: str = "small", force_reload: bool = False):
        """
        Charge un modèle Whisper
        
        Args:
            model_size: Taille du modèle (tiny, base, small, medium, large)
            force_reload: Forcer le rechargement du modèle
        """
        if self.current_model_size == model_size and not force_reload:
            logger.debug(f"Modèle {model_size} déjà chargé")
            return
        
        try:
            if FASTER_WHISPER_AVAILABLE:
                logger.info(f"🔄 Chargement du modèle Faster Whisper: {model_size}")
                
                # Configuration optimisée pour Hostinger (CPU)
                device = "cpu"
                compute_type = "int8"  # Plus léger en mémoire
                
                # Créer le modèle
                model = WhisperModel(
                    model_size,
                    device=device,
                    compute_type=compute_type,
                    download_root="./models"
                )
                
                self.models["faster_whisper"] = model
                self.current_model_size = model_size
                logger.info(f"✅ Modèle Faster Whisper {model_size} chargé")
                
            elif WHISPER_AVAILABLE:
                logger.info(f"🔄 Chargement du modèle Whisper standard: {model_size}")
                
                model = whisper.load_model(
                    model_size,
                    download_root="./models"
                )
                
                self.models["whisper"] = model
                self.current_model_size = model_size
                logger.info(f"✅ Modèle Whisper {model_size} chargé")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement du modèle {model_size}: {e}")
            raise
    
    def transcribe(self, audio_path: str, 
                  language: str = "fr",
                  model_size: str = "small",
                  enable_speakers: bool = False,
                  enable_timestamps: bool = True) -> Dict[str, Any]:
        """
        Transcrit un fichier audio
        
        Args:
            audio_path: Chemin vers le fichier audio
            language: Code de langue (fr, en, etc.)
            model_size: Taille du modèle Whisper
            enable_speakers: Activer la détection de locuteurs
            enable_timestamps: Inclure les timestamps
            
        Returns:
            Dictionnaire avec le résultat de la transcription
        """
        start_time = time.time()
        
        try:
            logger.info(f"🎯 Début transcription: {Path(audio_path).name}")
            logger.info(f"📋 Paramètres: langue={language}, modèle={model_size}, locuteurs={enable_speakers}")
            
            # Charger le modèle si nécessaire
            if model_size != self.current_model_size:
                self.load_model(model_size)
            
            # Choisir le meilleur moteur disponible
            if "faster_whisper" in self.available_engines:
                result = self._transcribe_faster_whisper(
                    audio_path, language, enable_speakers, enable_timestamps
                )
            elif "whisper" in self.available_engines:
                result = self._transcribe_whisper(
                    audio_path, language, enable_speakers, enable_timestamps
                )
            elif "speech_recognition" in self.available_engines:
                result = self._transcribe_speech_recognition(audio_path, language)
            else:
                raise Exception("Aucun moteur de transcription disponible")
            
            # Ajouter les métadonnées
            processing_time = time.time() - start_time
            result["processing_time"] = processing_time
            result["model_used"] = model_size
            result["language_requested"] = language
            
            logger.info(f"✅ Transcription terminée en {processing_time:.2f}s")
            logger.info(f"📝 Résultat: {len(result.get('text', ''))} caractères")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la transcription: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "segments": [],
                "processing_time": time.time() - start_time
            }
    
    def _transcribe_faster_whisper(self, audio_path: str, language: str, 
                                  enable_speakers: bool, enable_timestamps: bool) -> Dict[str, Any]:
        """Transcription avec Faster Whisper (méthode prioritaire)"""
        try:
            model = self.models.get("faster_whisper")
            if not model:
                raise Exception("Modèle Faster Whisper non chargé")
            
            # Paramètres de transcription
            language_code = self.supported_languages.get(language)
            
            # Options avancées pour une meilleure précision
            transcribe_options = {
                "language": language_code,
                "vad_filter": True,  # Détection d'activité vocale
                "vad_parameters": {
                    "min_silence_duration_ms": 500,  # Pause minimum pour découper
                    "max_speech_duration_s": 30,     # Durée max d'un segment
                    "min_speech_duration_ms": 250,   # Durée min pour être considéré comme parole
                },
                "beam_size": 5,      # Meilleure précision avec beam search
                "best_of": 5,        # Essayer 5 hypothèses et prendre la meilleure
                "temperature": 0,    # Déterministe pour la reproductibilité
                "compression_ratio_threshold": 2.4,  # Éviter les répétitions
                "log_prob_threshold": -1.0,
                "no_speech_threshold": 0.6,
                "condition_on_previous_text": True,  # Utiliser le contexte précédent
                "prompt_reset_on_temperature": 0.5,
                "initial_prompt": self._get_initial_prompt(language),
                "word_timestamps": enable_timestamps
            }
            
            # Lancer la transcription
            segments, info = model.transcribe(audio_path, **transcribe_options)
            
            # Traiter les résultats
            transcript_segments = []
            full_text = []
            
            for segment in segments:
                segment_dict = {
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                    "confidence": round(getattr(segment, 'avg_logprob', 0.0), 3)
                }
                
                # Ajouter les mots avec timestamps si disponible
                if enable_timestamps and hasattr(segment, 'words'):
                    segment_dict["words"] = [
                        {
                            "word": word.word,
                            "start": round(word.start, 2),
                            "end": round(word.end, 2),
                            "confidence": round(word.probability, 3)
                        }
                        for word in segment.words
                    ]
                
                transcript_segments.append(segment_dict)
                full_text.append(segment.text)
            
            # Post-traitement du texte
            final_text = self._post_process_text(" ".join(full_text).strip(), language)
            
            return {
                "success": True,
                "text": final_text,
                "segments": transcript_segments,
                "language_detected": info.language,
                "language_probability": round(info.language_probability, 3),
                "engine": "faster_whisper",
                "duration": info.duration,
                "all_language_probs": getattr(info, 'all_language_probs', None)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur Faster Whisper: {e}")
            raise
    
    def _transcribe_whisper(self, audio_path: str, language: str, 
                           enable_speakers: bool, enable_timestamps: bool) -> Dict[str, Any]:
        """Transcription avec Whisper standard"""
        try:
            model = self.models.get("whisper")
            if not model:
                # Charger le modèle à la volée (taille demandée si connue)
                self.load_model(self.current_model_size or "small")
                model = self.models["whisper"]
            
            language_code = self.supported_languages.get(language)
            
            # Options de transcription
            options = {
                "language": language_code,
                "task": "transcribe",
                "verbose": False,
                "temperature": 0,
                "beam_size": 5,
                "best_of": 5,
                "fp16": False,  # Compatibilité CPU
                "condition_on_previous_text": True,
                "initial_prompt": self._get_initial_prompt(language),
                "word_timestamps": enable_timestamps
            }
            
            # Lancer la transcription
            result = model.transcribe(audio_path, **options)
            
            # Traiter les segments
            segments = []
            for segment in result.get("segments", []):
                segment_dict = {
                    "start": round(segment["start"], 2),
                    "end": round(segment["end"], 2),
                    "text": segment["text"].strip(),
                    "confidence": round(segment.get("avg_logprob", 0.0), 3)
                }
                
                # Ajouter les mots si disponible
                if enable_timestamps and "words" in segment:
                    segment_dict["words"] = [
                        {
                            "word": word["word"],
                            "start": round(word["start"], 2),
                            "end": round(word["end"], 2),
                            "confidence": round(word.get("probability", 0.8), 3)
                        }
                        for word in segment["words"]
                    ]
                
                segments.append(segment_dict)
            
            # Post-traitement
            final_text = self._post_process_text(result["text"].strip(), language)
            
            return {
                "success": True,
                "text": final_text,
                "segments": segments,
                "language_detected": result.get("language", "unknown"),
                "engine": "whisper"
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur Whisper standard: {e}")
            raise
    
    def _transcribe_speech_recognition(self, audio_path: str, language: str) -> Dict[str, Any]:
        """Transcription avec SpeechRecognition (fallback)"""
        try:
            recognizer = sr.Recognizer()
            
            # Mapper les codes de langue
            lang_map = {
                "fr": "fr-FR",
                "en": "en-US",
                "es": "es-ES",
                "de": "de-DE",
                "it": "it-IT",
                "pt": "pt-PT",
                "ru": "ru-RU",
                "zh": "zh-CN",
                "ja": "ja-JP",
                "ar": "ar-SA"
            }
            
            recognition_language = lang_map.get(language, "fr-FR")
            
            # Charger le fichier audio
            with sr.AudioFile(audio_path) as source:
                # Ajuster le bruit ambiant
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.record(source)
            
            # Reconnaissance avec Google
            text = recognizer.recognize_google(
                audio, 
                language=recognition_language,
                show_all=False
            )
            
            return {
                "success": True,
                "text": self._post_process_text(text, language),
                "segments": [{
                    "start": 0,
                    "end": 0,  # Pas d'info de timing disponible
                    "text": text,
                    "confidence": 0.8  # Estimation
                }],
                "language_detected": language,
                "engine": "speech_recognition"
            }
            
        except sr.UnknownValueError:
            return {
                "success": False,
                "error": "Aucune parole détectée dans l'audio",
                "text": "",
                "segments": []
            }
        except sr.RequestError as e:
            return {
                "success": False,
                "error": f"Erreur du service de reconnaissance: {e}",
                "text": "",
                "segments": []
            }
        except Exception as e:
            logger.error(f"❌ Erreur SpeechRecognition: {e}")
            raise
    
    def _get_initial_prompt(self, language: str) -> str:
        """Retourne un prompt initial pour améliorer la précision selon la langue"""
        prompts = {
            "fr": "Voici une transcription précise en français avec ponctuation correcte:",
            "en": "Here is an accurate English transcription with proper punctuation:",
            "es": "Aquí hay una transcripción precisa en español con puntuación correcta:",
            "de": "Hier ist eine genaue deutsche Transkription mit korrekter Zeichensetzung:",
            "it": "Ecco una trascrizione accurata in italiano con punteggiatura corretta:",
            "pt": "Aqui está uma transcrição precisa em português com pontuação correta:"
        }
        
        return prompts.get(language, prompts["fr"])
    
    def _post_process_text(self, text: str, language: str) -> str:
        """Post-traitement du texte transcrit"""
        try:
            # Nettoyage basique
            text = text.strip()
            
            # Corrections spécifiques selon la langue
            if language == "fr":
                text = self._correct_french_text(text)
            elif language == "en":
                text = self._correct_english_text(text)
            
            # Corrections générales
            text = self._apply_general_corrections(text)
            
            return text
            
        except Exception as e:
            logger.warning(f"Erreur post-traitement: {e}")
            return text
    
    def _correct_french_text(self, text: str) -> str:
        """Corrections spécifiques au français"""
        corrections = {
            " d' ": " d'",
            " l' ": " l'",
            " c' ": " c'",
            " n' ": " n'",
            " s' ": " s'",
            " j' ": " j'",
            " m' ": " m'",
            " t' ": " t'",
            "qu' ": "qu'",
            "aujourd' hui": "aujourd'hui",
            "c' est": "c'est",
            "n' est": "n'est",
            "s' il": "s'il",
            "d' abord": "d'abord",
            "d' accord": "d'accord"
        }
        
        for wrong, correct in corrections.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def _correct_english_text(self, text: str) -> str:
        """Corrections spécifiques à l'anglais"""
        corrections = {
            " i ": " I ",
            " i'": " I'",
            "i'm": "I'm",
            "i'll": "I'll",
            "i've": "I've",
            "i'd": "I'd",
            "can't": "can't",
            "won't": "won't",
            "don't": "don't",
            "didn't": "didn't",
            "wouldn't": "wouldn't",
            "shouldn't": "shouldn't"
        }
        
        for wrong, correct in corrections.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def _apply_general_corrections(self, text: str) -> str:
        """Corrections générales pour toutes les langues"""
        import re
        
        # Supprimer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        # Corriger la ponctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        text = re.sub(r'([.,!?;:])\s*([.,!?;:])', r'\1 \2', text)
        
        # Majuscules après ponctuation
        text = re.sub(r'([.!?])\s+([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
        
        # Première lettre en majuscule
        if text:
            text = text[0].upper() + text[1:]
        
        return text.strip()
    
    def detect_speakers(self, audio_path: str, min_speakers: int = 1, max_speakers: int = 10) -> Dict[str, Any]:
        """
        Détecte et sépare les locuteurs dans l'audio (fonctionnalité avancée)
        
        Args:
            audio_path: Chemin vers le fichier audio
            min_speakers: Nombre minimum de locuteurs
            max_speakers: Nombre maximum de locuteurs
            
        Returns:
            Dictionnaire avec les informations de locuteurs
        """
        try:
            if not TORCH_AVAILABLE:
                logger.warning("PyTorch non disponible - détection de locuteurs désactivée")
                return {
                    "success": False,
                    "error": "PyTorch requis pour la détection de locuteurs",
                    "speakers": []
                }
            
            # Simulation de détection de locuteurs
            # En production, utiliser pyannote.audio ou similar-sounding
            logger.info("🎤 Détection de locuteurs (simulation)")
            
            # Pour l'instant, retourner une simulation
            return {
                "success": True,
                "speakers_detected": 2,  # Simulation
                "speakers": [
                    {
                        "speaker_id": "SPEAKER_01",
                        "segments": [
                            {"start": 0.0, "end": 5.2},
                            {"start": 8.1, "end": 12.3}
                        ]
                    },
                    {
                        "speaker_id": "SPEAKER_02", 
                        "segments": [
                            {"start": 5.2, "end": 8.1},
                            {"start": 12.3, "end": 18.7}
                        ]
                    }
                ],
                "note": "Fonctionnalité en développement - simulation"
            }
            
        except Exception as e:
            logger.error(f"Erreur détection de locuteurs: {e}")
            return {
                "success": False,
                "error": str(e),
                "speakers": []
            }
    
    def transcribe_with_speakers(self, audio_path: str, language: str = "fr", 
                                model_size: str = "small") -> Dict[str, Any]:
        """
        Transcrit avec détection de locuteurs
        
        Args:
            audio_path: Chemin vers le fichier audio
            language: Langue de transcription
            model_size: Taille du modèle
            
        Returns:
            Transcription avec attribution des locuteurs
        """
        try:
            # Transcription normale
            transcription_result = self.transcribe(
                audio_path, language, model_size, enable_speakers=True
            )
            
            if not transcription_result["success"]:
                return transcription_result
            
            # Détection de locuteurs
            speakers_result = self.detect_speakers(audio_path)
            
            # Fusionner les résultats
            if speakers_result["success"]:
                # Attribuer les segments aux locuteurs
                enhanced_segments = self._assign_speakers_to_segments(
                    transcription_result["segments"],
                    speakers_result["speakers"]
                )
                
                transcription_result["segments"] = enhanced_segments
                transcription_result["speakers_info"] = speakers_result
                transcription_result["has_speakers"] = True
            else:
                transcription_result["has_speakers"] = False
                transcription_result["speakers_error"] = speakers_result.get("error")
            
            return transcription_result
            
        except Exception as e:
            logger.error(f"Erreur transcription avec locuteurs: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "segments": []
            }
    
    def _assign_speakers_to_segments(self, transcription_segments: List[Dict], 
                                   speaker_segments: List[Dict]) -> List[Dict]:
        """Attribue les segments de transcription aux locuteurs"""
        try:
            enhanced_segments = []
            
            for trans_seg in transcription_segments:
                trans_start = trans_seg["start"]
                trans_end = trans_seg["end"]
                trans_mid = (trans_start + trans_end) / 2
                
                # Trouver le locuteur correspondant
                assigned_speaker = "UNKNOWN"
                
                for speaker in speaker_segments:
                    for spk_seg in speaker["segments"]:
                        if spk_seg["start"] <= trans_mid <= spk_seg["end"]:
                            assigned_speaker = speaker["speaker_id"]
                            break
                    if assigned_speaker != "UNKNOWN":
                        break
                
                # Ajouter l'info du locuteur
                enhanced_seg = trans_seg.copy()
                enhanced_seg["speaker"] = assigned_speaker
                enhanced_segments.append(enhanced_seg)
            
            return enhanced_segments
            
        except Exception as e:
            logger.error(f"Erreur attribution locuteurs: {e}")
            return transcription_segments
    
    def batch_transcribe(self, file_paths: List[str], 
                        common_settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transcrit plusieurs fichiers en lot
        
        Args:
            file_paths: Liste des chemins de fichiers
            common_settings: Paramètres communs pour tous les fichiers
            
        Returns:
            Liste des résultats de transcription
        """
        results = []
        
        logger.info(f"🔄 Transcription en lot: {len(file_paths)} fichiers")
        
        for i, file_path in enumerate(file_paths, 1):
            try:
                logger.info(f"📁 Traitement {i}/{len(file_paths)}: {Path(file_path).name}")
                
                result = self.transcribe(file_path, **common_settings)
                result["file_index"] = i
                result["file_name"] = Path(file_path).name
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Erreur fichier {file_path}: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "file_index": i,
                    "file_name": Path(file_path).name,
                    "text": "",
                    "segments": []
                })
        
        logger.info(f"✅ Transcription en lot terminée: {len(results)} résultats")
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Retourne les informations sur les modèles disponibles"""
        return {
            "current_model": self.current_model_size,
            "available_models": ["tiny", "base", "small", "medium", "large"],
            "model_descriptions": {
                "tiny": "Ultra rapide, précision limitée (39 MB)",
                "base": "Rapide, précision correcte (74 MB)", 
                "small": "Équilibré, recommandé (244 MB)",
                "medium": "Précis, plus lent (769 MB)",
                "large": "Maximum de précision (1550 MB)"
            },
            "supported_languages": list(self.supported_languages.keys()),
            "engines_status": self.get_available_engines()
        }
    
    def estimate_processing_time(self, audio_duration: float, model_size: str) -> float:
        """
        Estime le temps de traitement basé sur la durée audio et le modèle
        
        Args:
            audio_duration: Durée de l'audio en secondes
            model_size: Taille du modèle
            
        Returns:
            Temps estimé en secondes
        """
        # Facteurs basés sur des tests empiriques (CPU)
        time_factors = {
            "tiny": 0.1,    # 10% de la durée audio
            "base": 0.15,   # 15% de la durée audio
            "small": 0.25,  # 25% de la durée audio
            "medium": 0.4,  # 40% de la durée audio
            "large": 0.6    # 60% de la durée audio
        }
        
        factor = time_factors.get(model_size, 0.25)
        estimated_time = audio_duration * factor
        
        # Ajouter un overhead de base
        estimated_time += 5  # 5 secondes d'overhead
        
        return max(10, estimated_time)  # Minimum 10 secondes
    
    def validate_audio_for_transcription(self, audio_path: str) -> Dict[str, Any]:
        """
        Valide qu'un fichier audio est adapté à la transcription
        
        Args:
            audio_path: Chemin vers le fichier audio
            
        Returns:
            Résultat de validation avec recommandations
        """
        try:
            from utils.audio_processor import AudioProcessor
            
            processor = AudioProcessor()
            audio_info = processor.get_audio_info(audio_path)
            
            validation_result = {
                "is_valid": True,
                "warnings": [],
                "recommendations": [],
                "audio_info": audio_info
            }
            
            # Vérifications
            if audio_info.get("duration", 0) < 1:
                validation_result["warnings"].append("Fichier audio très court (< 1s)")
            
            if audio_info.get("duration", 0) > 3600:  # 1 heure
                validation_result["warnings"].append("Fichier audio très long (> 1h)")
                validation_result["recommendations"].append("Considérer découper en segments plus courts")
            
            if audio_info.get("sample_rate", 0) < 8000:
                validation_result["warnings"].append("Fréquence d'échantillonnage faible")
                validation_result["recommendations"].append("Qualité audio possiblement insuffisante")
            
            if audio_info.get("file_size", 0) > 100 * 1024 * 1024:  # 100 MB
                validation_result["warnings"].append("Fichier volumineux")
                validation_result["recommendations"].append("Considérer compresser l'audio")
            
            # Suggestions de modèle basées sur la durée
            duration = audio_info.get("duration", 0)
            if duration < 300:  # < 5 minutes
                validation_result["recommended_model"] = "small"
            elif duration < 1800:  # < 30 minutes
                validation_result["recommended_model"] = "small"
            else:  # > 30 minutes
                validation_result["recommended_model"] = "base"  # Plus rapide pour les longs audios
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Erreur validation audio: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "warnings": [],
                "recommendations": []
            }
    
    def cleanup_models(self):
        """Nettoie les modèles chargés en mémoire"""
        try:
            self.models.clear()
            self.current_model_size = None
            logger.info("🧹 Modèles nettoyés de la mémoire")
        except Exception as e:
            logger.error(f"Erreur nettoyage modèles: {e}")
    
    def get_transcription_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur les transcriptions"""
        return {
            "engines_available": len(self.available_engines),
            "primary_engine": self.available_engines[0] if self.available_engines else None,
            "languages_supported": len(self.supported_languages),
            "current_model": self.current_model_size,
            "memory_usage": "Optimisé pour Hostinger",
            "performance_mode": "CPU optimized"
        }