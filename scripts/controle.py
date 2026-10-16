"""Contrôle avant publication d'une vidéo verticale (TikTok, Reels, Shorts).

    controle.py VIDEO.mp4 [--format court|long] [--sans-voix] [--langue fr|en|auto] [--4k] [--ref AUTRE.mp4 …] [--cta mot …]

Mesuré dans le fichier, sur ton Mac, sans rien envoyer en ligne :
  - format 9:16, durée ;
  - texte lisible sans le son dans la première seconde (OCR macOS Vision) ;
  - la voix démarre tout de suite, sous-titres pendant la parole (Whisper + OCR) ;
  - rythme : plus long passage sans changement visuel ;
  - texte sous les boutons ou la description de TikTok / Instagram (zones de sécurité) ;
  - appel à l'action dans les dernières secondes ;
  - volume (LUFS intégrés, crête) et couleurs (yuv420p, plage TV, BT.709).
Écrit VIDEO.controle.md (rapport lisible) et VIDEO.controle.json à côté de la vidéo.
Ne prédit pas les vues : sert à corriger les défauts avant de publier.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OCR = HERE / "ocr"
FPS = 2  # images lues par seconde pour l'OCR
CTA_WORDS = ["comment", "bio", "lien", "abonne", "guide", "site", "réserv", "reserv", "suis-moi", "follow", "link", "subscribe"]
# Zones où TikTok / Instagram posent leurs boutons et leur description (coordonnées normalisées, origine en haut à gauche).
UNSAFE = {
    "boutons à droite": lambda x, y, w, h: x + w > 0.86 and 0.30 < y + h / 2 < 0.86,
    "description en bas": lambda x, y, w, h: y + h > 0.86,
    "onglets en haut": lambda x, y, w, h: y < 0.06,
}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(path)])
    d = json.loads(r.stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), {})
    a = any(s["codec_type"] == "audio" for s in d["streams"])
    return float(d["format"]["duration"]), int(v.get("width", 0)), int(v.get("height", 0)), a


def couleur(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt,color_range,color_space", "-of", "json", str(path)])
    st = json.loads(r.stdout)["streams"][0]
    return st.get("pix_fmt", "?"), st.get("color_range", "?"), st.get("color_space", "?")


def planche_couleur(path, refs):
    """Une image du milieu de la vidéo à côté de tes vidéos de référence : à regarder, pas à mesurer
    (saturation et contraste changent d'une scène à l'autre)."""
    imgs = []
    for src in [path] + [r for r in refs if r.exists() and r.resolve() != path]:
        d = float(json.loads(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(src)]).stdout)["format"]["duration"])
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{d * 0.35:.2f}", "-i", str(src), "-frames:v", "1", "-vf", "scale=540:960",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        if raw:
            imgs.append(np.frombuffer(raw, np.uint8).reshape(960, 540, 3))
    if len(imgs) < 2:
        return None
    out = path.with_suffix(".couleur.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{540 * len(imgs)}x960", "-i", "-", "-q:v", "3", str(out)],
                   input=np.concatenate(imgs, axis=1).tobytes())
    return out


def loudness(path):
    txt = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", txt)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", txt)
    return (float(i[-1]) if i else None), (float(p[-1]) if p else None)


def scene_changes(path, thr=0.12):
    r = run(["ffmpeg", "-hide_banner", "-i", str(path), "-vf", f"select='gt(scene,{thr})',showinfo", "-an", "-f", "null", "-"])
    return [float(m) for m in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def visual_events(path, ratio=3.0, floor=30.0, fps=5):
    """Changements visuels « nouveaux » : une zone de l'image (grille 6×4) change nettement plus que son niveau
    des 2 dernières secondes (carte qui apparaît, zoom, coupe), en ignorant la dérive continue et les gestes."""
    w, h = 108, 192
    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf", f"fps={fps},scale={w}:{h},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    if len(fr) < 2:
        return []
    d = np.abs(np.diff(fr, axis=0))
    gy, gx = 6, 4
    c = d.reshape(len(d), gy, h // gy, gx, w // gx).mean(axis=(2, 4)).reshape(len(d), -1)
    win = 2 * fps
    ev = []
    for i in range(len(c)):
        base = np.median(c[max(0, i - win): i], axis=0) if i > 0 else np.zeros(c.shape[1])
        if ((c[i] > ratio * (base + 2)) & (c[i] > floor)).any():
            t = (i + 1) / fps
            if not ev or t - ev[-1] > 0.6:
                ev.append(round(t, 2))
    return ev


def ocr_frames(path):
    with tempfile.TemporaryDirectory() as tmp:
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf", f"fps={FPS},scale=720:-2", "-q:v", "3", f"{tmp}/f_%05d.jpg"])
        r = run([str(OCR), tmp])
        data = json.loads(r.stdout or "[]")
    out = []
    for fr in data:
        n = int(re.search(r"(\d+)", fr["f"]).group(1))
        out.append({"t": (n - 1) / FPS, "items": [i for i in fr["items"] if len(i["t"].strip()) >= 2]})
    return out


def transcribe(path, langue):
    from faster_whisper import WhisperModel

    # Audio décodé par ffmpeg (16 kHz mono), sans dépendre de PyAV.
    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(audio, language=None if langue == "auto" else langue, word_timestamps=True, vad_filter=True)
    return [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for s in segs for w in (s.words or [])]


def fmt(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def main():
    ap = argparse.ArgumentParser(description="Contrôle avant publication d'une vidéo verticale.")
    ap.add_argument("video")
    ap.add_argument("--format", choices=["court", "long"], default="court", help="court = 25–45 s visés ; long = jusqu'à 90 s")
    ap.add_argument("--sans-voix", action="store_true", help="vidéo sans parole (pas de contrôle de la voix ni des sous-titres)")
    ap.add_argument("--langue", default="fr", help="langue parlée pour Whisper : fr, en… ou auto (défaut : fr)")
    ap.add_argument("--4k", dest="uhd", action="store_true", help="exiger une définition 2160×3840")
    ap.add_argument("--ref", nargs="*", default=[], help="tes vidéos de référence : planche « ta vidéo | réf » pour comparer les couleurs à l'œil")
    ap.add_argument("--cta", nargs="*", default=[], help="mots de ton appel à l'action en plus des mots courants (ex. ton mot-clé)")
    a = ap.parse_args()
    path = Path(a.video).expanduser().resolve()
    if not path.exists():
        sys.exit(f"Fichier introuvable : {path}")
    if not OCR.exists():
        sys.exit(f"OCR absent ({OCR}) : lance install.sh d'abord.")

    dur, w, h, has_audio = probe(path)
    lufs, peak = loudness(path) if has_audio else (None, None)
    cuts = sorted(set(round(t, 1) for t in scene_changes(path) + visual_events(path)))
    frames = ocr_frames(path)
    words = transcribe(path, a.langue) if (has_audio and not a.sans_voix) else []

    checks = []  # (niveau, titre, détail) — niveau : ok / attention / probleme

    def add(level, title, detail=""):
        checks.append((level, title, detail))

    ratio = h / w if w else 0
    add("ok" if abs(ratio - 16 / 9) < 0.02 else "probleme", "format 9:16", f"{w}×{h}")
    lo, hi = (25, 45) if a.format == "court" else (25, 90)
    add("ok" if lo <= dur <= hi else ("attention" if dur <= hi + 15 else "probleme"), "durée", f"{dur:.1f} s (visé : {lo}–{hi} s)")

    # Image : couleurs vidéo standard (sinon image grise ou délavée une fois publiée)
    pf, rng, csp = couleur(path)
    defauts = []
    if a.uhd and (w, h) != (2160, 3840):
        defauts.append(f"définition {w}×{h} (attendu 2160×3840)")
    if pf.startswith("yuvj") or rng == "pc" or csp in ("bt470bg", "smpte170m", "bt2020nc"):
        defauts.append(f"couleurs {pf} · {rng} · {csp} (attendu yuv420p · tv · bt709)")
    detail = f"{w}×{h} · {pf} · {rng} · {csp}"
    planche = planche_couleur(path, [Path(r).expanduser() for r in a.ref])
    if planche:
        detail += f" · planche à regarder : {planche.name}"
    add("probleme" if defauts else "ok", "image et couleurs", " ; ".join(defauts) + (" · " if defauts else "") + detail)

    first = [i["t"] for f in frames if f["t"] <= 1.0 for i in f["items"]]
    add("ok" if first else "probleme", "texte lisible sans le son dans la 1re seconde",
        " · ".join(dict.fromkeys(first))[:120] or "aucun texte détecté entre 0 et 1 s")

    if words:
        s0 = words[0]["s"]
        add("ok" if s0 <= 0.7 else ("attention" if s0 <= 1.5 else "probleme"), "la voix démarre tout de suite", f"premier mot à {s0:.2f} s (« {words[0]['w']} »)")
        speech = [f for f in frames if any(wd["s"] - 0.25 <= f["t"] <= wd["e"] + 0.25 for wd in words)]
        cov = len([f for f in speech if f["items"]]) / len(speech) if speech else 1
        holes = [fmt(f["t"]) for f in speech if not f["items"]][:8]
        add("ok" if cov >= 0.85 else ("attention" if cov >= 0.6 else "probleme"), "sous-titres pendant la parole",
            f"{cov:.0%} du temps de parole" + (f" · sans texte vers {', '.join(holes)}" if holes else ""))

    marks = [0.0] + cuts + [dur]
    gaps = [(marks[i], marks[i + 1] - marks[i]) for i in range(len(marks) - 1)]
    long_gaps = [(t, g) for t, g in gaps if g > 4.0]
    worst = max((g for _, g in gaps), default=0)
    early = [c for c in cuts if 0.3 <= c <= 3.0]
    add("ok" if not long_gaps else ("attention" if worst <= 6 else "probleme"), "un changement visuel toutes les 2–4 s",
        f"{len(cuts)} changements · plus long passage sans changement {worst:.1f} s"
        + (f" · à revoir : {', '.join(f'{fmt(t)} ({g:.1f} s)' for t, g in long_gaps[:6])}" if long_gaps else ""))
    add("ok" if early else "attention", "rupture visuelle dans les 3 premières secondes",
        f"{len(early)} changement(s) avant 3 s" if early else "aucun changement visuel avant 3 s")

    bad = {}
    for f in frames:
        for i in f["items"]:
            for zone, test in UNSAFE.items():
                if test(i["x"], i["y"], i["w"], i["h"]):
                    bad.setdefault(zone, []).append((f["t"], i["t"]))
    if bad:
        add("attention", "texte dans les zones des boutons ou de la description",
            " · ".join(f"{z} : « {v[0][1][:30]} » vers {fmt(v[0][0])} ({len(v)} fois)" for z, v in bad.items()))
    else:
        add("ok", "aucun texte sous les boutons ni sous la description")

    end_words = " ".join(wd["w"] for wd in words if wd["s"] >= dur - 7).lower()
    end_text = " ".join(i["t"] for f in frames if f["t"] >= dur - 7 for i in f["items"]).lower()
    cta = [k for k in CTA_WORDS + [c.lower() for c in a.cta] if k in end_words or k in end_text]
    add("ok" if cta else "attention", "appel à l'action dans les 7 dernières secondes", ", ".join(cta) if cta else "rien trouvé (commente, bio, lien, guide…)")

    if lufs is not None:
        lvl = "ok" if -16 <= lufs <= -12 else ("attention" if -19 <= lufs <= -10 else "probleme")
        add(lvl, "volume", f"{lufs:.1f} LUFS (visé : −14 ± 2)" + (f" · crête {peak:.1f} dBFS" if peak is not None else ""))
        if peak is not None and peak > -1.0:
            add("attention", "crête trop haute", f"{peak:.1f} dBFS (visé ≤ −1)")
    elif not has_audio:
        add("probleme", "son", "aucune piste audio")

    icons = {"ok": "✅", "attention": "⚠️", "probleme": "❌"}
    n = {k: sum(1 for c in checks if c[0] == k) for k in icons}
    summary = f"{n['ok']} ✅ · {n['attention']} ⚠️ · {n['probleme']} ❌"
    lines = [f"# Contrôle avant publication · {path.name}", "", f"**{summary}** · {dur:.1f} s", ""]
    for lvl in ("probleme", "attention", "ok"):
        lines += [f"- {icons[l]} **{t}**" + (f" : {d}" if d else "") for l, t, d in checks if l == lvl]
    lines += ["", "_Mesuré dans le fichier (ffmpeg, OCR macOS, Whisper small). Ne prédit pas les vues : sert à corriger avant de publier._"]
    report = "\n".join(lines)
    path.with_suffix(".controle.md").write_text(report + "\n")
    path.with_suffix(".controle.json").write_text(json.dumps({"video": str(path), "duree": dur, "resume": summary, "checks": checks, "cuts": cuts,
                                                              "lufs": lufs, "peak": peak, "mots": words}, ensure_ascii=False, indent=1))
    print(report)


if __name__ == "__main__":
    main()
