# Vision Helper Bot v2 (Windows / Vision-only)

A Windows desktop automation tool built with Tkinter that uses PNG template matching (OpenCV) and mouse/keyboard control (pyautogui) to detect on-screen elements and trigger configurable actions.

**Why I built it**  
Developed as a technical experiment to explore computer vision–based UI automation, workflow orchestration, and event handling in real-world desktop scenarios.

## 🧠 Features
- Template library (PNG targets + per-template threshold/scale/ROI/offset)
- Daily workflows (scheduled once per day)
- Watchers (modal/non-blocking popups & triggers) with a full step editor (similar to workflows)
- Interrupt arbitration so popups can be handled while a workflow is waiting
- Project persistence via `project.json` with a `templates/` folder

## 🛠️ Tech
- Python
- Tkinter (GUI)
- OpenCV (template matching)
- pyautogui (input automation)

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
