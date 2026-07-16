#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Préparation du corpus parallèle français <-> créole guadeloupéen.

Lit le TSV `data/parallel_corpus_fr_gcf.tsv`, nettoie, dédoublonne, mélange
(graine fixe pour la reproductibilité) et écrit train/dev/test dans un dossier
de sortie. Bibliothèque standard uniquement — s'exécute partout.

Usage :
    python training/prepare_data.py \
        --input data/parallel_corpus_fr_gcf.tsv \
        --outdir training/data \
        --dev-ratio 0.1 --test-ratio 0.1 --seed 42
"""

import argparse
import random
from pathlib import Path


def read_pairs(path: Path):
    """Lit les paires (fr, cr) en ignorant commentaires, lignes vides et doublons."""
    pairs, seen = [], set()
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                print(f"  ⚠️ ligne {lineno} ignorée (pas de tabulation): {line!r}")
                continue
            fr, cr = parts[0].strip(), parts[1].strip()
            if not fr or not cr:
                continue
            key = (fr.lower(), cr.lower())
            if key in seen:
                continue
            seen.add(key)
            pairs.append((fr, cr))
    return pairs


def split_pairs(pairs, dev_ratio, test_ratio, seed):
    rng = random.Random(seed)
    shuffled = pairs[:]
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_test = int(n * test_ratio)
    n_dev = int(n * dev_ratio)
    test = shuffled[:n_test]
    dev = shuffled[n_test:n_test + n_dev]
    train = shuffled[n_test + n_dev:]
    return train, dev, test


def write_tsv(pairs, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for fr, cr in pairs:
            fh.write(f"{fr}\t{cr}\n")


def main():
    ap = argparse.ArgumentParser(description="Prépare le corpus parallèle fr<->gcf")
    ap.add_argument("--input", default="data/parallel_corpus_fr_gcf.tsv")
    ap.add_argument("--outdir", default="training/data")
    ap.add_argument("--dev-ratio", type=float, default=0.1)
    ap.add_argument("--test-ratio", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    pairs = read_pairs(Path(args.input))
    print(f"📚 {len(pairs)} paires uniques lues depuis {args.input}")
    if len(pairs) < 10:
        print("  ⚠️ Corpus très petit : ajoutez des phrases avant d'entraîner un modèle.")

    train, dev, test = split_pairs(pairs, args.dev_ratio, args.test_ratio, args.seed)
    outdir = Path(args.outdir)
    write_tsv(train, outdir / "train.tsv")
    write_tsv(dev, outdir / "dev.tsv")
    write_tsv(test, outdir / "test.tsv")
    print(f"✅ train={len(train)}  dev={len(dev)}  test={len(test)}  -> {outdir}/")


if __name__ == "__main__":
    main()
