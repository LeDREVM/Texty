# Backend Transcripteur Audio Pro (Flask + Whisper) pour Render / Docker.
# Whisper nécessite ffmpeg et libsndfile : un conteneur Docker est requis
# (le runtime Python natif de Render ne permet pas d'installer ces paquets système).
FROM python:3.11-slim

# Dépendances système : ffmpeg (pydub/whisper), libsndfile (soundfile)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer les dépendances Python d'abord (meilleur cache de build)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

ENV PYTHONUNBUFFERED=1 \
    FLASK_DEBUG=False \
    WHISPER_MODEL_DIR=/app/models \
    PORT=10000

EXPOSE 10000

# Timeout élevé : la transcription sur CPU peut durer plusieurs minutes.
# 1 worker pour limiter la mémoire (les modèles Whisper sont volumineux).
CMD ["sh", "-c", "gunicorn wsgi:application --bind 0.0.0.0:${PORT} --workers 1 --timeout 300"]
