"""Analyse image par image d'une vidéo de référence.

  frames.py VIDEO DOSSIER_SORTIE
- lit TOUTES les images (à la cadence de la vidéo), réduites à 72×128 en niveaux de gris ;
- différence avec l'image précédente : globale (coupe franche) et par zone 6 colonnes × 8 lignes (incrustation qui
  apparaît / disparaît, texte qui change) ;
- events.json : chaque événement (temps, type, zones touchées) ;
- planches : sheet_XX.jpg = 2 images/s, 6 colonnes × 3 lignes (9 s par planche), avec le temps ;
- events_XX.jpg = l'image juste après chaque événement (pour voir chaque changement).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) != 3:
    sys.exit("usage : frames.py VIDEO DOSSIER_SORTIE")
video, out = Path(sys.argv[1]).expanduser(), Path(sys.argv[2]).expanduser()
out.mkdir(parents=True, exist_ok=True)
W, H = 72, 128
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"scale={W}:{H}", "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                     capture_output=True, check=True).stdout
frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W).astype(np.int16)
rate = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate",
                       "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip()
num, _, den = rate.partition("/")
fps = float(num) / float(den or 1) if num and float(den or 1) else 30.0
n = len(frames)

# différences
glob = [0.0] + [float(np.abs(frames[i] - frames[i - 1]).mean()) for i in range(1, n)]
gx, gy = 6, 8
zw, zh = W // gx, H // gy
def zones(i):
    d = np.abs(frames[i] - frames[i - 1])
    return d.reshape(gy, zh, gx, zw).mean(axis=(1, 3))

events = []
last = -99
for i in range(1, n):
    z = zones(i)
    g = glob[i]
    if g > 28:
        kind = "coupe"
    elif z.max() > 30 and (z > 30).sum() <= 24:
        kind = "local"
    elif g > 12:
        kind = "changement"
    else:
        continue
    if i - last < 3:  # même événement sur plusieurs images
        continue
    last = i
    hot = [(int(r), int(c)) for r, c in zip(*np.where(z > 30))]
    rows = sorted({r for r, _ in hot})
    events.append({"frame": i, "t": round(i / fps, 2), "type": kind, "global": round(g, 1),
                   "zones_hautes": len(hot), "lignes": rows})

json.dump({"frames": n, "fps": fps, "events": events}, open(out / "events.json", "w"), indent=1)

# planches
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
except Exception:
    font = ImageFont.load_default()
TW, TH = 240, 427

def grab(t):
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={TW}:{TH}",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    from io import BytesIO
    return Image.open(BytesIO(png)).convert("RGB") if png else Image.new("RGB", (TW, TH))

def sheet(times, path, cols=6):
    rows = (len(times) + cols - 1) // cols
    im = Image.new("RGB", (cols * TW, rows * (TH + 30)), "white")
    d = ImageDraw.Draw(im)
    for k, t in enumerate(times):
        x, y = (k % cols) * TW, (k // cols) * (TH + 30)
        im.paste(grab(t), (x, y + 30))
        d.text((x + 6, y + 3), f"{t:.2f}s", fill="black", font=font)
    im.save(path, quality=82)

dur = n / fps
ts = [round(k * 0.5, 2) for k in range(int(dur * 2) + 1)]
for s in range(0, len(ts), 18):
    sheet(ts[s:s + 18], out / f"sheet_{s // 18:02d}.jpg")
ev_t = [round(e["t"] + 2 / fps, 3) for e in events]
for s in range(0, len(ev_t), 18):
    sheet(ev_t[s:s + 18], out / f"events_{s // 18:02d}.jpg")
print(video.name, n, "images,", len(events), "événements,", sum(1 for e in events if e["type"] == "coupe"), "coupes")
