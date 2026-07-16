---
title: Texty - Transcripteur Audio Pro
emoji: 🎙️
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: Transcription audio multilingue (Whisper) + créole guadeloupéen
---

# Texty — backend sur Hugging Face Spaces (Docker, gratuit)

Ce fichier est la **fiche du Space** : à placer comme `README.md` à la racine
du Space (les métadonnées YAML ci-dessus configurent le Space en mode Docker,
port 7860). Le CPU gratuit HF offre ~16 Go de RAM — suffisant pour les modèles
Whisper `tiny`/`base`/`small` (sans GPU, donc plus lent).

## Créer le Space

1. Sur https://huggingface.co/new-space :
   - **Owner** : ton compte · **Space name** : `texty`
   - **SDK** : **Docker** (template « Blank »)
   - Visibilité : Public ou Private
2. Pousse le code de l'application dans le dépôt du Space (racine) :
   ```
   Dockerfile          requirements.txt
   app.py  wsgi.py     utils/  templates/  static/  data/
   README.md           <- cette fiche (avec les métadonnées YAML)
   ```
   Le plus simple : cloner le repo du Space, y copier ces fichiers, puis
   `git add . && git commit -m "backend texty" && git push`.
   (Le même `Dockerfile` que Render fonctionne ici : non-root, port 7860.)
3. Le Space se construit tout seul. Une fois « Running », l'API est sur :
   ```
   https://<ton-user>-texty.hf.space
   ```

## Variables d'environnement (Settings ▸ Variables and secrets)

- `CORS_ORIGINS = https://textymyel.netlify.app`  ← autorise ton front Netlify
- (optionnel) `MAX_FILE_SIZE = 104857600`

## Relier au front Netlify

Mets sur Netlify **`API_BASE_URL = https://<ton-user>-texty.hf.space`**, puis
redéploie le front. Le dashboard appellera ce backend pour la transcription.

> Note : le stockage d'un Space gratuit est éphémère — le modèle Whisper est
> re-téléchargé après une mise en veille (quelques minutes au 1ᵉʳ appel).
