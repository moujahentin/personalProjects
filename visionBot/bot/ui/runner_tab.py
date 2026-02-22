from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable

class RunnerTab:
    def __init__(self, parent, on_start: Callable[[], None], on_pause: Callable[[], None], on_resume: Callable[[], None], on_stop: Callable[[], None]):
        self.frame = ttk.Frame(parent, padding=10)
        top = ttk.Frame(self.frame); top.pack(fill="x")
        ttk.Button(top, text="Start Engine", command=on_start).pack(side="left")
        ttk.Button(top, text="Pause", command=on_pause).pack(side="left", padx=(8, 0))
        ttk.Button(top, text="Resume", command=on_resume).pack(side="left", padx=(8, 0))
        ttk.Button(top, text="Stop (ESC)", command=on_stop).pack(side="left", padx=(8, 0))

        ttk.Separator(self.frame).pack(fill="x", pady=8)

        self.log_text = tk.Text(self.frame, height=28, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        ttk.Label(self.frame, text="Tip: pyautogui FAILSAFE = move mouse to top-left corner to abort.").pack(anchor="w", pady=(8, 0))

    def append_log(self, line: str):
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
