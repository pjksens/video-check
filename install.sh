#!/bin/bash
# Installe le skill video-check (macOS uniquement) : ffmpeg, environnement Python, OCR macOS Vision, modèle Whisper.
# Relançable sans risque : chaque étape vérifie si elle est déjà faite.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
say() { printf '\n▸ %s\n' "$1"; }

[ "$(uname)" = "Darwin" ] || { echo "Ce skill ne marche que sur Mac (OCR macOS Vision)."; exit 1; }

say "Outils du Mac (swiftc)"
if ! xcrun --find swiftc >/dev/null 2>&1; then
  echo "Il faut les outils en ligne de commande d'Apple. Lance : xcode-select --install"
  echo "puis relance ce script quand l'installation est finie."
  exit 1
fi

say "ffmpeg"
if ! command -v ffmpeg >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then brew install ffmpeg
  else echo "Installe Homebrew (https://brew.sh) puis relance ce script, ou installe ffmpeg toi-même."; exit 1; fi
fi
ffmpeg -version | head -1

say "Python (environnement à part, dans le dossier du skill)"
PY="$(command -v python3 || true)"
[ -n "$PY" ] || { echo "python3 introuvable : installe-le (brew install python) puis relance."; exit 1; }
[ -x "$DIR/.venv/bin/python" ] || "$PY" -m venv "$DIR/.venv"
"$DIR/.venv/bin/python" -m pip install --quiet --upgrade pip
"$DIR/.venv/bin/python" -m pip install --quiet numpy pillow faster-whisper

say "OCR macOS Vision"
xcrun swiftc -O "$DIR/scripts/ocr.swift" -o "$DIR/scripts/ocr"

say "Modèle Whisper « small » (~460 Mo, une seule fois)"
"$DIR/.venv/bin/python" -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

say "Prêt."
echo "Dans Claude Code : « analyse cette vidéo : … » ou « contrôle ma vidéo avant de la publier : … »"
