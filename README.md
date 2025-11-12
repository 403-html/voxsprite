# VoxSprite

Lightweight PyQt6 desktop panel for driving voice-reactive PNG avatars. The UI reacts to live microphone input, toggles talking frames based on configurable thresholds, animates idle sequences, and exposes chroma/layer controls for overlays.

https://github.com/user-attachments/assets/fd7eec60-adce-4668-95f8-f4943ad3afc5

## Requirements

- Python 3.10+  
- macOS or Windows with an accessible default microphone device

Install dependencies inside your preferred virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Project Layout

```
vox_sprite/       Application package (UI, audio, widgets, translations)
voice_reactor.json  User settings (auto-created on first save)
main.py           Convenience launcher (equivalent to `python -m vox_sprite`)
```

No binaries are produced; run the code directly:

```bash
python3 main.py
# or
python3 -m vox_sprite
```

The panel opens immediately and persists its state to `voice_reactor.json` in the project root.

### Assets & Defaults

Inputs for idle/talking frames start empty. Use the UI to add your own PNGs. Idle/talk thresholds, transparency, and window behaviors are fully configurable before saving.

### Translations

Select the UI language from the drop-down in the top-left corner of the panel. The list is built from JSON files in `vox_sprite/translations/` (each file exposes a `language.name`). Switching languages rebuilds the window instantly while preserving your current settings. The `VOXSPRITE_LANG` environment variable still works as a startup default, and the last chosen language is stored in `voice_reactor.json`.

## Usage

### Launch & setup

1. Place your idle/talk PNG files anywhere on disk (transparent backgrounds work best).
2. Start the panel with `python3 main.py` (or `python3 -m vox_sprite`). The avatar window spawns immediately and mirrors whatever you configure in the control panel.
3. Add frames and tweak thresholds, then click **Save** (or press `Ctrl+S`) to persist everything to `voice_reactor.json`. The next launch restores those values automatically.

### Panel sections

#### Language

- **Language selector** (top-left) swaps between any translation JSON that ships inside `vox_sprite/translations/`. Selecting a new language rebuilds the UI while keeping your current settings, and the choice is persisted so you only need to set it once.

#### Audio

- **Level meter** shows live microphone energy. Yellow markers indicate each configured talking threshold so you can see when frames will flip.
- **Talk threshold slider/spinbox** control when the default talking sprite should trigger (`0.001–0.5`). Drag the slider for coarse changes, or type exact decimals in the spinbox.

#### Appearance

- **Talking image** path is the fallback PNG that displays whenever the current input crosses the main talk threshold.
- **Talk levels** let you layer extra mouth shapes for louder speech. Each row stores a PNG and the minimum amplitude it should appear at. Use **Add level** to clone the default talk image, **Browse** to swap artwork, tweak thresholds with the spinbox, and **Remove** to delete a row. Rows are automatically sorted from quietest to loudest and feed both the avatar window and level meter markers.
- **Width slider** scales the rendered avatar (`64–1024px`). Moving it reloads the sprites at the new size.
- **Background color + Transparent checkbox** define the avatar window backdrop. Pick a chroma color with the button, or enable transparency to punch the window straight through for OBS.

#### Idle animation

- **Idle frames list** holds all PNGs used when no talk threshold is active. Use **Add** (multi-select supported) to import files, **Remove** to delete highlighted entries, **Up/Down** to change order, and **Clear** to empty the list. The top entry is also saved as the `idle_image`.
- **Random order** toggles shuffling between frames.
- **Interval controls** set the min/max seconds between idle swaps. VoxSprite clamps the values so `min <= max`, and the avatar window updates immediately so you can preview the pacing.

#### Window behavior

- **Keep on top** forces the avatar window to stay above other apps—handy for screen recordings.
- **Allow drag** enables/disables click-drag repositioning (useful if you prefer a locked overlay).
- **Remember position** captures the avatar’s coordinates whenever you move it, then restores them on the next launch.

#### Saving, menu & shortcuts

- **Save button** (or `Ctrl+S`) writes `voice_reactor.json`. A green confirmation briefly appears beside the button.
- **Help > About** shows version info and project links; **Help > Shortcuts** lists every keyboard shortcut. F1 opens About anywhere. `Ctrl+Q` closes the panel, and **Help > Open Config Directory** reveals the folder that holds `voice_reactor.json`.

### Examples

More examples and "how-to" will (or already are) be in [WIKI](https://github.com/403-html/voxsprite/wiki). 

## License

Project is licensed under MIT. More about it here [LICENSE](LICENSE).
