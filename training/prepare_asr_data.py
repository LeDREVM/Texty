#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Préparation des données ASR (reconnaissance vocale) créole guadeloupéen.

Lit un manifeste CSV `audio_path,text` (un extrait audio + sa transcription
créole validée), vérifie/dédoublonne, mélange (graine fixe) et écrit
train/dev/test. Bibliothèque standard uniquement — s'exécute partout.

Usage :
    python training/prepare_asr_data.py \
        --input data/creole_asr_manifest.csv \
        --outdir training/asr_data \
        --dev-ratio 0.1 --test-ratio 0.1 --seed 42
"""

import argparse
import csv
import random
from pathlib import Path


def read_manifest(path: Path):
    rows, seen = [], set()
    missing = 0
    with open(path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or 'audio_path' not in reader.fieldnames or 'text' not in reader.fieldnames:
            raise SystemExit("Le manifeste doit avoir l'en-tête : audio_path,text")
        for row in reader:
            audio = (row.get('audio_path') or '').strip()
            text = (row.get('text') or '').strip()
            if not audio or not text:
                continue
            if audio in seen:
                continue
            seen.add(audio)
            if not Path(audio).exists():
                missing += 1
                print(f"  ⚠️ audio introuvable: {audio}")
            rows.append({'audio_path': audio, 'text': text})
    if missing:
        print(f"  ⚠️ {missing} fichier(s) audio introuvable(s) — corrige les chemins avant l'entraînement.")
    return rows


def split_rows(rows, dev_ratio, test_ratio, seed):
    rng = random.Random(seed)
    shuffled = rows[:]
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_test = int(n * test_ratio)
    n_dev = int(n * dev_ratio)
    return shuffled[n_test + n_dev:], shuffled[n_test:n_test + n_dev], shuffled[:n_test]


def write_csv(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=['audio_path', 'text'])
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description="Prépare les données ASR créole")
    ap.add_argument('--input', default='data/creole_asr_manifest.csv')
    ap.add_argument('--outdir', default='training/asr_data')
    ap.add_argument('--dev-ratio', type=float, default=0.1)
    ap.add_argument('--test-ratio', type=float, default=0.1)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    rows = read_manifest(Path(args.input))
    print(f"🎧 {len(rows)} extraits valides depuis {args.input}")
    if len(rows) < 20:
        print("  ⚠️ Très peu de données : l'ASR demande idéalement plusieurs HEURES d'audio transcrit.")

    train, dev, test = split_rows(rows, args.dev_ratio, args.test_ratio, args.seed)
    out = Path(args.outdir)
    write_csv(train, out / 'train.csv')
    write_csv(dev, out / 'dev.csv')
    write_csv(test, out / 'test.csv')
    print(f"✅ train={len(train)}  dev={len(dev)}  test={len(test)}  -> {out}/")


if __name__ == '__main__':
    main()
