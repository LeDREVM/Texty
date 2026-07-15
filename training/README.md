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
