# Variables d'environnement à définir (déploiement)

Valeurs concrètes pour ce projet — Space HF : **`Hiiwok/texty`**,
front Netlify : **`https://textymyel.netlify.app`**.
URL API du backend (sous-domaine en minuscules) : **`https://hiiwok-texty.hf.space`**.

---

## 1. Netlify — front statique

**Site settings ▸ Environment variables ▸ Add a variable**

| Clé            | Valeur                              |
| -------------- | ----------------------------------- |
| `API_BASE_URL` | `https://hiiwok-texty.hf.space`     |

> Après l'avoir définie : **Deploys ▸ Trigger deploy ▸ Clear cache and deploy site**
> pour que le build l'injecte dans `static/js/config.js`.

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

## 4. GitHub Actions — déploiement auto du backend vers HF (optionnel)

Le workflow `.github/workflows/deploy-hf.yml` pousse le backend vers le Space à
chaque push. **Repo ▸ Settings ▸ Secrets and variables ▸ Actions** :

| Type       | Nom           | Valeur                              |
| ---------- | ------------- | ----------------------------------- |
| **Secret** | `HF_TOKEN`    | *(ton NOUVEAU token HF, rôle Write)* |
| Variable   | `HF_USERNAME` | `Hiiwok`                            |
| Variable   | `HF_SPACE`    | `texty`                             |

> 🔒 Le token va **uniquement** dans le *Secret* `HF_TOKEN` (chiffré par GitHub).
> Jamais dans un fichier, un commit, ou la conversation.

---

## Schéma — les deux URLs se pointent mutuellement

```
Netlify (front)                          Backend HF Space (Hiiwok/texty)
  API_BASE_URL ───────────────────────▶  https://hiiwok-texty.hf.space
  https://textymyel.netlify.app  ◀─────  CORS_ORIGINS
```

Ordre conseillé : (1) déployer le backend → obtenir son URL, (2) mettre
`API_BASE_URL` sur Netlify + redeploy, (3) vérifier que `CORS_ORIGINS` du backend
pointe bien vers `https://textymyel.netlify.app`.
