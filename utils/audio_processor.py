#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de traitement audio pour le Transcripteur Audio Pro
Optimisé pour les ingénieurs son et vidéastes
"""

import os
import tempfile
import logging
import numpy as np
from typing import Tuple, Optional
from pathlib import Path

# Traitement audio
try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from pydub import AudioSegment
    from pydub.effects import normalize, compress_dynamic_range
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Classe pour le traitement et l'amélioration audio"""
    
    def __init__(self):
        self.target_sr = 16000  # Fréquence d'échantillonnage cible pour Whisper
        
        # Vérifier les dépendances disponibles
        self.check_dependencies()
    
    def check_dependencies(self):
        """Vérifie les dépendances disponibles"""
        logger.info(f"LibROSA disponible: {LIBROSA_AVAILABLE}")
        logger.info(f"PyDub disponible: {PYDUB_AVAILABLE}")
        logger.info(f"NoiseReduce disponible: {NOISEREDUCE_AVAILABLE}")
        
        if not (LIBROSA_AVAILABLE or PYDUB_AVAILABLE):
            logger.warning("Aucune bibliothèque de traitement audio disponible!")
    
    def load_audio(self, file_path: str, target_sr: Optional[int] = None) -> Tuple[np.ndarray, int]:
        """
        Charge un fichier audio et le convertit au format requis
        
        Args:
            file_path: Chemin vers le fichier audio
            target_sr: Fréquence d'échantillonnage cible
            
        Returns:
            Tuple (audio_data, sample_rate)
        """
        if target_sr is None:
            target_sr = self.target_sr
            
        try:
            if LIBROSA_AVAILABLE:
                # Méthode préférée avec LibROSA
                audio, sr = librosa.load(file_path, sr=target_sr, mono=True)
                logger.debug(f"Audio chargé avec LibROSA: {len(audio)} samples à {sr}Hz")
                return audio, sr
                
            elif PYDUB_AVAILABLE:
                # Fallback avec PyDub
                audio_segment = AudioSegment.from_file(file_path)
                audio_segment = audio_segment.set_channels(1).set_frame_rate(target_sr)
                
                # Convertir en numpy array
                audio_data = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
                audio_data = audio_data / np.iinfo(audio_segment.array_type).max
                
                logger.debug(f"Audio chargé avec PyDub: {len(audio_data)} samples à {target_sr}Hz")
                return audio_data, target_sr
            else:
                raise Exception("Aucune bibliothèque de traitement audio disponible")
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement audio: {e}")
            raise
    
    def enhance_audio(self, audio: np.ndarray, sr: int, 
                     noise_reduction: float = 0.5,
                     amplification: float = 0,
                     normalize_audio: bool = True,
                     bass_boost: float = 0,
                     treble_boost: float = 0) -> np.ndarray:
        """
        Améliore la qualité audio
        
        Args:
            audio: Signal audio en numpy array
            sr: Fréquence d'échantillonnage
            noise_reduction: Niveau de réduction de bruit (0-1)
            amplification: Amplification en dB
            normalize_audio: Normaliser l'audio
            bass_boost: Boost des graves en dB
            treble_boost: Boost des aigus en dB
            
        Returns:
            Signal audio amélioré
        """
        try:
            enhanced_audio = audio.copy()
            
            # Réduction de bruit
            if noise_reduction > 0 and NOISEREDUCE_AVAILABLE:
                logger.debug(f"Application réduction de bruit: {noise_reduction}")
                enhanced_audio = nr.reduce_noise(
                    y=enhanced_audio, 
                    sr=sr, 
                    prop_decrease=noise_reduction,
                    stationary=False  # Plus efficace pour la parole
                )
            
            # Égaliseur basique (simulation)
            if bass_boost != 0 or treble_boost != 0:
                enhanced_audio = self._apply_simple_eq(enhanced_audio, sr, bass_boost, treble_boost)
            
            # Amplification
            if amplification != 0:
                gain = 10 ** (amplification / 20)  # Conversion dB vers gain linéaire
                enhanced_audio = enhanced_audio * gain
                logger.debug(f"Amplification appliquée: {amplification}dB (gain: {gain:.2f})")
            
            # Normalisation
            if normalize_audio:
                peak = np.max(np.abs(enhanced_audio))
                if peak > 0:
                    enhanced_audio = enhanced_audio / peak * 0.95  # Éviter la saturation
                    logger.debug("Normalisation appliquée")
            
            # Limiter les valeurs pour éviter la distorsion
            enhanced_audio = np.clip(enhanced_audio, -1.0, 1.0)
            
            return enhanced_audio
            
        except Exception as e:
            logger.error(f"Erreur lors de l'amélioration audio: {e}")
            return audio
    
    def _apply_simple_eq(self, audio: np.ndarray, sr: int, bass_boost: float, treble_boost: float) -> np.ndarray:
        """Applique un égaliseur simple (simulation)"""
        try:
            if not LIBROSA_AVAILABLE:
                return audio
                
            # Simulation basique d'égaliseur
            # En production, utiliser un vrai filtre
            if bass_boost != 0:
                # Boost des basses fréquences (< 200Hz)
                bass_gain = 10 ** (bass_boost / 20)
                audio = audio * (1 + (bass_gain - 1) * 0.3)  # Application partielle
            
            if treble_boost != 0:
                # Boost des hautes fréquences (> 2000Hz)
                treble_gain = 10 ** (treble_boost / 20)
                audio = audio * (1 + (treble_gain - 1) * 0.3)  # Application partielle
            
            return audio
        except Exception as e:
            logger.warning(f"Erreur égaliseur: {e}")
            return audio
    
    def enhance_audio_file(self, input_path: str, 
                          noise_reduction: float = 0.5,
                          amplification: float = 0,
                          normalize_audio: bool = True,
                          bass_boost: float = 0,
                          treble_boost: float = 0) -> str:
        """
        Améliore un fichier audio et retourne le chemin du fichier amélioré
        
        Args:
            input_path: Chemin du fichier d'entrée
            noise_reduction: Niveau de réduction de bruit
            amplification: Amplification en dB
            normalize_audio: Normaliser l'audio
            bass_boost: Boost des graves
            treble_boost: Boost des aigus
            
        Returns:
            Chemin du fichier audio amélioré
        """
        try:
            # Charger l'audio
            audio_data, sr = self.load_audio(input_path)
            
            # Améliorer l'audio
            enhanced_audio = self.enhance_audio(
                audio_data, sr, noise_reduction, amplification, 
                normalize_audio, bass_boost, treble_boost
            )
            
            # Sauvegarder le fichier amélioré
            output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            
            if LIBROSA_AVAILABLE:
                sf.write(output_path, enhanced_audio, sr)
            elif PYDUB_AVAILABLE:
                # Convertir en format PyDub
                enhanced_audio_int = (enhanced_audio * 32767).astype(np.int16)
                audio_segment = AudioSegment(
                    enhanced_audio_int.tobytes(),
                    frame_rate=sr,
                    sample_width=2,
                    channels=1
                )
                audio_segment.export(output_path, format='wav')
            
            logger.info(f"Fichier audio amélioré sauvegardé: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erreur lors de l'amélioration du fichier: {e}")
            raise
    
    def extract_segment(self, input_path: str, start_time: float, end_time: float) -> str:
        """
        Extrait un segment audio entre deux temps
        
        Args:
            input_path: Chemin du fichier d'entrée
            start_time: Temps de début en secondes
            end_time: Temps de fin en secondes
            
        Returns:
            Chemin du fichier segment extrait
        """
        try:
            if PYDUB_AVAILABLE:
                # Méthode préférée avec PyDub pour la précision temporelle
                audio_segment = AudioSegment.from_file(input_path)
                start_ms = int(start_time * 1000)
                end_ms = int(end_time * 1000)
                
            elif LIBROSA_AVAILABLE:
                # Fallback avec LibROSA
                audio_data, sr = self.load_audio(input_path)
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                
                segment = audio_data[start_sample:end_sample]
                
                output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
                sf.write(output_path, segment, sr)
            else:
                raise Exception("Aucune bibliothèque disponible pour l'extraction")
            
            logger.info(f"Segment extrait: {start_time}s-{end_time}s -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du segment: {e}")
            raise
    
    def get_audio_info(self, file_path: str) -> dict:
        """
        Récupère les informations d'un fichier audio
        
        Args:
            file_path: Chemin du fichier audio
            
        Returns:
            Dictionnaire avec les informations audio
        """
        try:
            if PYDUB_AVAILABLE:
                audio_segment = AudioSegment.from_file(file_path)
                
                return {
                    "duration": len(audio_segment) / 1000.0,  # en secondes
                    "sample_rate": audio_segment.frame_rate,
                    "channels": audio_segment.channels,
                    "format": audio_segment.sample_width * 8,  # bits
                    "file_size": os.path.getsize(file_path)
                }
                
            elif LIBROSA_AVAILABLE:
                audio_data, sr = librosa.load(file_path, sr=None)
                
                return {
                    "duration": len(audio_data) / sr,
                    "sample_rate": sr,
                    "channels": 1,  # LibROSA charge en mono par défaut
                    "format": "32-bit float",
                    "file_size": os.path.getsize(file_path)
                }
            else:
                # Informations basiques sans traitement
                return {
                    "file_size": os.path.getsize(file_path),
                    "format": Path(file_path).suffix
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos audio: {e}")
            return {"error": str(e)}
    
    def convert_to_wav(self, input_path: str, target_sr: Optional[int] = None) -> str:
        """
        Convertit un fichier audio au format WAV
        
        Args:
            input_path: Chemin du fichier d'entrée
            target_sr: Fréquence d'échantillonnage cible
            
        Returns:
            Chemin du fichier WAV converti
        """
        try:
            if target_sr is None:
                target_sr = self.target_sr
                
            if PYDUB_AVAILABLE:
                audio = AudioSegment.from_file(input_path)
                audio = audio.set_channels(1).set_frame_rate(target_sr)
                
                output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
                audio.export(output_path, format='wav')
                
            elif LIBROSA_AVAILABLE:
                audio_data, sr = librosa.load(input_path, sr=target_sr, mono=True)
                
                output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
                sf.write(output_path, audio_data, sr)
            else:
                # Si aucune bibliothèque n'est disponible, retourner le fichier original
                logger.warning("Aucune bibliothèque de conversion disponible")
                return input_path
            
            logger.info(f"Fichier converti en WAV: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion WAV: {e}")
            return input_path
    
    def analyze_audio_quality(self, audio: np.ndarray, sr: int) -> dict:
        """
        Analyse la qualité d'un signal audio
        
        Args:
            audio: Signal audio
            sr: Fréquence d'échantillonnage
            
        Returns:
            Dictionnaire avec les métriques de qualité
        """
        try:
            # Calcul des métriques basiques
            rms = np.sqrt(np.mean(audio**2))
            peak = np.max(np.abs(audio))
            dynamic_range = 20 * np.log10(peak / (rms + 1e-10))
            
            # Détection de saturation
            saturation_ratio = np.sum(np.abs(audio) > 0.95) / len(audio)
            
            # Estimation du bruit (simple)
            # Prendre les 10% plus faibles en amplitude comme estimation du bruit
            sorted_audio = np.sort(np.abs(audio))
            noise_floor = np.mean(sorted_audio[:int(len(sorted_audio) * 0.1)])
            snr_estimate = 20 * np.log10(rms / (noise_floor + 1e-10))
            
            return {
                "rms_level": float(rms),
                "peak_level": float(peak),
                "dynamic_range_db": float(dynamic_range),
                "saturation_ratio": float(saturation_ratio),
                "estimated_snr_db": float(snr_estimate),
                "needs_normalization": peak < 0.1 or peak > 0.95,
                "needs_noise_reduction": snr_estimate < 20,
                "quality_score": self._calculate_quality_score(rms, peak, dynamic_range, saturation_ratio, snr_estimate)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de qualité: {e}")
            return {"error": str(e)}
    
    def _calculate_quality_score(self, rms: float, peak: float, dynamic_range: float, 
                                saturation_ratio: float, snr: float) -> float:
        """
        Calcule un score de qualité audio (0-100)
        
        Args:
            rms: Niveau RMS
            peak: Niveau de crête
            dynamic_range: Plage dynamique
            saturation_ratio: Ratio de saturation
            snr: Rapport signal/bruit estimé
            
        Returns:
            Score de qualité (0-100)
        """
        try:
            score = 100.0
            
            # Pénalité pour saturation
            score -= saturation_ratio * 50
            
            # Pénalité pour niveau trop faible ou trop élevé
            if peak < 0.1:
                score -= 20
            elif peak > 0.95:
                score -= 30
            
            # Bonus pour bon SNR
            if snr > 30:
                score += 10
            elif snr < 10:
                score -= 20
            
            # Bonus pour bonne plage dynamique
            if 10 < dynamic_range < 40:
                score += 10
            
            return max(0, min(100, score))
            
        except Exception:
            return 50.0  # Score neutre en cas d'erreur
    
    def suggest_enhancements(self, file_path: str) -> dict:
        """
        Suggère des améliorations basées sur l'analyse audio
        
        Args:
            file_path: Chemin du fichier audio
            
        Returns:
            Dictionnaire avec les suggestions d'amélioration
        """
        try:
            # Charger et analyser l'audio
            audio_data, sr = self.load_audio(file_path)
            quality_analysis = self.analyze_audio_quality(audio_data, sr)
            
            suggestions = {
                "recommended_settings": {},
                "reasons": [],
                "priority": "low"
            }
            
            # Suggestions basées sur l'analyse
            if quality_analysis.get("needs_normalization", False):
                suggestions["recommended_settings"]["normalize"] = True
                suggestions["reasons"].append("Niveau audio non optimal")
                suggestions["priority"] = "medium"
            
            if quality_analysis.get("needs_noise_reduction", False):
                suggestions["recommended_settings"]["noise_reduction"] = 0.7
                suggestions["reasons"].append("Bruit de fond détecté")
                suggestions["priority"] = "high"
            
            if quality_analysis.get("peak_level", 0) < 0.1:
                suggestions["recommended_settings"]["amplification"] = 6
                suggestions["reasons"].append("Signal trop faible")
                suggestions["priority"] = "high"
            
            if quality_analysis.get("saturation_ratio", 0) > 0.01:
                suggestions["recommended_settings"]["amplification"] = -3
                suggestions["reasons"].append("Saturation détectée")
                suggestions["priority"] = "high"
            
            suggestions["quality_analysis"] = quality_analysis
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de suggestions: {e}")
            return {"error": str(e)}
    
    def batch_process(self, file_paths: list, enhancement_settings: dict) -> list:
        """
        Traite plusieurs fichiers audio en lot
        
        Args:
            file_paths: Liste des chemins de fichiers
            enhancement_settings: Paramètres d'amélioration
            
        Returns:
            Liste des chemins des fichiers traités
        """
        processed_files = []
        
        for file_path in file_paths:
            try:
                enhanced_path = self.enhance_audio_file(
                    file_path,
                    **enhancement_settings
                )
                processed_files.append(enhanced_path)
                logger.info(f"Fichier traité: {file_path} -> {enhanced_path}")
                
            except Exception as e:
                logger.error(f"Erreur lors du traitement de {file_path}: {e}")
                processed_files.append(None)
        
        return processed_files_segment[start_ms:end_ms]
                
                output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
                segment.export(output_path, format='wav')
                
            elif LIBROSA_AVAILABLE:
                # Fallback avec LibROSA
                audio_data, sr = self.load_audio(input_path)
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                
                segment = audio