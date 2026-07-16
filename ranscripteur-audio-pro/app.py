#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transcripteur Audio Pro - Application Flask principale
Créé par Négus Dja pour les ingénieurs son et vidéastes
Optimisé pour l'hébergement sur Hostinger
"""

import os
import sys
import uuid
import logging
from io import BytesIO
from pathlib import Path
from datetime import datetime

# Chemins de base, indépendants du répertoire de travail courant (CWD)
BASE_DIR = Path(__file__).resolve().parent      # .../ranscripteur-audio-pro
REPO_ROOT = BASE_DIR.parent                      # racine du dépôt

# Rendre le package 'utils' (situé à la racine du dépôt) importable quel que soit le CWD
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Framework web
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Utilitaires du projet
from utils.audio_processor import AudioProcessor
from utils.transcription_engine import TranscriptionEngine
from utils.format_converter import FormatConverter
from utils.creole_dictionary import CreoleDictionary
from utils.translator import Translator

# Créer les dossiers nécessaires AVANT de configurer le logging (sinon le
# FileHandler échoue sur un dépôt fraîchement cloné où logs/ n'existe pas encore)
UPLOAD_FOLDER = BASE_DIR / 'uploads'
TEMP_FOLDER = BASE_DIR / 'temp'
MODELS_FOLDER = BASE_DIR / 'models'
LOGS_FOLDER = BASE_DIR / 'logs'
for _folder in (UPLOAD_FOLDER, TEMP_FOLDER, MODELS_FOLDER, LOGS_FOLDER):
    _folder.mkdir(parents=True, exist_ok=True)

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_FOLDER / 'app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialisation Flask : templates dans ./templates, fichiers statiques à la racine du dépôt
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / 'templates'),
    static_folder=str(REPO_ROOT / 'static'),
)

# CORS restreint : par défaut même origine / localhost, surchargeable via CORS_ORIGINS
_cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000')
CORS(app, origins=[o.strip() for o in _cors_origins.split(',') if o.strip()])

# Configuration
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE', str(100 * 1024 * 1024)))
# Cache navigateur des fichiers statiques (secondes) — accélère les visites répétées
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = int(os.getenv('STATIC_MAX_AGE', '3600'))
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['TEMP_FOLDER'] = str(TEMP_FOLDER)
app.config['MODELS_FOLDER'] = str(MODELS_FOLDER)

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

# Formats de sortie autorisés pour la conversion
OUTPUT_FORMATS = {'text', 'srt', 'vtt', 'json', 'docx', 'csv'}

# Instances globales
audio_processor = AudioProcessor()
transcription_engine = TranscriptionEngine()
format_converter = FormatConverter()
creole_dictionary = CreoleDictionary()
translator = Translator(creole_dictionary)

# Directions de traduction autorisées pour le dictionnaire
DICTIONARY_DIRECTIONS = {'fr-cr', 'cr-fr', 'auto'}
TRANSLATE_DIRECTIONS = {'fr-cr', 'cr-fr'}

def allowed_file(filename: str) -> bool:
    """Vérifie si le type de fichier est autorisé"""
    if not filename or '.' not in filename:
        return False

    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS['audio'] or extension in ALLOWED_EXTENSIONS['video']

def parse_float(value, default: float, minimum: float = None, maximum: float = None) -> float:
    """Convertit une valeur de formulaire en float, avec bornes ; ValueError si invalide."""
    try:
        result = float(value) if value is not None else float(default)
    except (TypeError, ValueError):
        raise ValueError(f"Valeur numérique invalide: {value!r}")
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result

def safe_temp_path(prefix: str, filename: str) -> str:
    """Construit un chemin temporaire unique (évite les collisions entre requêtes)."""
    safe_name = secure_filename(filename) or 'audio'
    return os.path.join(app.config['TEMP_FOLDER'], f"{prefix}_{uuid.uuid4().hex}_{safe_name}")

@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

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
        "max_file_size_mb": app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024),
        "creole_dictionary": creole_dictionary.stats()
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
        
        # Paramètres de transcription (validés)
        language = request.form.get('language', 'fr')
        if language not in SUPPORTED_LANGUAGES:
            language = 'fr'
        model_size = request.form.get('model', 'small')
        if model_size not in WHISPER_MODELS:
            model_size = 'small'
        output_format = request.form.get('format', 'text')
        if output_format not in OUTPUT_FORMATS:
            return jsonify({"error": "Format de sortie non supporté"}), 400
        enable_speakers = request.form.get('speakers', 'false').lower() == 'true'
        enhance_audio = request.form.get('enhance', 'false').lower() == 'true'

        # Paramètres d'amélioration audio
        try:
            noise_reduction = parse_float(request.form.get('noise_reduction'), 0.5, 0.0, 1.0)
            amplification = parse_float(request.form.get('amplification'), 0, -30.0, 30.0)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        normalize_audio = request.form.get('normalize', 'true').lower() == 'true'

        logger.info(f"Début transcription: {file.filename}, langue: {language}, modèle: {model_size}")

        # Sauvegarder le fichier temporairement (nom unique pour éviter les collisions)
        filename = secure_filename(file.filename)
        temp_input = safe_temp_path('input', file.filename)
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
        limit_mb = app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
        return jsonify({"error": f"Fichier trop volumineux (max {limit_mb}MB)"}), 413
    except Exception:
        logger.exception("Erreur lors de la transcription")
        return jsonify({
            "success": False,
            "error": "Erreur de traitement"
        }), 500

def _send_temp_file(path: str, download_name: str):
    """Lit un fichier temporaire en mémoire et le renvoie, pour pouvoir le supprimer
    immédiatement sans risquer d'interrompre le flux de téléchargement (send_file paresseux)."""
    with open(path, 'rb') as fh:
        data = BytesIO(fh.read())
    return send_file(
        data,
        as_attachment=True,
        download_name=download_name,
        mimetype='audio/wav'
    )

def _cleanup(*paths):
    for file_path in paths:
        if not file_path:
            continue
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as e:
            logger.warning(f"Impossible de supprimer {file_path}: {e}")

@app.route('/api/enhance', methods=['POST'])
def enhance_audio_endpoint():
    """Endpoint pour l'amélioration audio uniquement"""
    temp_input = enhanced_path = None
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "Aucun fichier audio fourni"}), 400

        file = request.files['audio']
        if not allowed_file(file.filename):
            return jsonify({"error": "Type de fichier non supporté"}), 400

        # Paramètres d'amélioration (validés)
        try:
            noise_reduction = parse_float(request.form.get('noise_reduction'), 0.5, 0.0, 1.0)
            amplification = parse_float(request.form.get('amplification'), 0, -30.0, 30.0)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        normalize_audio = request.form.get('normalize', 'true').lower() == 'true'

        # Sauvegarder et traiter
        filename = secure_filename(file.filename)
        temp_input = safe_temp_path('enhance', file.filename)
        file.save(temp_input)

        # Améliorer l'audio
        enhanced_path = audio_processor.enhance_audio_file(
            temp_input, noise_reduction, amplification, normalize_audio
        )

        # Retourner le fichier amélioré (chargé en mémoire avant nettoyage)
        return _send_temp_file(enhanced_path, f"enhanced_{filename}")

    except Exception:
        logger.exception("Erreur d'amélioration")
        return jsonify({"error": "Erreur de traitement"}), 500
    finally:
        _cleanup(temp_input, enhanced_path)

@app.route('/api/extract_segment', methods=['POST'])
def extract_audio_segment():
    """Endpoint pour extraire un segment audio"""
    temp_input = segment_path = None
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "Aucun fichier audio fourni"}), 400

        file = request.files['audio']
        if not allowed_file(file.filename):
            return jsonify({"error": "Type de fichier non supporté"}), 400

        try:
            start_time = parse_float(request.form.get('start_time'), 0, 0.0)
            end_time = parse_float(request.form.get('end_time'), 0, 0.0)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400

        if end_time <= start_time:
            return jsonify({"error": "Temps de fin doit être supérieur au temps de début"}), 400

        # Sauvegarder le fichier temporairement
        filename = secure_filename(file.filename)
        temp_input = safe_temp_path('segment', file.filename)
        file.save(temp_input)

        # Extraire le segment
        segment_path = audio_processor.extract_segment(temp_input, start_time, end_time)

        if not segment_path:
            return jsonify({"error": "Impossible d'extraire le segment"}), 500

        # Retourner le segment (chargé en mémoire avant nettoyage)
        return _send_temp_file(
            segment_path,
            f"segment_{start_time:.1f}s-{end_time:.1f}s_{filename}"
        )

    except Exception:
        logger.exception("Erreur d'extraction")
        return jsonify({"error": "Erreur de traitement"}), 500
    finally:
        _cleanup(temp_input, segment_path)

@app.route('/api/formats', methods=['GET'])
def get_supported_formats():
    """Retourne les formats supportés"""
    return jsonify({
        "audio_formats": list(ALLOWED_EXTENSIONS['audio']),
        "video_formats": list(ALLOWED_EXTENSIONS['video']),
        "languages": SUPPORTED_LANGUAGES,
        "models": WHISPER_MODELS,
        "output_formats": sorted(OUTPUT_FORMATS)
    })

@app.route('/api/dictionary', methods=['GET'])
def dictionary_lookup():
    """
    Dictionnaire français <-> créole guadeloupéen.

    Query params:
        q         : mot ou expression à rechercher (obligatoire)
        direction : 'fr-cr' (défaut), 'cr-fr' ou 'auto'
        mode      : 'exact' (défaut) ou 'search' (recherche partielle)
    """
    query = (request.args.get('q') or '').strip()
    if not query:
        return jsonify({"error": "Paramètre 'q' requis"}), 400

    direction = request.args.get('direction', 'fr-cr')
    if direction not in DICTIONARY_DIRECTIONS:
        return jsonify({"error": "Direction invalide (fr-cr, cr-fr ou auto)"}), 400

    mode = request.args.get('mode', 'exact')
    if mode not in ('exact', 'search'):
        return jsonify({"error": "Mode invalide (exact ou search)"}), 400

    try:
        if mode == 'search':
            results = creole_dictionary.search(query)
        else:
            results = creole_dictionary.lookup(query, direction)

        return jsonify({
            "success": True,
            "query": query,
            "direction": direction,
            "mode": mode,
            "count": len(results),
            "results": results
        })
    except Exception:
        logger.exception("Erreur dictionnaire")
        return jsonify({"error": "Erreur du dictionnaire"}), 500

@app.route('/api/translate', methods=['POST'])
def translate_text():
    """
    Traduit un texte français <-> créole guadeloupéen.

    JSON: { "text": "...", "direction": "fr-cr" | "cr-fr" }
    Utilise le modèle NLLB affiné s'il est disponible, sinon le repli dictionnaire.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Corps JSON invalide ou manquant"}), 400

    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({"error": "Texte vide"}), 400

    direction = data.get('direction', 'fr-cr')
    if direction not in TRANSLATE_DIRECTIONS:
        return jsonify({"error": "Direction invalide (fr-cr ou cr-fr)"}), 400

    try:
        result = translator.translate(text, direction)
        result.update({"success": True, "direction": direction, "source": text})
        return jsonify(result)
    except Exception:
        logger.exception("Erreur de traduction")
        return jsonify({"error": "Erreur de traduction"}), 500

@app.route('/api/dictionary/all', methods=['GET'])
def dictionary_all():
    """Retourne le lexique complet (ou une catégorie via ?category=...)."""
    try:
        category = request.args.get('category')
        entries = (creole_dictionary.by_category(category)
                   if category else creole_dictionary.all_entries())
        return jsonify({
            "success": True,
            "meta": creole_dictionary.get_meta(),
            "categories": creole_dictionary.categories(),
            "count": len(entries),
            "entries": entries
        })
    except Exception:
        logger.exception("Erreur dictionnaire (all)")
        return jsonify({"error": "Erreur du dictionnaire"}), 500

@app.route('/api/convert_format', methods=['POST'])
def convert_transcript_format():
    """Convertit un transcript vers différents formats"""
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Corps JSON invalide ou manquant"}), 400

        text = data.get('text', '')
        segments = data.get('segments', [])
        output_format = data.get('format', 'text')

        if not text:
            return jsonify({"error": "Texte vide"}), 400
        if output_format not in OUTPUT_FORMATS:
            return jsonify({"error": "Format de sortie non supporté"}), 400

        result = format_converter.convert(text, segments, output_format)

        return jsonify({
            "success": True,
            "content": result,
            "format": output_format
        })

    except Exception:
        logger.exception("Erreur de conversion")
        return jsonify({"error": "Erreur de conversion"}), 500

@app.route('/api/stats')
def get_stats():
    """Statistiques de l'application"""
    try:
        # Compter les fichiers dans les dossiers (chemins ancrés sur BASE_DIR)
        uploads_dir = app.config['UPLOAD_FOLDER']
        temp_dir = app.config['TEMP_FOLDER']
        uploads_count = len([f for f in os.listdir(uploads_dir) if os.path.isfile(os.path.join(uploads_dir, f))])
        temp_count = len([f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))])

        return jsonify({
            "uploads_count": uploads_count,
            "temp_files": temp_count,
            "available_engines": transcription_engine.get_available_engines(),
            "uptime": "Running",
            "author": "Négus Dja - Directeur Artistique Guadeloupe"
        })
    except Exception:
        logger.exception("Erreur stats")
        return jsonify({"error": "Erreur interne"}), 500

# Gestion des erreurs
@app.errorhandler(413)
def file_too_large(error):
    """Gestion des fichiers trop volumineux"""
    limit_mb = app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
    return jsonify({"error": f"Fichier trop volumineux (limite: {limit_mb}MB)"}), 413

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