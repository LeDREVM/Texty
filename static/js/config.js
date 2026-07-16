/**
 * Configuration front — Transcripteur Audio Pro
 *
 * API_BASE_URL : base des appels API.
 *   - "" (vide)  -> même origine (cas d'un déploiement Flask classique)
 *   - "https://mon-backend.example.com" -> backend externe (cas Netlify :
 *     le front est statique sur Netlify, le backend Flask/Whisper tourne
 *     ailleurs). Le build Netlify remplace cette valeur via la variable
 *     d'environnement API_BASE_URL (voir netlify/build.sh).
 *
 * Pense à autoriser l'origine du front dans le CORS du backend
 * (variable CORS_ORIGINS de app.py).
 */
window.API_BASE_URL = window.API_BASE_URL || "";

// Construit une URL d'API en préfixant la base (sans double slash).
window.apiUrl = function (path) {
    var base = window.API_BASE_URL || "";
    if (base && base.charAt(base.length - 1) === "/") {
        base = base.slice(0, -1);
    }
    return base + path;
};
