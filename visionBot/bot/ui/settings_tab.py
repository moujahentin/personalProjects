from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable
from ..models import Project

class SettingsTab:
    def __init__(self, parent, get_project: Callable[[], Project], on_apply: Callable[[], None]):
        self.get_project = get_project
        self.on_apply = on_apply
        self.frame = ttk.Frame(parent, padding=10)

        self.v_poll = tk.IntVar(value=self.get_project().global_poll_ms)
        self.v_mode = tk.StringVar(value=self.get_project().global_screenshot_mode)

        f = ttk.Frame(self.frame); f.pack(anchor="nw", fill="x")

        ttk.Label(f, text="Watcher poll (ms)").grid(row=0, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.v_poll, width=10).grid(row=0, column=1, sticky="w", padx=(8, 0))

        ttk.Label(f, text="Screenshot mode").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(f, textvariable=self.v_mode, values=["mss", "pil"], state="readonly", width=10)                .grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

        ttk.Button(f, text="Apply Settings", command=self._apply).grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Label(self.frame, text="Important (stability): set Windows display scaling to 100% if possible.").pack(anchor="w", pady=(18, 0))

    def refresh(self):
        self.v_poll.set(self.get_project().global_poll_ms)
        self.v_mode.set(self.get_project().global_screenshot_mode)

    def _apply(self):
        p = self.get_project()
        p.global_poll_ms = int(self.v_poll.get())
        p.global_screenshot_mode = self.v_mode.get()
        self.on_apply()
