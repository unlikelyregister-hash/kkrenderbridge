# Input Folder — Where to Put Inspiration Images

This is the single place to drop your inspiration images.

```
kk-workspace/
├── input/
│   ├── looks/                    # Surface traits (hair/eye/skin color, hair style)
│   │   └── sarah/               # ← one look = one folder with .png card(s)
│   │       └── Koikatu_F_...png
│   └── styles/                   # Structural traits (face shape, body shape, features)
│       └── round_face/          # ← one style = one folder with multiple .png cards
│           ├── b7d8c72...png
│           └── KK_319725.png
```

## How to use

1. Drop your inspiration `.png` card(s) into `input/looks/<name>/` — one folder per look
2. Drop multiple `.png` cards that share a style into `input/styles/<style_name>/` — one folder per style, multiple cards per folder
3. Run:
   ```
   python card_builder.py \
       --look "input/looks/sarah/*.png" \
       --style "input/styles/round_face" \
       --output out/my_character.kkpe
   ```

## What each folder controls

| Folder | Controls | Read by |
|--------|----------|---------|
| `input/looks/<name>/` | hair color, eye color, skin tone, hair style | `apply_look_traits()` via WD tagging |
| `input/styles/<name>/` | shapeValueFace (52 sliders), shapeValueBody (44 sliders), noseId, lipLineId, eyebrowId, headId, bustWeight | `apply_style_traits()` via slider calibration |

## Source of example cards

The example cards in `input/` were copied from your Koikatsu installation:
- `input/looks/sarah/` — from `C:\Games\Koikatsu\UserData\chara\female\IA2\Sarah\Cards\`
- `input/styles/round_face/` — from `C:\Games\Koikatsu\UserData\chara\female\[Community]\`

You can replace these with your own inspiration images at any time — just drop `.png` character cards into the folders.

## Where output goes

Built cards go to `out/` (created automatically if missing).
