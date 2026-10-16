"""Transcription mot à mot avec horodatage (Whisper small, sur le Mac).

    transcrire.py VIDEO [--langue fr|en|auto]

Écrit VIDEO.transcription.json ([{w, s, e}] : mot, début, fin en secondes) et affiche le texte avec les temps.
"""
import argparse
import json
from pathlib import Path

from controle import transcribe

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--langue", default="auto")
a = ap.parse_args()
path = Path(a.video).expanduser().resolve()
words = transcribe(path, a.langue)
path.with_suffix(".transcription.json").write_text(json.dumps(words, ensure_ascii=False, indent=1))
line, start = [], None
for w in words:
    start = w["s"] if start is None else start
    line.append(w["w"])
    if w["w"].endswith((".", "?", "!")) or len(line) >= 12:
        print(f"[{start:6.2f}] {' '.join(line)}")
        line, start = [], None
if line:
    print(f"[{start:6.2f}] {' '.join(line)}")
