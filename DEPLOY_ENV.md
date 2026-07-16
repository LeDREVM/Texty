# Variables d'environnement à définir (déploiement)

Récapitulatif copier-coller. Remplace `<TON_USER_HF>` par ton nom d'utilisateur
Hugging Face (l'URL du Space est `https://<TON_USER_HF>-texty.hf.space`).

---

## 1. Netlify — front statique

**Site settings ▸ Environment variables ▸ Add a variable**

| Clé            | Valeur                                        |
| -------------- | --------------------------------------------- |
| `API_BASE_URL` | `https://<TON_USER_HF>-texty.hf.space`        |

> C'est l'URL de ton **backend** (HF Space ou Render). Après l'avoir définie :
> **Deploys ▸ Trigger deploy ▸ Clear cache and deploy site** pour que le build
> l'injecte dans `static/js/config.js`.
>
> Exemple : si ton user HF est `myel`, mets `https://myel-texty.hf.space`.

---

## 2. Hugging Face Space — backend

**Settings ▸ Variables and secrets ▸ New variable** (type *Variable*, pas *Secret*)

| Clé             | Valeur                             | Requis    |
| --------------- | ---------------------------------- | --------- |
| `CORS_ORIGINS`  | `https://textymyel.netlify.app`    | ✅ oui     |
| `MAX_FILE_SIZE` | `104857600`                        | optionnel |

> `FLASK_DEBUG=False`, `WHISPER_MODEL_DIR=/app/models` et `PORT=7860` sont déjà
> fixés par le `Dockerfile` — inutile de les remettre.

---

## 3. Render — backend (alternative, déjà dans `render.yaml`)

| Clé                 | Valeur                          |
| ------------------- | ------------------------------- |
| `CORS_ORIGINS`      | `https://textymyel.netlify.app` |
| `WHISPER_MODEL_DIR` | `/app/models`                   |
| `FLASK_DEBUG`       | `False`                         |
| `MAX_FILE_SIZE`     | `104857600`                     |

---

## Schéma — les deux URLs se pointent mutuellement

```
Netlify (front)                          Backend (HF Space ou Render)
  API_BASE_URL ───────────────────────▶  https://<TON_USER_HF>-texty.hf.space
  https://textymyel.netlify.app  ◀─────  CORS_ORIGINS
```

Ordre conseillé : (1) déployer le backend → obtenir son URL, (2) mettre
`API_BASE_URL` sur Netlify + redeploy, (3) vérifier que `CORS_ORIGINS` du backend
pointe bien vers `https://textymyel.netlify.app`.
