# Données ASR créole — à uploader sur Google Drive

Ce dossier est prêt pour Colab (`DATA_DIR = /content/drive/MyDrive/creole_asr`).

## Structure

```
creole_asr/
├── README.md
├── manifest.csv              ← index audio + transcription
└── enregistrements/          ← mets tes fichiers ici
    └── conseil_de_sage_2.wav
```

## Ajouter un enregistrement

1. Place le fichier audio dans `enregistrements/`  
   (idéalement **WAV mono 16 kHz** ; `.mp3` / `.m4a` fonctionnent aussi)
2. Ajoute **une ligne** dans `manifest.csv` :

```csv
audio_path,text
enregistrements/mon_fichier.wav,fraz an kréyòl validé
```

3. Remplace le `TODO:…` par la vraie transcription créole (pas de ligne vide).

## Envoyer sur Colab

1. Uploade tout le dossier `creole_asr/` dans **Mon Drive** Google
2. Ouvre le notebook Colab Whisper créole
3. Vérifie : `DATA_DIR = "/content/drive/MyDrive/creole_asr"`
4. **Exécution ▸ Tout exécuter**

## Astuces

- Un fichier = une ligne dans le manifeste
- Préfère des extraits courts (~10–30 s) plutôt qu’un enregistrement de 20 min
- Les gros fichiers audio ne sont **pas** versionnés dans git (voir `.gitignore`)
