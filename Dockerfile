# Backend Transcripteur Audio Pro (Flask + Whisper).
# Compatible Render ET Hugging Face Spaces (Docker) : conteneur NON-ROOT
# (exigé par HF Spaces, accepté par Render) et port configurable ${PORT:-7860}.
# Whisper nécessite ffmpeg + libsndfile (impossible en runtime natif).
FROM python:3.11-slim

# Dépendances système : ffmpeg (pydub/whisper), libsndfile (soundfile),
# git (Hugging Face Spaces injecte un `git config` pendant le build).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        git \
    && rm -rf /var/lib/apt/lists/*

# Utilisateur non-root (UID 1000) requis par Hugging Face Spaces
RUN useradd -m -u 1000 user

WORKDIR /app

# Installer les dépendances Python (meilleur cache de build)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code puis donner la propriété à l'utilisateur non-root
COPY . .
RUN chown -R user:user /app

# Caches et modèles dans des dossiers inscriptibles par l'utilisateur
ENV PYTHONUNBUFFERED=1 \
    FLASK_DEBUG=False \
    HOME=/app \
    HF_HOME=/app/.cache/huggingface \
    XDG_CACHE_HOME=/app/.cache \
    WHISPER_MODEL_DIR=/app/models \
    PORT=7860

USER user
EXPOSE 7860

# Port flexible : Render fournit $PORT (ex. 10000), HF Spaces utilise 7860.
# --timeout 1800 : la transcription CPU d'un fichier long peut durer longtemps
#   (sinon gunicorn tue le worker et la requête échoue en « failed to fetch »).
# --graceful-timeout 30 : redémarrage plus propre (évite le port bloqué).
# --threads 4 : sert les requêtes de suivi (/api/transcribe_status) pendant qu'un
#   job de transcription tourne en tâche de fond dans le même worker.
CMD ["sh", "-c", "gunicorn wsgi:application --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 4 --timeout 1800 --graceful-timeout 30"]
