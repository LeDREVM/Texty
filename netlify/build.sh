#!/usr/bin/env bash
# Assemble le site statique pour Netlify.
# Netlify ne peut PAS exécuter le backend Flask/Whisper : on ne publie que le
# dashboard (front). Le backend tourne ailleurs et est appelé via API_BASE_URL.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"

rm -rf "$DIST"
mkdir -p "$DIST"

# index.html à la racine du site + assets statiques
cp "$ROOT/templates/index.html" "$DIST/index.html"
cp -r "$ROOT/static" "$DIST/static"

# Injecte l'URL du backend (variable d'environnement Netlify) dans config.js
API_BASE_URL="${API_BASE_URL:-}"
if [ -n "$API_BASE_URL" ]; then
  sed -i "s#window.API_BASE_URL = window.API_BASE_URL || \"\";#window.API_BASE_URL = \"${API_BASE_URL}\";#" \
    "$DIST/static/js/config.js"
fi

echo "✅ Build Netlify prêt dans dist/ (API_BASE_URL='${API_BASE_URL:-<vide=même origine>}')"
