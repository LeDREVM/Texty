#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transcripteur Audio Pro - Application Flask principale
Créé par Négus Dja pour les ingénieurs son et vidéastes
Optimisé pour l'hébergement sur Hostinger
"""

import os
import io
import json
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime

# Framework web
from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Utilitaires du projet
from utils.audio_processor import AudioProcessor
from utils.transcription_engine import TranscriptionEngine
from utils.format_converter import FormatConverter

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialisation Flask
app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMP_FOLDER'] = 'temp'
app.config['MODELS_FOLDER'] = 'models'

# Créer les dossiers nécessaires
for folder in ['uploads', 'temp', 'models', 'logs']:
    os.makedirs(folder, exist_ok=True)

# Types de fichiers autorisés
ALLOWED_EXTENSIONS = {
    'audio': {'mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg', 'wma'},
    'video': {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}
}

# Langues supportées
SUPPORTED_LANGUAGES = {
    'auto': 'Détection automatique',
    'fr': 'Français',
    'en': 'Anglais',
    'es': 'Espagnol',
    'de': 'Allemand',
    'it': 'Italien',
    'pt': 'Portugais',
    'ru': 'Russe',
    'zh': 'Chinois',
    'ja': 'Japonais',
    'ar': 'Arabe',
    'hi': 'Hindi',
    'ko': 'Coréen',
    'nl': 'Néerlandais',
    'sv': 'Suédois'
}

# Modèles Whisper
WHISPER_MODELS = {
    'tiny': 'Très rapide (moins précis)',
    'base': 'Rapide',
    'small': 'Équilibré (recommandé)',
    'medium': 'Précis',
    'large': 'Maximum de précision'
}

# Instances globales
audio_processor = AudioProcessor()
transcription_engine = TranscriptionEngine()
format_converter = FormatConverter()

def allowed_file(filename: str) -> bool:
    """Vérifie si le type de fichier est autorisé"""
    if '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS['audio'] or extension in ALLOWED_EXTENSIONS['video']

@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Servir les fichiers statiques"""
    return send_from_directory('static', filename)

@app.route('/api/health')
def health_check():
    """Vérification de l'état du service"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "author": "Négus Dja",
        "engines": transcription_engine.get_available_engines(),
        "languages": list(SUPPORTED_LANGUAGES.keys()),
        "models": list(WHISPER_MODELS.keys()),
        "max_file_size_mb": app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
    })

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """Endpoint principal de transcription"""
    start_time = datetime.now()
    
    try:
        # Vérifier qu'un fichier a été envoyé
        if 'audio' not in request.files:
            return jsonify({"error": "Aucun fichier audio fourni"}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({"error": "Nom de fichier vide"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Type de fichier non supporté"}), 400
        
        # Paramètres de transcription
        language = request.form.get('language', 'fr')
        model_size = request.form.get('model', 'small')
        enable_speakers = request.form.get('speakers', 'false').lower() == 'true'
        enhance_audio = request.form.get('enhance', 'false').lower() == 'true'
        output_format = request.form.get('format', 'text')
        
        # Paramètres d'amélioration audio
        noise_reduction = float(request.form.get('noise_reduction', 0.5))
        amplification = float(request.form.get('amplification', 0))
        normalize_audio = request.form.get('normalize', 'true').lower() == 'true'
        
        logger.info(f"Début transcription: {file.filename}, langue: {language}, modèle: {model_size}")
        
        # Sauvegarder le fichier temporairement
        filename = secure_filename(file.filename)
        temp_input = os.path.join(app.config['TEMP_FOLDER'], f"input_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        file.save(temp_input)
        
        try:
            # Traitement audio
            processed_audio_path = temp_input
            
            if enhance_audio:
                logger.info("Application des améliorations audio...")
                processed_audio_path = audio_processor.enhance_audio_file(
                    temp_input, noise_reduction, amplification, normalize_audio
                )
            
            # Transcription
            result = transcription_engine.transcribe(
                processed_audio_path, 
                language=language,
                model_size=model_size,
                enable_speakers=enable_speakers
            )
            
            # Conversion du format si nécessaire
            if output_format != 'text' and result['success']:
                converted_result = format_converter.convert(
                    result['text'], 
                    result.get('segments', []), 
                    output_format
                )
                result['formatted_output'] = converted_result
            
            # Calcul du temps de traitement
            processing_time = (datetime.now() - start_time).total_seconds()
            result['processing_time'] = processing_time
            result['filename'] = filename
            
            logger.info(f"Transcription terminée en {processing_time:.2f}s: {len(result.get('text', ''))} caractères")
            
            return jsonify(result)
            
        finally:
            # Nettoyage des fichiers temporaires
            cleanup_files = [temp_input]
            if enhance_audio and processed_audio_path != temp_input:
                cleanup_files.append(processed_audio_path)
            
            for file_path in cleanup_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Impossible de supprimer {file_path}: {e}")
            
    except RequestEntityTooLarge:
        return jsonify({"error": "Fichier trop volumineux (max 100MB)"}), 413
    except Exception as e:
        logger.error(f"Erreur lors de la transcription: {e}")
        return jsonify({
            "success": False,
            "error": f"Erreur de traitement: {str(e)}"
        }), 500

@app.route('/api/enhance', methods=['POST'])
def enhance_audio_endpoint():
    """Endpoint pour l'amélioration audio uniquement"""
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "Aucun fichier audio fourni"}), 400
        
        file = request.files['audio']
        if not allowed_file(file.filename):
            return jsonify({"error": "Type de fichier non supporté"}), 400
        
        # Paramètres d'amélioration
        noise_reduction = float(request.form.get('noise_reduction', 0.5))
        amplification = float(request.form.get('amplification', 0))
        normalize_audio = request.form.get('normalize', 'true').lower() == 'true'
        
        # Sauvegarder et traiter
        filename = secure_filename(file.filename)
        temp_input = os.path.join(app.config['TEMP_FOLDER'], f"enhance_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        file.save(temp_input)
        
        try:
            # Améliorer l'audio
            enhanced_path = audio_processor.enhance_audio_file(
                temp_input, noise_reduction, amplification, normalize_audio
            )
            
            # Retourner le fichier amélioré
            return send_file(
                enhanced_path,
                as_attachment=True,
                download_name=f"enhanced_{filename}",
                mimetype='audio/wav'
            )
            
        finally:
            # Nettoyage
            for file_path in [temp_input, enhanced_path]:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass
            
    except Exception as e:
        logger.error(f"Erreur d'amélioration: {e}")
        return jsonify({"error": f"Erreur de traitement: {str(e)}"}), 500

@app.route('/api/extract_segment', methods=['POST'])
def extract_audio_segment():
    """Endpoint pour extraire un segment audio"""
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "Aucun fichier audio fourni"}), 400
        
        file = request.files['audio']
        start_time = float(request.form.get('start_time', 0))
        end_time = float(request.form.get('end_time', 0))
        
        if end_time <= start_time:
            return jsonify({"error": "Temps de fin doit être supérieur au temps de début"}), 400
        
        # Sauvegarder le fichier temporairement
        filename = secure_filename(file.filename)
        temp_input = os.path.join(app.config['TEMP_FOLDER'], f"segment_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        file.save(temp_input)
        
        try:
            # Extraire le segment
            segment_path = audio_processor.extract_segment(
                temp_input, start_time, end_time
            )
            
            if not segment_path:
                return jsonify({"error": "Impossible d'extraire le segment"}), 500
            
            # Retourner le segment
            return send_file(
                segment_path,
                as_attachment=True,
                download_name=f"segment_{start_time:.1f}s-{end_time:.1f}s_{filename}",
                mimetype='audio/wav'
            )
            
        finally:
            # Nettoyage
            for file_path in [temp_input, segment_path]:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass
            
    except Exception as e:
        logger.error(f"Erreur d'extraction: {e}")
        return jsonify({"error": f"Erreur de traitement: {str(e)}"}), 500

@app.route('/api/formats', methods=['GET'])
def get_supported_formats():
    """Retourne les formats supportés"""
    return jsonify({
        "audio_formats": list(ALLOWED_EXTENSIONS['audio']),
        "video_formats": list(ALLOWED_EXTENSIONS['video']),
        "languages": SUPPORTED_LANGUAGES,
        "models": WHISPER_MODELS,
        "output_formats": ["text", "srt", "vtt", "json"]
    })

@app.route('/api/convert_format', methods=['POST'])
def convert_transcript_format():
    """Convertit un transcript vers différents formats"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        segments = data.get('segments', [])
        output_format = data.get('format', 'txt')
        
        if not text:
            return jsonify({"error": "Texte vide"}), 400
        
        result = format_converter.convert(text, segments, output_format)
        
        return jsonify({
            "success": True,
            "content": result,
            "format": output_format
        })
        
    except Exception as e:
        logger.error(f"Erreur de conversion: {e}")
        return jsonify({"error": f"Erreur de conversion: {str(e)}"}), 500

@app.route('/api/stats')
def get_stats():
    """Statistiques de l'application"""
    try:
        # Compter les fichiers dans les dossiers
        uploads_count = len([f for f in os.listdir('uploads') if os.path.isfile(os.path.join('uploads', f))])
        temp_count = len([f for f in os.listdir('temp') if os.path.isfile(os.path.join('temp', f))])
        
        return jsonify({
            "uploads_count": uploads_count,
            "temp_files": temp_count,
            "available_engines": transcription_engine.get_available_engines(),
            "uptime": "Running",
            "author": "Négus Dja - Directeur Artistique Guadeloupe"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Gestion des erreurs
@app.errorhandler(413)
def file_too_large(error):
    """Gestion des fichiers trop volumineux"""
    return jsonify({"error": "Fichier trop volumineux (limite: 100MB)"}), 413

@app.errorhandler(500)
def internal_error(error):
    """Gestion des erreurs internes"""
    logger.error(f"Erreur interne: {error}")
    return jsonify({"error": "Erreur interne du serveur"}), 500

@app.errorhandler(404)
def not_found(error):
    """Gestion des pages non trouvées"""
    return jsonify({"error": "Endpoint non trouvé"}), 404

# Configuration pour la production
def create_app():
    """Factory function pour la production"""
    return app

if __name__ == '__main__':
    # Mode développement
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    
    logger.info("🎙️ Transcripteur Audio Pro - Démarrage")
    logger.info(f"👨‍🎨 Créé par Négus Dja - Directeur Artistique")
    logger.info(f"🌍 Basé en Guadeloupe")
    logger.info(f"🎯 Optimisé pour les ingénieurs son et vidéastes avec TDAH")
    logger.info(f"🚀 Démarrage sur le port {port}")
    logger.info(f"🔧 Mode debug: {debug_mode}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)