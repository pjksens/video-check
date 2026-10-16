---
name: video-check
description: Analyse image par image d'une vidéo verticale (TikTok, Reels, Shorts) et contrôle avant publication. Use when the user asks to analyse a reference video (« analyse cette vidéo », « décortique ce reel », « comment est montée cette vidéo ») or to check their own video before posting (« contrôle ma vidéo », « elle est prête à publier ? », « vérifie avant que je poste »). macOS only.
---

# video-check

Deux commandes. Les mesures tournent sur le Mac de l'utilisateur ; les scripts n'envoient rien en ligne. Toi, tu regardes les planches d'images et le rapport (comme toute image qu'on te montre).

`SKILL_DIR` = le dossier de ce fichier (en général `~/.claude/skills/video-check`).
Python = `$SKILL_DIR/.venv/bin/python`. Si ce fichier ou `$SKILL_DIR/scripts/ocr` manque, lance d'abord `bash $SKILL_DIR/install.sh`.

## 1. Analyser une vidéo de référence (comment elle est montée)

L'utilisateur donne un fichier vidéo qu'il a sur son Mac. Ce skill ne télécharge pas de vidéos : s'il n'a qu'un lien, demande-lui le fichier.

1. `$SKILL_DIR/.venv/bin/python $SKILL_DIR/scripts/frames.py VIDEO DOSSIER` avec `DOSSIER` = `<nom de la vidéo>-analyse` à côté de la vidéo.
   Écrit `events.json` (chaque coupe ou changement local, avec son temps), `sheet_XX.jpg` (2 images par seconde) et `events_XX.jpg` (l'image juste après chaque changement).
2. Transcription avec horodatage : `$SKILL_DIR/.venv/bin/python $SKILL_DIR/scripts/transcrire.py VIDEO` (écrit `VIDEO.transcription.json`).
3. **Regarde vraiment les planches** (outil Read sur chaque `sheet_XX.jpg` et `events_XX.jpg`). Ne décris jamais une image que tu n'as pas ouverte.
4. Rends une fiche courte :
   - l'accroche des 3 premières secondes : ce qu'on voit, ce qu'on entend, le texte à l'écran ;
   - le rythme : nombre de coupes, temps moyen entre deux changements, passages lents ;
   - les types de plans qui alternent (face caméra, écran, gros plan, incrustation…) ;
   - les sous-titres : taille, position, nombre de mots ;
   - la fin et l'appel à l'action ;
   - 3 idées précises à reprendre pour ses vidéos.

   Chiffres tirés de `events.json` et de la transcription. Ce que tu interprètes, dis-le.

## 2. Contrôler sa vidéo avant publication

`$SKILL_DIR/.venv/bin/python $SKILL_DIR/scripts/controle.py VIDEO [--format court|long] [--sans-voix] [--langue fr|en|auto] [--4k] [--ref REF.mp4 …] [--cta MOT …]`

- `--format long` si la vidéo vise plus de 45 s. `--sans-voix` si personne ne parle.
- `--cta` : son mot-clé d'appel à l'action s'il n'est pas dans la liste courante (commente, bio, lien, guide…).
- `--ref` : une ou deux de ses vidéos dont il aime l'image. Le script écrit `VIDEO.couleur.jpg` : ouvre-la et compare à l'œil.

Le script écrit `VIDEO.controle.md` et `VIDEO.controle.json`. Donne le résumé (✅ / ⚠️ / ❌), puis pour chaque ❌ et ⚠️ : ce qui ne va pas, à quel moment (m:ss), et comment le corriger.
Si la vidéo vient de son propre montage (Remotion, CapCut, Premiere…), propose la correction concrète.

## Règles

- Ce skill mesure et détecte des défauts. Il ne prédit pas les vues : ne promets jamais qu'une vidéo va marcher.
- Ne publie rien, n'envoie rien en ligne.
- Premier lancement de la transcription : Whisper peut mettre une minute à charger.
