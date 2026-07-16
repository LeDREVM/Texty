#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fine-tuning de Whisper pour la reconnaissance vocale (ASR) du créole guadeloupéen.

⚠️ À EXÉCUTER SUR UNE MACHINE AVEC GPU (Google Colab / Kaggle / serveur GPU).
   Ne fonctionne pas dans l'environnement web du projet (pas de GPU, pas de PyPI).

Le créole guadeloupéen n'a pas de jeton de langue dédié dans Whisper : on utilise
le français (« French ») comme langue proxy, par transfert. Le modèle apprend le
créole à partir de tes données audio transcrites.

Données : produites par training/prepare_asr_data.py (train.csv / dev.csv, colonnes
          audio_path,text). Audio de préférence 16 kHz mono.
Dépendances : voir training/requirements-train.txt

Exemple :
    python training/finetune_whisper_creole.py \
        --manifest-dir training/asr_data \
        --base-model openai/whisper-small \
        --output-dir training/whisper-creole \
        --epochs 10 --batch-size 8
"""

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Dict, Union

import torch
import evaluate
from datasets import Dataset, Audio
from transformers import (
    WhisperProcessor,
    WhisperForConditionalGeneration,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)


def load_manifest(path: Path):
    rows = []
    with open(path, newline='', encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            audio = (row.get('audio_path') or '').strip()
            text = (row.get('text') or '').strip()
            if audio and text:
                rows.append({'audio': audio, 'text': text})
    return rows


def to_dataset(rows):
    ds = Dataset.from_dict({
        'audio': [r['audio'] for r in rows],
        'text': [r['text'] for r in rows],
    })
    return ds.cast_column('audio', Audio(sampling_rate=16000))


@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any

    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]):
        input_features = [{'input_features': f['input_features']} for f in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors='pt')
        label_features = [{'input_ids': f['labels']} for f in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors='pt')
        labels = labels_batch['input_ids'].masked_fill(labels_batch.attention_mask.ne(1), -100)
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]
        batch['labels'] = labels
        return batch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest-dir', default='training/asr_data')
    ap.add_argument('--base-model', default='openai/whisper-small')
    ap.add_argument('--language', default='French')  # proxy pour le créole
    ap.add_argument('--output-dir', default='training/whisper-creole')
    ap.add_argument('--epochs', type=int, default=10)
    ap.add_argument('--batch-size', type=int, default=8)
    ap.add_argument('--lr', type=float, default=1e-5)
    args = ap.parse_args()

    processor = WhisperProcessor.from_pretrained(
        args.base_model, language=args.language, task='transcribe'
    )
    model = WhisperForConditionalGeneration.from_pretrained(args.base_model)
    model.generation_config.language = args.language.lower()
    model.generation_config.task = 'transcribe'
    model.generation_config.forced_decoder_ids = None

    mdir = Path(args.manifest_dir)
    train_ds = to_dataset(load_manifest(mdir / 'train.csv'))
    dev_ds = to_dataset(load_manifest(mdir / 'dev.csv'))
    print(f"train={len(train_ds)}  dev={len(dev_ds)}")

    def prepare(batch):
        audio = batch['audio']
        batch['input_features'] = processor.feature_extractor(
            audio['array'], sampling_rate=16000
        ).input_features[0]
        batch['labels'] = processor.tokenizer(batch['text']).input_ids
        return batch

    train_ds = train_ds.map(prepare, remove_columns=train_ds.column_names)
    dev_ds = dev_ds.map(prepare, remove_columns=dev_ds.column_names)

    collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)
    wer_metric = evaluate.load('wer')

    def compute_metrics(pred):
        pred_ids = pred.predictions
        label_ids = pred.label_ids
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
        pred_str = processor.tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = processor.tokenizer.batch_decode(label_ids, skip_special_tokens=True)
        return {'wer': 100 * wer_metric.compute(predictions=pred_str, references=label_str)}

    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        fp16=torch.cuda.is_available(),
        eval_strategy='epoch',
        save_strategy='epoch',
        predict_with_generate=True,
        generation_max_length=225,
        logging_steps=20,
        report_to='none',
        load_best_model_at_end=True,
        metric_for_best_model='wer',
        greater_is_better=False,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=dev_ds,
        data_collator=collator,
        compute_metrics=compute_metrics,
        tokenizer=processor.feature_extractor,
    )

    trainer.train()
    trainer.save_model(args.output_dir)
    processor.save_pretrained(args.output_dir)
    print(f"✅ Modèle affiné dans {args.output_dir}  (WER = plus bas = mieux)")
    print("\nPour l'utiliser dans l'app, convertis-le au format faster-whisper (CTranslate2) :")
    print(f"  ct2-transformers-converter --model {args.output_dir} "
          f"--output_dir {args.output_dir}-ct2 --quantization int8")
    print("Puis pointe la variable d'environnement du backend dessus :")
    print(f"  CREOLE_MODEL_PATH={args.output_dir}-ct2")


if __name__ == '__main__':
    main()
