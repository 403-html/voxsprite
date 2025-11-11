# VoxSprite

Lightweight PyQt6 desktop panel for driving voice-reactive PNG avatars. The UI reacts to live microphone input, toggles talking frames based on configurable thresholds, animates idle sequences, and exposes chroma/layer controls for overlays.

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
