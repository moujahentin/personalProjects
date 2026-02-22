# Vision Helper Bot v2 (Windows / Vision-only)

A Tkinter-based automation helper that uses PNG template matching (OpenCV) and mouse/keyboard control (pyautogui).
It supports:
- Template library (PNG targets + per-template threshold/scale/ROI/offset)
- Daily workflows (scheduled once per day)
- Watchers (modal/non-blocking popups & triggers) with **full step editor** like workflows
- Interrupt arbitration so popups can be handled while a workflow is waiting
- Project saved to `project.json` with a `templates/` folder

## Install (recommended: venv)
```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
python app.py
```

## Project folder
By default a folder `bot_project/` is created next to `app.py`:
- `bot_project/project.json`
- `bot_project/templates/`  (your PNG files)

## Notes
- pyautogui FAILSAFE is enabled: move mouse to top-left corner to abort.
- For stability, Windows display scaling at 100% helps template matching.
