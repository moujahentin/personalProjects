from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Optional, Tuple
from ..models import ActionDef, TemplateDef, safe_id

ACTION_TYPES = ["click_template", "wait_template", "type_text", "press_key", "sleep"]
ON_FAIL_TYPES = ["stop", "skip"]

class StepEditor(ttk.LabelFrame):
    """Reusable step editor panel (same for workflows and watcher handlers)."""

    def __init__(self, master, get_templates: Callable[[], List[TemplateDef]], on_apply: Callable[[ActionDef], None], **kwargs):
        super().__init__(master, text="Step Settings", padding=10, **kwargs)
        self.get_templates = get_templates
        self.on_apply = on_apply
        self._current: Optional[ActionDef] = None

        # vars
        self.v_enabled = tk.BooleanVar(value=True)
        self.v_type = tk.StringVar(value="click_template")
        self.v_template = tk.StringVar(value="")
        self.v_timeout = tk.DoubleVar(value=10.0)
        self.v_retries = tk.IntVar(value=2)
        self.v_onfail = tk.StringVar(value="stop")

        self.v_clicks = tk.IntVar(value=1)
        self.v_postdelay = tk.DoubleVar(value=0.2)
        self.v_text = tk.StringVar(value="")
        self.v_key = tk.StringVar(value="enter")
        self.v_sleep = tk.DoubleVar(value=1.0)

        self._build()

    def _build(self):
        ttk.Checkbutton(self, text="Enabled", variable=self.v_enabled).grid(row=0, column=0, sticky="w")
        ttk.Label(self, text="Type").grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Combobox(self, textvariable=self.v_type, values=ACTION_TYPES, state="readonly", width=16)                .grid(row=0, column=2, sticky="w")

        ttk.Label(self, text="Template").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.cb_template = ttk.Combobox(self, textvariable=self.v_template, values=[], state="readonly", width=28)
        self.cb_template.grid(row=1, column=1, columnspan=2, sticky="w", pady=(8, 0), padx=(6, 0))

        ttk.Label(self, text="Timeout(s)").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(self, textvariable=self.v_timeout, width=10).grid(row=2, column=1, sticky="w", pady=(8, 0), padx=(6, 0))
        ttk.Label(self, text="Retries").grid(row=2, column=2, sticky="w", pady=(8, 0), padx=(10, 0))
        ttk.Entry(self, textvariable=self.v_retries, width=6).grid(row=2, column=3, sticky="w", pady=(8, 0))

        ttk.Label(self, text="On fail").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(self, textvariable=self.v_onfail, values=ON_FAIL_TYPES, state="readonly", width=10)                .grid(row=3, column=1, sticky="w", pady=(8, 0), padx=(6, 0))

        ttk.Label(self, text="Clicks").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(self, textvariable=self.v_clicks, width=6).grid(row=4, column=1, sticky="w", pady=(8, 0), padx=(6, 0))
        ttk.Label(self, text="Post-delay(s)").grid(row=4, column=2, sticky="w", pady=(8, 0), padx=(10, 0))
        ttk.Entry(self, textvariable=self.v_postdelay, width=10).grid(row=4, column=3, sticky="w", pady=(8, 0))

        ttk.Label(self, text="Text (type_text)").grid(row=5, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(self, textvariable=self.v_text, width=44).grid(row=5, column=1, columnspan=3, sticky="w", pady=(8, 0), padx=(6, 0))

        ttk.Label(self, text="Key (press_key)").grid(row=6, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(self, textvariable=self.v_key, width=12).grid(row=6, column=1, sticky="w", pady=(8, 0), padx=(6, 0))
        ttk.Label(self, text="Seconds (sleep)").grid(row=6, column=2, sticky="w", pady=(8, 0), padx=(10, 0))
        ttk.Entry(self, textvariable=self.v_sleep, width=10).grid(row=6, column=3, sticky="w", pady=(8, 0))

        ttk.Button(self, text="Apply Step Changes", command=self._apply).grid(row=7, column=0, sticky="w", pady=(10, 0))

    def refresh_templates(self):
        self.cb_template["values"] = [t.name for t in self.get_templates()]

    def load_step(self, a: Optional[ActionDef], template_name_lookup: Callable[[str], str]):
        self._current = a
        if not a:
            return
        self.v_enabled.set(a.enabled)
        self.v_type.set(a.type)
        self.v_timeout.set(float(a.timeout_s))
        self.v_retries.set(int(a.max_retries))
        self.v_onfail.set(a.on_fail)

        if a.type in ("click_template", "wait_template"):
            self.v_template.set(template_name_lookup(a.params.get("template_id", "")))
        else:
            self.v_template.set("")

        self.v_clicks.set(int(a.params.get("clicks", 1)))
        self.v_postdelay.set(float(a.params.get("post_delay", 0.2)))
        self.v_text.set(str(a.params.get("text", "")))
        self.v_key.set(str(a.params.get("key", "enter")))
        self.v_sleep.set(float(a.params.get("seconds", 1.0)))

    def _template_id_from_name(self, name: str) -> str:
        for t in self.get_templates():
            if t.name == name:
                return t.id
        return ""

    def _apply(self):
        if not self._current:
            messagebox.showwarning("No step selected", "Διάλεξε πρώτα ένα step από τη λίστα.")
            return
        a = self._current
        a.enabled = bool(self.v_enabled.get())
        a.type = self.v_type.get()
        a.timeout_s = float(self.v_timeout.get())
        a.max_retries = int(self.v_retries.get())
        a.on_fail = self.v_onfail.get()

        if a.type == "click_template":
            tid = self._template_id_from_name(self.v_template.get())
            a.params = {
                "template_id": tid,
                "click": "left",
                "clicks": int(self.v_clicks.get()),
                "interval": 0.0,
                "post_delay": float(self.v_postdelay.get()),
            }
        elif a.type == "wait_template":
            tid = self._template_id_from_name(self.v_template.get())
            a.params = {"template_id": tid}
        elif a.type == "type_text":
            a.params = {"text": self.v_text.get(), "interval": 0.02}
        elif a.type == "press_key":
            a.params = {"key": self.v_key.get()}
        elif a.type == "sleep":
            a.params = {"seconds": float(self.v_sleep.get())}
        else:
            a.params = dict(a.params)

        self.on_apply(a)

def new_default_step() -> ActionDef:
    return ActionDef(
        id=safe_id("act"),
        enabled=True,
        type="click_template",
        params={"template_id": "", "click": "left", "clicks": 1, "interval": 0.0, "post_delay": 0.2},
        on_fail="stop",
        timeout_s=10.0,
        max_retries=2,
    )
