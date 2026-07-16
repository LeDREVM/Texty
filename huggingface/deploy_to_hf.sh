#!/usr/bin/env bash
# Déploie le backend Texty (Flask + Whisper) sur un Hugging Face Space (Docker).
#
# ⚠️ À LANCER SUR TA MACHINE — pas dans l'environnement web (qui n'a ni accès à
#    huggingface.co ni ton token HF).
#
# Prérequis (une seule fois) :
#   pip install -U "huggingface_hub[cli]"
#   hf auth login                  # colle ton token : https://huggingface.co/settings/tokens
#
# Usage (depuis la racine du dépôt) :
#   bash huggingface/deploy_to_hf.sh <ton_user_hf> [nom_space]
#   ex :  bash huggingface/deploy_to_hf.sh myel texty
set -euo pipefail

HF_USER="${1:?Usage: bash huggingface/deploy_to_hf.sh <hf_username> [space_name]}"
SPACE="${2:-texty}"
REPO_ID="$HF_USER/$SPACE"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"

echo "▶ Space cible : https://huggingface.co/spaces/$REPO_ID"

# 1) Créer le Space (Docker) s'il n'existe pas encore
if command -v hf >/dev/null 2>&1; then
  hf repo create "$SPACE" --repo-type space 2>/dev/null \
    && echo "  Space créé." || echo "  (Space déjà existant ou création ignorée.)"
else
  echo "  CLI 'hf' absente : crée le Space à la main (SDK Docker) sur https://huggingface.co/new-space"
fi

# 2) Cloner le dépôt du Space
git clone "https://huggingface.co/spaces/$REPO_ID" "$WORK/space"

# 3) Copier les fichiers de l'application + la fiche du Space (avec métadonnées YAML)
cd "$ROOT"
cp Dockerfile requirements.txt app.py wsgi.py "$WORK/space/"
cp -r utils templates static data "$WORK/space/"
cp huggingface/README.md "$WORK/space/README.md"

# 4) Commit + push
cd "$WORK/space"
git add -A
if git commit -m "Deploy Texty backend (Flask + Whisper)"; then
  git push
  echo ""
  echo "✅ Poussé ! Build en cours : https://huggingface.co/spaces/$REPO_ID"
  echo "   1) Settings ▸ Variables : CORS_ORIGINS = https://textymyel.netlify.app"
  echo "   2) Sur Netlify : API_BASE_URL = https://${HF_USER}-${SPACE}.hf.space  puis redeploy"
else
  echo "Rien à committer (déjà à jour)."
fi
