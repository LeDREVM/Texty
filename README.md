# Texty - Transcripteur Audio Pro

Projet "Transcripteur Audio Pro" par Négus Dja.

Ce dépôt contient une application Flask pour la transcription et le traitement audio.

Ressources utiles
- Démarrer en développement:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ranscripteur-audio-pro
export FLASK_APP=app.py
export FLASK_DEBUG=true   # développement local uniquement — ne jamais activer en production
flask run
```

Le projet inclut un panneau web dans `ranscripteur-audio-pro/Templates/index.html` et des utilitaires dans `utils/`.

Pour pousser vers GitHub, configurez votre remote et authentification (SSH/HTTPS avec PAT).
# 🎙️ Transcripteur Audio Pro

> *"Ce qui est en haut est comme ce qui est en bas"* — Hermès Trismégiste

**Application de transcription audio professionnelle créée par Négus Dja**

*Directeur Artistique basé en Guadeloupe*

*Spécialement optimisée pour les ingénieurs son, vidéastes et créateurs avec TDAH*

## ✨ Fonctionnalités

### 🎯 Transcription de précision maximale

* **IA Whisper** avec correction automatique pour une transcription au mot près
* **Support multilingue** : Plus de 25 langues avec détection automatique
* **Modèles multiples** : Du rapide (tiny) au maximum de précision (large)
* **Détection de locuteurs** pour les conversations et interviews

### 🎵 Édition audio intégrée

* **Lecteur audio avancé** avec forme d'onde visuelle
* **Outils de découpe** : sélection, rognage, extraction de segments
* **Contrôles complets** : lecture, pause, vitesse variable, volume
* **Navigation précise** avec timestamps

### 🔧 Amélioration de qualité sonore

* **Réduction de bruit** automatique et configurable
* **Amplification intelligente** sans distorsion
* **Égaliseur 3 bandes** (graves, médiums, aigus)
* **Normalisation** pour uniformiser le volume
* **Suggestions automatiques** basées sur l'analyse audio

### 📤 Export multi-formats

* **Texte simple** (TXT) pour édition
* **Sous-titres** (SRT, VTT) compatibles tous lecteurs
* **JSON structuré** avec métadonnées complètes
* **CSV** pour analyse de données
* **Document Word** formaté
* **Partage facile** via email, WhatsApp, liens

### 🔒 Confidentialité totale

* **Traitement 100% local** - Aucune donnée envoyée vers l'extérieur
* **Aucune inscription** requise
* **Vos fichiers restent chez vous**

## 🚀 Installation

### Installation automatique (recommandée)

```bash
# Cloner le projet
git clone https://github.com/negus-dja/transcripteur-audio-pro.git
cd transcripteur-audio-pro

# Rendre le script exécutable et lancer l'installation
chmod +x setup.sh
./setup.sh
```

### Installation manuelle

1. **Créer un environnement virtuel**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

2. **Installer les dépendances**

```bash
pip install -r requirements.txt
```

3. **Installer FFmpeg** (requis)

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS (avec Homebrew)
brew install ffmpeg

# Windows (avec Chocolatey)
choco install ffmpeg
```

4. **Créer les dossiers nécessaires**

```bash
mkdir -p uploads temp models logs
```

## 🎮 Utilisation

### Démarrage en mode développement

```bash
python app.py
```

### Démarrage en mode production

```bash
gunicorn wsgi:application
```

L'application sera accessible sur `http://localhost:5000`

### Interface web

1. **📁 Import Audio** : Glissez-déposez votre fichier ou cliquez pour sélectionner
2. **🎯 Transcription** : Configurez la langue, le modèle, et lancez la transcription
3. **✂️ Édition Audio** : Naviguez, sélectionnez et découpez votre audio
4. **🔧 Amélioration** : Améliorez la qualité audio avec les outils intégrés
5. **📤 Export** : Téléchargez dans le format de votre choix

### Raccourcis clavier

* `Espace` : Lecture/Pause
* `←` : Reculer de 10s
* `→` : Avancer de 10s
* `Ctrl+S` : Marquer début de sélection
* `Ctrl+E` : Marquer fin de sélection
* `Ctrl+T` : Lancer la transcription

## 🌐 Déploiement sur Hostinger

### Upload des fichiers

1. Compresser le projet : `zip -r transcripteur.zip . -x "*.git*" "__pycache__*"`
2. Uploader via le gestionnaire de fichiers Hostinger
3. Extraire dans `public_html/transcripteur/`

### Configuration Python sur Hostinger

1. Aller dans **Python** dans le panneau de contrôle
2. Créer une nouvelle application Python 3.9+
3. Définir le répertoire : `/public_html/transcripteur`
4. Point d'entrée : `wsgi:application`

### Variables d'environnement

Créer un fichier `.env` :

```env
# Production : laisser le debug désactivé (FLASK_DEBUG absent ou False)
FLASK_DEBUG=False
PORT=5000
MAX_FILE_SIZE=104857600            # taille max en octets (100 Mo) — lu par l'app
CORS_ORIGINS=https://votre-domaine.example   # origines autorisées (séparées par des virgules)
WHISPER_MODEL_DIR=./models
```

### Installation des dépendances

```bash
cd public_html/transcripteur
pip install -r requirements.txt
```

## 🔧 Configuration

### Modèles Whisper

Les modèles sont téléchargés automatiquement au premier usage :

* **tiny** : 39 MB - Ultra rapide, précision limitée
* **base** : 74 MB - Rapide, précision correcte
* **small** : 244 MB - **Recommandé** - Équilibré
* **medium** : 769 MB - Précis, plus lent
* **large** : 1550 MB - Maximum de précision

### Formats supportés

**Audio** : MP3, WAV, M4A, FLAC, OGG, WMA

**Vidéo** : MP4, AVI, MOV, MKV, WEBM, FLV

### Limites

* Taille max : 100MB par fichier
* Durée max recommandée : 2h (pour les performances)
* Langues : 25+ langues supportées

## 📊 Performances

### Temps de transcription estimés (CPU)

* **tiny** : ~10% de la durée audio
* **base** : ~15% de la durée audio
* **small** : ~25% de la durée audio (recommandé)
* **medium** : ~40% de la durée audio
* **large** : ~60% de la durée audio

*Exemple : 10 minutes d'audio = ~2.5 minutes de transcription avec le modèle "small"*

### Optimisations pour Hostinger

* Modèles compressés (int8) pour réduire l'usage mémoire
* Nettoyage automatique des fichiers temporaires
* Traitement par chunks pour les gros fichiers
* Cache des modèles pour éviter les rechargements

## 🎨 Personnalisation

### Interface utilisateur

L'interface est conçue pour être  **intuitive et accessible** , particulièrement pour les personnes avec TDAH :

* **Couleurs contrastées** pour une meilleure lisibilité
* **Feedback visuel immédiat** sur toutes les actions
* **Organisation claire** en onglets thématiques
* **Raccourcis clavier** pour les actions fréquentes
* **Messages d'état explicites** à chaque étape

### API REST

L'application expose une API REST complète :

```bash
# Vérifier l'état du service
GET /api/health

# Transcrire un fichier
POST /api/transcribe
  - multipart/form-data
  - Fichier : 'audio'
  - Paramètres : language, model, speakers, enhance, etc.

# Améliorer un fichier audio
POST /api/enhance
  - Paramètres : noise_reduction, amplification, normalize

# Extraire un segment
POST /api/extract_segment
  - Paramètres : start_time, end_time

# Convertir les formats
POST /api/convert_format
  - JSON : text, segments, format

# Formats supportés
GET /api/formats
```

## 🔍 Dépannage

### Problèmes courants

**Erreur : "Aucun moteur de transcription disponible"**

```bash
# Vérifier l'installation des dépendances
pip install --upgrade faster-whisper openai-whisper

# Tester l'installation
python -c "import whisper; print('Whisper OK')"
```

**Erreur : "FFmpeg non trouvé"**

```bash
# Installer FFmpeg selon votre système
# Ubuntu/Debian
sudo apt install ffmpeg

# Vérifier l'installation
ffmpeg -version
```

**Problème de mémoire sur Hostinger**

* Utiliser le modèle "tiny" ou "base" au lieu de "small"
* Réduire la taille des fichiers avant upload
* Activer la compression audio dans les paramètres

**Timeout lors de la transcription**

* Découper les fichiers longs en segments plus courts
* Utiliser un modèle plus rapide
* Vérifier les limites de votre hébergement

### Logs de débogage

Les logs sont disponibles dans :

* `logs/app.log` : Logs de l'application
* Console du navigateur : Logs JavaScript
* Panneau Hostinger : Logs du serveur Python

## 🤝 Support spécialisé

### Pour les ingénieurs son

* **Préservation de la qualité audio** : Traitement non-destructif
* **Formats professionnels** : Support WAV, FLAC haute résolution
* **Métadonnées complètes** : Informations techniques préservées
* **Workflow optimisé** : Intégration dans les chaînes de post-production

### Pour les vidéastes

* **Extraction audio automatique** depuis les vidéos
* **Synchronisation préservée** : Timestamps précis pour le montage
* **Sous-titres prêts** : SRT/VTT directement utilisables
* **Workflow YouTube/TikTok** : Formats optimisés réseaux sociaux

### Pour les créateurs avec TDAH

* **Interface simplifiée** : Une action = un résultat visible
* **Feedback immédiat** : Confirmations visuelles et sonores
* **Sauvegarde automatique** : Aucune perte de travail
* **Raccourcis intuitifs** : Actions rapides au clavier
* **Organisation claire** : Chaque fonction dans son onglet

## 📈 Feuille de route

### Version 1.1 (prochaine)

* [ ] Détection avancée de locuteurs avec pyannote.audio
* [ ] Export PDF avec mise en forme
* [ ] API webhook pour intégration externe
* [ ] Support des playlists audio
* [ ] Mode batch pour traitement en lot

### Version 1.2

* [ ] Interface mobile responsive
* [ ] Collaboration temps réel
* [ ] Intégration cloud (Dropbox, Google Drive)
* [ ] Templates de mise en forme personnalisés
* [ ] Analyse sentimentale du contenu

### Version 2.0

* [ ] Transcription vidéo avec reconnaissance faciale
* [ ] Support des langues créoles (focus Guadeloupe)
* [ ] IA de résumé automatique
* [ ] Plugin pour logiciels de montage (Adobe, DaVinci)

## 🏆 Remerciements

### Technologies utilisées

* **Whisper (OpenAI)** : Moteur de transcription IA
* **Faster-Whisper** : Optimisation et accélération
* **Flask** : Framework web Python
* **LibROSA** : Traitement audio scientifique
* **PyDub** : Manipulation audio simple
* **NoiseReduce** : Réduction de bruit

### Inspiration

Cette application a été créée pour **simplifier la vie quotidienne** des créateurs audio/vidéo, en particulier ceux avec TDAH qui ont besoin d'outils  **intuitifs et efficaces** .

L'approche **"tout-en-un"** permet de gérer l'intégralité du workflow de transcription sans jongler entre multiple applications.

## 📞 Contact & Support

### Créateur

**Négus Dja**

*Directeur Artistique*

📍 Basé en Guadeloupe

### Spécialisations

* 🎵 **Ingénierie audio** et post-production
* 🎬 **Montage vidéo** et création de contenu
* 💻 **Développement sur mesure** pour créateurs
* 🌱 **Cuisine végétalienne** (passion personnelle)

### Pour vos projets

Si vous avez des besoins spécifiques en :

* Applications audio/vidéo personnalisées
* Outils pour créateurs avec TDAH
* Solutions d'automatisation créative
* Formation aux outils numériques

N'hésitez pas à me contacter pour discuter de vos projets !

## 📄 Licence

**Transcripteur Audio Pro** est un logiciel libre créé par Négus Dja.

### Utilisation

* ✅ **Usage personnel** illimité
* ✅ **Usage professionnel** autorisé
* ✅ **Modification** du code source
* ✅ **Distribution** avec attribution

### Attribution

Si vous utilisez ou modifiez ce logiciel, merci de mentionner :

> *"Basé sur Transcripteur Audio Pro par Négus Dja"*

### Responsabilité

Ce logiciel est fourni "tel quel", sans garantie. L'auteur ne peut être tenu responsable des dommages liés à son utilisation.

---

## 🎯 Message de Négus Dja

*"En tant que Directeur Artistique basé en Guadeloupe, j'ai créé cet outil pour mes collègues créateurs qui, comme moi, jonglent entre projets audio, vidéo et code.*

*L'objectif est simple : **simplifier votre vie quotidienne** en automatisant les tâches répétitives pour que vous puissiez vous concentrer sur votre créativité.*

*Que vous soyez ingénieur son, vidéaste, ou créateur avec TDAH, j'espère que cet outil vous sera aussi utile qu'il l'est pour moi.*

*N'hésitez pas à partager vos retours et suggestions - c'est comme ça qu'on grandit ensemble !*

*Bon créatif ! 🎨"*

---

**🔗 Liens utiles**

* [Documentation API](https://claude.ai/docs/api_documentation.md)
* [Guide d&#39;installation détaillé](https://claude.ai/docs/installation.md)
* [Dépannage avancé](https://claude.ai/docs/troubleshooting.md)
* [Changelog](https://claude.ai/CHANGELOG.md)

**🏷️ Tags**
`transcription` `audio` `whisper` `flask` `guadeloupe` `TDAH` `ingénieur-son` `vidéaste` `IA` `local` `privé`
