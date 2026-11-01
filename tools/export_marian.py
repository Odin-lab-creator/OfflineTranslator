#!/usr/bin/env python3
"""Экспорт Opus-MT (MarianMT) в ONNX int8 для приложения.

Использование: export_marian.py Helsinki-NLP/opus-mt-en-ru out_dir
В out_dir: encoder.onnx, decoder.onnx, tokenizer.json (кусочки SentencePiece), vocab.json, config.json.
"""
import json
import shutil
import sys
from pathlib import Path

import sentencepiece as spm
from huggingface_hub import hf_hub_download
from onnxruntime.quantization import QuantType, quantize_dynamic
from optimum.exporters.onnx import main_export
from transformers import MarianTokenizer

name, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
tmp = Path("tmp_export") / out.name
main_export(name, output=tmp, task="text2text-generation", opset=14)
print(sorted(p.name for p in tmp.iterdir()))
quantize_dynamic(str(tmp / "encoder_model.onnx"), str(out / "encoder.onnx"), weight_type=QuantType.QInt8)
quantize_dynamic(str(tmp / "decoder_model.onnx"), str(out / "decoder.onnx"), weight_type=QuantType.QInt8)

tok = MarianTokenizer.from_pretrained(name)
sp = spm.SentencePieceProcessor(model_file=hf_hub_download(name, "source.spm"))
pieces = []
for i in range(sp.get_piece_size()):
    kind = 1
    if sp.is_unknown(i):
        kind = 2
    elif sp.is_control(i):
        kind = 3
    elif sp.is_unused(i):
        kind = 5
    elif sp.is_byte(i):
        kind = 6
    pieces.append([sp.id_to_piece(i), sp.get_score(i), kind])
with open(out / "tokenizer.json", "w", encoding="utf-8") as f:
    json.dump({"pieces": pieces}, f, ensure_ascii=False)
shutil.copy(hf_hub_download(name, "vocab.json"), out / "vocab.json")
cfg = json.load(open(hf_hub_download(name, "config.json")))
with open(out / "config.json", "w") as f:
    json.dump(
        {
            "model": name,
            "pad": cfg["pad_token_id"],
            "eos": cfg["eos_token_id"],
            "unk": tok.unk_token_id,
            "decoder_start": cfg.get("decoder_start_token_id", cfg["pad_token_id"]),
            "max_length": 256,
        },
        f,
    )
shutil.rmtree(tmp, ignore_errors=True)
print("exported", name)
