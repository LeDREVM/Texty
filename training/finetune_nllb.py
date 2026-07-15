#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fine-tuning d'un modèle NLLB-200 pour la traduction français <-> créole guadeloupéen.

⚠️ À EXÉCUTER SUR UNE MACHINE AVEC GPU (Google Colab / Kaggle / serveur GPU).
   Ne fonctionne pas dans l'environnement web du projet (pas de GPU, pas d'accès PyPI).

Le créole guadeloupéen n'a pas de code de langue dédié dans NLLB. On réutilise
le code du créole haïtien « hat_Latn » comme jeton de langue cible, par transfert
(langues proches). C'est un choix pragmatique documenté ; on peut aussi ajouter un
nouveau jeton de langue si le corpus est important.

Dépendances : voir training/requirements-train.txt
Données      : produites par training/prepare_data.py (train.tsv / dev.tsv / test.tsv)

Exemple :
    python training/finetune_nllb.py \
        --data-dir training/data \
        --model facebook/nllb-200-distilled-600M \
        --output-dir training/nllb-fr-gcf \
        --epochs 10 --batch-size 8
"""

import argparse
from pathlib import Path

import numpy as np
from datasets import Dataset
import sacrebleu
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)

SRC_LANG = "fra_Latn"   # français
TGT_LANG = "hat_Latn"   # proxy pour le créole guadeloupéen (voir docstring)


def load_tsv(path: Path):
    fr, cr = [], []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            fr.append(parts[0].strip())
            cr.append(parts[1].strip())
    return fr, cr


def build_bidirectional_dataset(fr, cr):
    """Crée un dataset traduisant dans les DEUX sens (fr->cr et cr->fr)."""
    src, tgt, src_lang, tgt_lang = [], [], [], []
    for f, c in zip(fr, cr):
        # fr -> créole
        src.append(f); tgt.append(c); src_lang.append(SRC_LANG); tgt_lang.append(TGT_LANG)
        # créole -> fr
        src.append(c); tgt.append(f); src_lang.append(TGT_LANG); tgt_lang.append(SRC_LANG)
    return Dataset.from_dict({
        "src": src, "tgt": tgt, "src_lang": src_lang, "tgt_lang": tgt_lang,
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="training/data")
    ap.add_argument("--model", default="facebook/nllb-200-distilled-600M")
    ap.add_argument("--output-dir", default="training/nllb-fr-gcf")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--max-len", type=int, default=128)
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    train_fr, train_cr = load_tsv(data_dir / "train.tsv")
    dev_fr, dev_cr = load_tsv(data_dir / "dev.tsv")
    print(f"train={len(train_fr)}  dev={len(dev_fr)}")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)

    train_ds = build_bidirectional_dataset(train_fr, train_cr)
    dev_ds = build_bidirectional_dataset(dev_fr, dev_cr)

    def preprocess(batch):
        # Le code de langue source pilote la tokenisation NLLB
        tokenizer.src_lang = batch["src_lang"][0]
        model_inputs = tokenizer(
            batch["src"], max_length=args.max_len, truncation=True
        )
        labels = tokenizer(
            text_target=batch["tgt"], max_length=args.max_len, truncation=True
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    # batched par langue source homogène pour fixer src_lang correctement
    train_tok = train_ds.sort("src_lang").map(preprocess, batched=True, batch_size=32,
                                              remove_columns=train_ds.column_names)
    dev_tok = dev_ds.sort("src_lang").map(preprocess, batched=True, batch_size=32,
                                          remove_columns=dev_ds.column_names)

    collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    def compute_metrics(eval_pred):
        preds, labels = eval_pred
        if isinstance(preds, tuple):
            preds = preds[0]
        preds = np.where(preds != -100, preds, tokenizer.pad_token_id)
        labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
        decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
        chrf = sacrebleu.corpus_chrf(decoded_preds, [decoded_labels]).score
        bleu = sacrebleu.corpus_bleu(decoded_preds, [decoded_labels]).score
        return {"chrf": round(chrf, 2), "bleu": round(bleu, 2)}

    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=20,
        predict_with_generate=True,
        fp16=True,
        load_best_model_at_end=True,
        metric_for_best_model="chrf",
        report_to="none",
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_tok,
        eval_dataset=dev_tok,
        data_collator=collator,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"✅ Modèle sauvegardé dans {args.output_dir}")
    print("   Copiez ce dossier dans models/ pour que l'app le charge (utils/translator.py).")


if __name__ == "__main__":
    main()
