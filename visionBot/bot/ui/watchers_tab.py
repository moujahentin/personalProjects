from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from ..models import Project, WatcherDef, ActionDef, Rect, safe_id
from .components import StepEditor, new_default_step

class WatchersTab:
    def __init__(self, parent, get_project: Callable[[], Project], on_changed: Callable[[], None]):
        self.parent = parent
        self.get_project = get_project
        self.on_changed = on_changed

        self.frame = ttk.Frame(parent, padding=10)
        self._build()

    def _build(self):
        left = ttk.Frame(self.frame)
        left.pack(side="left", fill="y")

        ttk.Label(left, text="Watchers").pack(anchor="w")
        self.lb = tk.Listbox(left, width=38, height=24, exportselection=False)
        self.lb.pack(fill="y")
        self.lb.bind("<<ListboxSelect>>", lambda e: self._on_select_watcher())

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Add", command=self._add_watcher).pack(side="left")
        ttk.Button(btns, text="Remove", command=self._remove_watcher).pack(side="left", padx=(8, 0))

        right = ttk.LabelFrame(self.frame, text="Watcher Settings", padding=10)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self.v_name = tk.StringVar()
        self.v_enabled = tk.BooleanVar(value=True)
        self.v_type = tk.StringVar(value="modal")
        self.v_template = tk.StringVar(value="")
        self.v_cooldown = tk.DoubleVar(value=10.0)
        self.v_max_attempts = tk.IntVar(value=0)
        self.v_rx = tk.IntVar(value=0)
        self.v_ry = tk.IntVar(value=0)
        self.v_rw = tk.IntVar(value=0)
        self.v_rh = tk.IntVar(value=0)

        g = ttk.Frame(right); g.pack(fill="x")
        ttk.Label(g, text="Name").grid(row=0, column=0, sticky="w")
        ttk.Entry(g, textvariable=self.v_name, width=28).grid(row=0, column=1, sticky="w", padx=(6, 18))
        ttk.Checkbutton(g, text="Enabled", variable=self.v_enabled).grid(row=0, column=2, sticky="w")

        ttk.Label(g, text="Type").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(g, textvariable=self.v_type, values=["modal", "non_blocking"], state="readonly", width=14)                .grid(row=1, column=1, sticky="w", pady=(8, 0), padx=(6, 0))

        ttk.Label(g, text="Template").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.cb_template = ttk.Combobox(g, textvariable=self.v_template, values=[], state="readonly", width=28)
        self.cb_template.grid(row=2, column=1, sticky="w", pady=(8, 0), padx=(6, 0))

        ttk.Label(g, text="Cooldown(s)").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(g, textvariable=self.v_cooldown, width=10).grid(row=3, column=1, sticky="w", pady=(8, 0), padx=(6, 0))
        ttk.Label(g, text="Max attempts (0=∞)").grid(row=3, column=2, sticky="w", pady=(8, 0), padx=(10, 0))
        ttk.Entry(g, textvariable=self.v_max_attempts, width=6).grid(row=3, column=3, sticky="w", pady=(8, 0))

        ttk.Label(g, text="ROI (x,y,w,h) - 0 = FULL SCREEN").grid(row=4, column=0, sticky="w", pady=(10, 4))
        roi = ttk.Frame(g); roi.grid(row=5, column=0, columnspan=4, sticky="w")
        ttk.Entry(roi, textvariable=self.v_rx, width=6).pack(side="left")
        ttk.Entry(roi, textvariable=self.v_ry, width=6).pack(side="left", padx=4)
        ttk.Entry(roi, textvariable=self.v_rw, width=6).pack(side="left", padx=4)
        ttk.Entry(roi, textvariable=self.v_rh, width=6).pack(side="left", padx=4)

        ttk.Button(right, text="Apply Watcher Settings", command=self._apply_watcher).pack(anchor="w", pady=(12, 0))

        ttk.Separator(right).pack(fill="x", pady=10)

        # handler steps editor (same as workflows)
        ttk.Label(right, text="Handler Steps (sequence executed AFTER the detected click).").pack(anchor="w")

        mid = ttk.Frame(right); mid.pack(fill="both", expand=True, pady=(6, 0))
        self.steps_lb = tk.Listbox(mid, height=12, exportselection=False)
        self.steps_lb.pack(side="left", fill="both", expand=True)
        self.steps_lb.bind("<<ListboxSelect>>", lambda e: self._on_select_step())

        sb = ttk.Frame(mid); sb.pack(side="left", fill="y", padx=(10, 0))
        ttk.Button(sb, text="Add Step", command=self._add_step).pack(fill="x")
        ttk.Button(sb, text="Remove", command=self._remove_step).pack(fill="x", pady=(6, 0))
        ttk.Button(sb, text="Move Up", command=lambda: self._move_step(-1)).pack(fill="x", pady=(16, 0))
        ttk.Button(sb, text="Move Down", command=lambda: self._move_step(1)).pack(fill="x", pady=(6, 0))
        ttk.Button(sb, text="Duplicate", command=self._dup_step).pack(fill="x", pady=(16, 0))

        self.step_editor = StepEditor(right, get_templates=lambda: self.get_project().templates, on_apply=self._apply_step_from_editor)
        self.step_editor.pack(fill="x", pady=(10, 0))

    def refresh(self):
        p = self.get_project()
        self.lb.delete(0, tk.END)
        for w in p.watchers:
            flag = "✅" if w.enabled else "⬜"
            self.lb.insert(tk.END, f"{flag} {w.name} ({w.popup_type})")
        self.cb_template["values"] = [t.name for t in p.templates]
        self.step_editor.refresh_templates()

    def _selected_watcher(self) -> Optional[WatcherDef]:
        p = self.get_project()
        sel = self.lb.curselection()
        if not sel:
            return None
        i = sel[0]
        if i < 0 or i >= len(p.watchers):
            return None
        return p.watchers[i]

    def _template_id_from_name(self, name: str) -> str:
        for t in self.get_project().templates:
            if t.name == name:
                return t.id
        return ""

    def _template_name_from_id(self, tid: str) -> str:
        for t in self.get_project().templates:
            if t.id == tid:
                return t.name
        return ""

    def _on_select_watcher(self):
        w = self._selected_watcher()
        if not w:
            return
        self.v_name.set(w.name)
        self.v_enabled.set(w.enabled)
        self.v_type.set(w.popup_type)
        self.v_template.set(self._template_name_from_id(w.template_id))
        self.v_cooldown.set(float(w.cooldown_s))
        self.v_max_attempts.set(int(w.max_attempts))
        self.v_rx.set(w.region.x); self.v_ry.set(w.region.y); self.v_rw.set(w.region.w); self.v_rh.set(w.region.h)

        self._refresh_steps()
        self.step_editor.refresh_templates()

    def _add_watcher(self):
        p = self.get_project()
        p.watchers.append(WatcherDef(id=safe_id("watch"), name="New Watcher", popup_type="modal", cooldown_s=10.0))
        self.refresh()
        self.on_changed()

    def _remove_watcher(self):
        w = self._selected_watcher()
        if not w:
            messagebox.showwarning("No selection", "Διάλεξε πρώτα watcher από τη λίστα.")
            return
        if not messagebox.askyesno("Remove", f"Remove watcher '{w.name}'?"):
            return
        p = self.get_project()
        p.watchers = [x for x in p.watchers if x.id != w.id]
        self.refresh()
        self.steps_lb.delete(0, tk.END)
        self.on_changed()

    def _apply_watcher(self):
        w = self._selected_watcher()
        if not w:
            messagebox.showwarning("No selection", "Διάλεξε πρώτα watcher από τη λίστα.")
            return
        w.name = self.v_name.get().strip() or w.name
        w.enabled = bool(self.v_enabled.get())
        w.popup_type = self.v_type.get()
        tid = self._template_id_from_name(self.v_template.get())
        if tid:
            w.template_id = tid
        w.cooldown_s = float(self.v_cooldown.get())
        w.max_attempts = int(self.v_max_attempts.get())
        w.region = Rect(int(self.v_rx.get()), int(self.v_ry.get()), int(self.v_rw.get()), int(self.v_rh.get()))
        self.refresh()
        self.on_changed()

    # handler steps list
    def _refresh_steps(self):
        w = self._selected_watcher()
        self.steps_lb.delete(0, tk.END)
        if not w:
            return
        for a in w.handler_steps:
            flag = "✅" if a.enabled else "⬜"
            self.steps_lb.insert(tk.END, f"{flag} {a.type} (on_fail={a.on_fail})")

    def _selected_step(self) -> Optional[ActionDef]:
        w = self._selected_watcher()
        if not w:
            return None
        sel = self.steps_lb.curselection()
        if not sel:
            return None
        i = sel[0]
        if i < 0 or i >= len(w.handler_steps):
            return None
        return w.handler_steps[i]

    def _on_select_step(self):
        a = self._selected_step()
        self.step_editor.refresh_templates()
        self.step_editor.load_step(a, template_name_lookup=self._template_name_from_id)

    def _add_step(self):
        w = self._selected_watcher()
        if not w:
            messagebox.showwarning("No selection", "Διάλεξε πρώτα watcher από τη λίστα.")
            return
        w.handler_steps.append(new_default_step())
        self._refresh_steps()
        self.on_changed()

    def _remove_step(self):
        w = self._selected_watcher()
        if not w:
            return
        sel = self.steps_lb.curselection()
        if not sel:
            return
        del w.handler_steps[sel[0]]
        self._refresh_steps()
        self.on_changed()

    def _move_step(self, delta: int):
        w = self._selected_watcher()
        if not w:
            return
        sel = self.steps_lb.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + delta
        if j < 0 or j >= len(w.handler_steps):
            return
        w.handler_steps[i], w.handler_steps[j] = w.handler_steps[j], w.handler_steps[i]
        self._refresh_steps()
        self.steps_lb.selection_set(j)
        self.on_changed()

    def _dup_step(self):
        w = self._selected_watcher()
        a = self._selected_step()
        if not w or not a:
            return
        w.handler_steps.append(ActionDef(id=safe_id("act"), enabled=a.enabled, type=a.type, params=dict(a.params),
                                         on_fail=a.on_fail, timeout_s=a.timeout_s, max_retries=a.max_retries))
        self._refresh_steps()
        self.on_changed()

    def _apply_step_from_editor(self, a: ActionDef):
        self._refresh_steps()
        self.on_changed()
