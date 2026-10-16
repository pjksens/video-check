# video-check

Skill Claude Code pour tes vidéos verticales (TikTok, Reels, Shorts). Deux commandes. Les mesures tournent sur ton Mac (les scripts n'envoient rien en ligne) ; Claude regarde ensuite les planches d'images et le rapport pour te répondre :

- **Analyser une vidéo de référence** : coupes et changements image par image, planches de 2 images par seconde, transcription horodatée. Claude regarde les planches et te dit comment la vidéo est montée (accroche, rythme, plans, sous-titres, fin).
- **Contrôler ta vidéo avant de publier** : format, texte dans la première seconde, voix et sous-titres, rythme, texte sous les boutons de TikTok / Instagram, appel à l'action, volume, couleurs. Rapport ✅ / ⚠️ / ❌ avec le moment exact de chaque défaut.

Ça mesure et ça détecte des défauts. Ça ne prédit pas les vues.

## Installer (macOS)

Colle ceci dans Claude Code :

```
Installe le skill video-check : clone https://github.com/pjksens/video-check dans ~/.claude/skills/video-check, puis lance bash ~/.claude/skills/video-check/install.sh et dis-moi si une étape échoue.
```

Ou à la main :

```bash
git clone https://github.com/pjksens/video-check ~/.claude/skills/video-check && bash ~/.claude/skills/video-check/install.sh
```

Il faut : macOS, les outils en ligne de commande d'Apple (`xcode-select --install`), Homebrew ou ffmpeg déjà installé, python3. Le script installe ffmpeg si besoin, un environnement Python à part (numpy, pillow, faster-whisper), compile l'OCR macOS Vision et télécharge le modèle Whisper « small » (~460 Mo, une fois).

## Utiliser

Dans Claude Code :

- « Analyse cette vidéo : ~/Downloads/reel.mp4 »
- « Contrôle ma vidéo avant de la publier : ~/Movies/ma-video.mp4 »

Les vidéos à analyser doivent être sur ton Mac : le skill ne télécharge rien.

## Licence

MIT
