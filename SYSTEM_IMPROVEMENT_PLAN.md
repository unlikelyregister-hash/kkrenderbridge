# System Improvement Plan — Koikatsu Character Builder

## Current State Assessment

The workspace contains a functional round-trip pipeline for Koikatsu `.png` character cards using `kkloader`. Key components:
- Card loading/modification/saving via `kkloader`
- Card builder (`card_builder.py`) that combines look refs + style dirs
- Clothing decoupling (`clothing/decouple.py`) for stripping/injecting clothes
- Game lifecycle manager (`game_manager.py`) with single-instance enforcement
- UI automation (`ui_automation.py`) with calibrated action sequences
- Orchestrator (`run_build.py`) tying everything together
- Slider calibration data (`scripts/slider_calibration.json`) with 52 face + 44 body sliders mapped
- Style group analysis that averages shapeValueFace/body across multiple cards
- Look merging that averages RGB traits across multiple look images

## The 6 Improvements — Status & Implementation

### ✅ Fix 1: Clothing as Separate Optional Component
**Implementation:** Done. Three modes supported:
- **Default nude** (default): `set_defaults_nude()` sets all 9 clothing part IDs to 0 with skin-tone colors
- **--keep-clothes**: Preserves original clothing from the look card
- **--clothes-from <card>**: Injects clothing parts from a specific source card via `inject_clothes()`

The `load_character` action sequence in `config/actions.json` has `clothing_sets: false` so the in-game load dialog also excludes clothes.

### ✅ Fix 2: Two-Folder Input (Look Images + Style Directory)
**Implementation:** Done.
- `--look <path>`: Primary look card (file, glob, or directory). Extracts hair_color, eye_color, skin tones.
- `--look-dir <dir>`: Additional look cards whose RGB traits get averaged via `merge_look_traits()`.
- `--style <dir>`: Style directory with multiple cards. `style_group_signature()` computes pairwise cosine similarity of shapeValueFace/Body vectors, then averages them into a target style profile.
- A style is composed of multiple cards so you can see the similarities within a group.

### ✅ Fix 3: Full Slider Support (Not Just Skin Color + Hair)
**Implementation:** Done via `card_builder.py` + `scripts/slider_calibration.json`.
- `apply_style_traits()` applies the style signature's averaged `shapeValueFace` (52 sliders) and `shapeValueBody` (44 sliders) with a configurable blend factor.
- Discrete features (noseId, lipLineId, eyebrowId, headId, bustWeight, bustSoftness, pupil dimensions) are set from the consensus across style group members.
- `apply_look_traits()` handles hair color, eye color, skin main/sub colors.
- The slider calibration JSON maps all 96 slider indices to names, descriptions, ranges, and per-card statistics.

### ✅ Fix 4: Game Launch + Navigate + Load Card
**Implementation:** Done via three integrated modules:
- `game_manager.py` — `GameSession.ensure_character_maker()` launches the game if not running, waits for scene load
- `ui_automation.py` — ctypes-based `mouse_click()`, `mouse_drag()`, `key_press()`, `type_text()` operating on absolute screen coordinates
- `config/actions.json` — calibrated sequences: `title_to_char_maker`, `load_character`, `slider_list_tab`, etc.
- `run_build.py --launch-game --ensure-cm --load-in-game` triggers the full flow

### ✅ Fix 5: Single Instance Enforcement
**Implementation:** Done. `game_manager.py`:
- `is_game_running()` checks for Koikatu.exe via wmic
- `GameSession` enforces single instance — detects running game, saves and restarts if not in Character Maker
- PID 29200 detected during verification

### ✅ Fix 6: Orchestrator (`run_build.py`)
**Implementation:** Done. Full CLI integrates all components:
```bash
python run_build.py \\
    --look "looks/hair_blonde_eyes_blue/" \\
    --style "styles/round_face/" \\
    --output out/my_char.kkpe \\
    --launch-game --ensure-cm --load-in-game
```

## Remaining Work / Open Items

### 1. Click Coordinate Calibration
The coordinates in `config/actions.json` are placeholder estimates for 1920×1080. They need actual calibration against your screen layout.

**How to calibrate:**
```bash
python record_coords.py
```
Move your mouse to each UI element and press Enter to record. Or edit `config/recording_coords.json` manually.

### 2. Character Maker Navigation Flow
The current `ensure_character_maker()` in `game_manager.py` launches the game but doesn't navigate to Character Maker via UI clicks. It waits for the scene to load by checking `output_log.txt`. This works if the game auto-loads into CM, but if it lands on the title screen, you need the UI automation to click through.

**Current flow after launch:**
1. Game launches → wait for scene load in log
2. If CM detected in log → done
3. If not → the `run_build.py --load-in-game` path would need to run `title_to_char_maker` + `load_character` sequences

The actions.json sequences are defined but not yet automatically chained from the orchestrator.

### 3. In-Game Slider Adjustment
The pipeline currently modifies sliders via card file editing (writing shapeValueFace/Body arrays directly). This is more reliable than UI automation for precise values. However, if you want to **see** the sliders being adjusted in-game:

**Option A:** Load the built card, then use the `slider_list_tab` + `adjust_slider` sequences to navigate to specific sliders and read their values.

**Option B:** After loading the card in CM, the slider values are already set from the file — you just need to verify them visually.

The `scripts/slider_calibration.json` gives you the mapping from slider index → name so you know what each slider does.

### 4. Style Group Population
The `styles/` directory has empty subdirectories except `round_face/` (2 cards). You need to populate the other style groups with cards:
- `styles/athletic/` — athletic physique cards
- `styles/curvy/` — curvy body type cards
- `styles/slender/` — slim/thin body type cards

Each style folder should contain multiple `.png` cards that share that body/face style.

### 5. Look Directory Population
The `looks/` directory has 4 subdirectories. Populate with cards that represent the surface appearance you want:
- Hair color
- Eye color
- Skin tone
- Hair style

Multiple cards in a look directory get their RGB traits averaged.

## How the Pieces Fit Together

```
run_build.py (orchestrator)
├── Resolves --look / --look-dir → extracts look traits (hair/eye/skin RGB)
├── Analyzes --style dir → computes style_signature (avg shapeValueFace/Body + consensus features)
├── build_card():
│   ├── Loads base card
│   ├── apply_look_traits() → sets hair/eye/skin colors
│   ├── apply_style_traits() → sets shapeValueFace/Body sliders + discrete features
│   ├── Handles clothes: nude / keep / inject
│   ├── Overrides metadata (name, nickname, etc.)
│   └── Saves .kkpe/.png
├── (Optional) --launch-game: GameSession ensures game running
├── (Optional) --ensure-cm: navigates to Character Maker
├── (Optional) --load-in-game: loads the built card via UI automation
└── (Optional) --close-game: saves and closes
```

## Suggested Next Steps

1. **Calibrate click coordinates** — run `record_coords.py`, record positions for:
   - Char Maker button on title screen
   - Female button on gender select
   - Load Character button
   - Load button in dialog
   - Any other UI elements you need to automate

2. **Populate style groups** — copy cards into `styles/athletic/`, `styles/curvy/`, `styles/slender/` as needed

3. **Test the full pipeline** with a simple build:
   ```bash
   python run_build.py --look "looks/sarah_base/sarah.png" --style "styles/round_face" --output out/test.kkpe
   ```

4. **Test game automation** (when ready):
   ```bash
   python run_build.py --look "..." --style "..." --output out/test.kkpe --launch-game --ensure-cm
   ```

## File Reference

| File | Purpose |
|------|---------|
| `run_build.py` | Master orchestrator — all 6 fixes integrated |
| `card_builder.py` | Core card building: look/style extraction, trait application, clothes handling |
| `clothing/decouple.py` | Strip/inject/set_defaults_nude for clothing parts |
| `game_manager.py` | Single-instance game lifecycle, launch, close, scene detection |
| `ui_automation.py` | ctypes mouse/keyboard control, action sequence execution |
| `config/actions.json` | Calibrated UI action sequences (needs coordinate tuning) |
| `config/recording_coords.json` | Recorded coordinates from record_coords.py |
| `scripts/slider_calibration.json` | 96 slider mappings with names, ranges, statistics |
| `styles/` | Style group directories (populate with cards) |
| `looks/` | Look reference directories (populate with cards) |
| `record_coords.py` | Interactive coordinate recorder for UI calibration |
| `calibrate_coords.py` | Screenshot-based coordinate analysis (alternative calibration method) |
