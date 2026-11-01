#!/usr/bin/env python3
"""Сравнивает эталонный перевод transformers (жадный) с нашим ONNX-конвейером на Python."""
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from transformers import MarianMTModel, MarianTokenizer

name, d = sys.argv[1], Path(sys.argv[2])
sentences = sys.argv[3:]
tok = MarianTokenizer.from_pretrained(name)
model = MarianMTModel.from_pretrained(name)
cfg = json.load(open(d / "config.json"))
enc = ort.InferenceSession(str(d / "encoder.onnx"))
dec = ort.InferenceSession(str(d / "decoder.onnx"))
print("encoder inputs", [i.name for i in enc.get_inputs()], "decoder inputs", [i.name for i in dec.get_inputs()],
      "decoder outputs", [o.name for o in dec.get_outputs()][:3])
for s in sentences:
    batch = tok([s], return_tensors="pt")
    ref = tok.decode(model.generate(**batch, num_beams=1, max_new_tokens=128)[0], skip_special_tokens=True)
    ids = batch["input_ids"].numpy()
    mask = np.ones_like(ids)
    hidden = enc.run(None, {"input_ids": ids, "attention_mask": mask})[0]
    out = [cfg["decoder_start"]]
    for _ in range(128):
        logits = dec.run(None, {"input_ids": np.array([out]), "encoder_hidden_states": hidden, "encoder_attention_mask": mask})[0]
        row = logits[0, -1].copy()
        row[cfg["pad"]] = -1e9
        nxt = int(row.argmax())
        if nxt == cfg["eos"]:
            break
        out.append(nxt)
    ours = tok.decode(out[1:], skip_special_tokens=True)
    print(f"SRC: {s}\nREF: {ref}\nINT8: {ours}\nTOKENS: {tok.convert_ids_to_tokens(ids[0])}\n")
