# Entraîner un modèle de traduction français ↔ créole guadeloupéen

Ce dossier contient le pipeline pour **fine-tuner NLLB-200** sur un corpus parallèle
français ↔ kréyòl gwadloupéyen, l'évaluer, puis le servir depuis l'application.

> ⚠️ **L'entraînement nécessite un GPU** (Google Colab, Kaggle, ou une machine locale
> avec CUDA). Il **ne s'exécute pas** dans l'environnement web du projet (pas de GPU,
> pas d'accès à PyPI). Seule la préparation des données (`prepare_data.py`) tourne partout.

---

## Le point le plus important : les données

La qualité du modèle dépend **directement** de la quantité et de la qualité du corpus
parallèle. Le créole guadeloupéen est une langue peu dotée : il faut constituer ce corpus.

Sources possibles de phrases fr ↔ créole alignées :
- Nouveau Testament / Bible en créole guadeloupéen
- Recueils de proverbes, contes, chansons
- Manuels et publications du GEREC
- Sous-titres, transcriptions bilingues
- Traduction manuelle de phrases (vous / locuteurs natifs)

Ordre de grandeur : ~1 000 paires pour un premier essai, **~10 000+** pour un résultat
utilisable. Le dictionnaire mot à mot (`data/creole_gwada.json`) sert de *glossaire*,
pas de corpus de phrases.

**Format** : `data/parallel_corpus_fr_gcf.tsv`, une paire par ligne :
```
phrase française<TAB>phrase créole
```

---

## Étapes

### 1. Préparer les données (partout, sans GPU)
```bash
python training/prepare_data.py \
    --input data/parallel_corpus_fr_gcf.tsv \
    --outdir training/data \
    --dev-ratio 0.1 --test-ratio 0.1 --seed 42
# -> training/data/{train,dev,test}.tsv
```

### 2. Installer les dépendances d'entraînement (sur GPU)
```bash
pip install -r training/requirements-train.txt
```

### 3. Lancer le fine-tuning (sur GPU)
```bash
python training/finetune_nllb.py \
    --data-dir training/data \
    --model facebook/nllb-200-distilled-600M \
    --output-dir training/nllb-fr-gcf \
    --epochs 10 --batch-size 8
```
- Modèle de base : `nllb-200-distilled-600M` (bon compromis). Pour plus petit/rapide :
  `facebook/nllb-200-distilled-600M` reste le meilleur point de départ ; en dernier recours
  un modèle plus léger dégradera la qualité.
- Le créole gwada n'ayant pas de code NLLB, on réutilise `hat_Latn` (créole haïtien) comme
  jeton de langue cible, par transfert. C'est documenté dans `finetune_nllb.py`.
- L'entraînement est **bidirectionnel** (fr→cr et cr→fr) à partir du même corpus.

### 4. Évaluation
Le script affiche **chrF** et **BLEU** sur le jeu de dev à chaque époque
(chrF est plus fiable que BLEU pour une langue morphologiquement riche et peu dotée).

### 5. Servir le modèle dans l'application
Copiez le dossier entraîné là où l'app le cherche :
```bash
cp -r training/nllb-fr-gcf models/nllb-fr-gcf
export TRANSLATION_MODEL_DIR=models/nllb-fr-gcf   # lu par utils/translator.py
```
L'endpoint `POST /api/translate` utilisera automatiquement le modèle s'il est présent,
sinon il retombe sur le traducteur dictionnaire+règles (voir ci-dessous).

---

## Sans entraînement : le traducteur de repli

En attendant un modèle, `utils/translator.py` fournit une traduction **dictionnaire +
règles** (marqueurs `ka`/`ké`/`té`, articles) déjà branchée sur `POST /api/translate`.
C'est une approximation mot à mot — utile pour dépanner, pas une vraie traduction.

---

## Rappel responsabilité

Le corpus fourni est un **jeu de départ minime, à valider et enrichir par des locuteurs
natifs**. Ne publiez pas un modèle comme référence linguistique sans relecture humaine.

---

# Reconnaissance vocale (ASR) : transcrire le créole à l'audio

Whisper de base ne connaît pas le créole guadeloupéen. On peut l'**affiner** sur de
l'audio créole transcrit pour améliorer la transcription. Là aussi : **GPU requis**,
et surtout **des données** (le point dur).

## Les données (le nerf de la guerre)

Il faut des paires **(extrait audio, transcription créole validée)**. L'ASR est gourmand :
viser idéalement **plusieurs heures** d'audio transcrit. Pistes :
- Enregistrements créoles avec leur transcription (radio, podcasts, interviews… avec droits).
- **Bootstrap malin** : transcris tes audios créoles dans l'app (modèle `small`, langue
  français), **corrige** le texte à la main, et réutilise ces paires (audio + texte corrigé)
  comme données d'entraînement. Chaque correction améliore le futur modèle.

**Format** : `data/creole_asr_manifest.csv`, colonnes `audio_path,text` (audio 16 kHz mono
de préférence). Une ligne = un extrait + sa transcription.

## 🚀 Le plus simple : le notebook Colab clé en main

Ouvre **`training/whisper_creole_colab.ipynb`** dans Google Colab
(Runtime ▸ GPU), mets tes audios + un `manifest.csv` (`audio_path,text`) dans un
dossier Google Drive, puis **Exécution ▸ Tout exécuter**. Il installe tout, entraîne,
évalue (WER), convertit au format faster-whisper et te fait télécharger le modèle.
Les étapes manuelles ci-dessous sont l'équivalent en ligne de commande.

## Étapes (équivalent CLI)

### 1. Préparer les données (partout, sans GPU)
```bash
python training/prepare_asr_data.py \
    --input data/creole_asr_manifest.csv \
    --outdir training/asr_data --seed 42
# -> training/asr_data/{train,dev,test}.csv
```

### 2. Fine-tuner Whisper (sur GPU)
```bash
pip install -r training/requirements-train.txt
python training/finetune_whisper_creole.py \
    --manifest-dir training/asr_data \
    --base-model openai/whisper-small \
    --output-dir training/whisper-creole \
    --epochs 10 --batch-size 8
```
- Langue proxy = français (`--language French`) : le créole n'a pas de jeton dédié.
- Métrique : **WER** (Word Error Rate) sur le jeu de dev — **plus bas = mieux**.
- Modèle de base : `openai/whisper-small` (bon compromis) ; `tiny`/`base` pour plus léger.

### 3. Convertir pour l'app (faster-whisper / CTranslate2)
L'app utilise faster-whisper. Convertis le modèle affiné :
```bash
ct2-transformers-converter --model training/whisper-creole \
    --output_dir training/whisper-creole-ct2 --quantization int8
```

### 4. Brancher le modèle dans le backend
Copie le dossier converti dans `models/` et pointe la variable d'environnement :
```bash
cp -r training/whisper-creole-ct2 models/whisper-creole-ct2
export CREOLE_MODEL_PATH=models/whisper-creole-ct2   # lu par utils/transcription_engine.py
```
Le backend chargera **ce modèle affiné à la place** du Whisper standard (sur HF Space :
Settings ▸ Variables → `CREOLE_MODEL_PATH=/app/models/whisper-creole-ct2`, et embarque le
dossier dans l'image ou télécharge-le au démarrage).

## Rappel responsabilité (ASR)
Un modèle entraîné sur peu de données transcrira mal et de façon biaisée. À faire valider
par des locuteurs natifs, et à améliorer par itérations (corriger → réentraîner).
