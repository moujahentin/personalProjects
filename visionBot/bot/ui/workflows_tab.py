from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from ..models import Project, WorkflowDef, ActionDef, safe_id, parse_hhmm
from .components import StepEditor, new_default_step

class WorkflowsTab:
    def __init__(self, parent, get_project: Callable[[], Project], on_changed: Callable[[], None]):
        self.parent = parent
        self.get_project = get_project
        self.on_changed = on_changed

        self.frame = ttk.Frame(parent, padding=10)
        self._build()

    def _build(self):
        left = ttk.Frame(self.frame)
        left.pack(side="left", fill="y")

        ttk.Label(left, text="Daily Workflows").pack(anchor="w")
        self.lb = tk.Listbox(left, width=38, height=24, exportselection=False)
        self.lb.pack(fill="y")
        self.lb.bind("<<ListboxSelect>>", lambda e: self._on_select_workflow())

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Add", command=self._add_workflow).pack(side="left")
        ttk.Button(btns, text="Remove", command=self._remove_workflow).pack(side="left", padx=(8, 0))

        right = ttk.LabelFrame(self.frame, text="Workflow Editor", padding=10)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # workflow settings
        self.v_name = tk.StringVar()
        self.v_enabled = tk.BooleanVar(value=True)
        self.v_sched = tk.BooleanVar(value=True)
        self.v_time = tk.StringVar(value="09:00")
        self.v_maxdur = tk.IntVar(value=1800)

        s = ttk.Frame(right); s.pack(fill="x")
        ttk.Label(s, text="Name").grid(row=0, column=0, sticky="w")
        ttk.Entry(s, textvariable=self.v_name, width=28).grid(row=0, column=1, sticky="w", padx=(6, 18))
        ttk.Checkbutton(s, text="Enabled", variable=self.v_enabled).grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(s, text="Scheduled", variable=self.v_sched).grid(row=0, column=3, sticky="w", padx=(10, 0))

        ttk.Label(s, text="Daily time (HH:MM)").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(s, textvariable=self.v_time, width=10).grid(row=1, column=1, sticky="w", padx=(6, 18), pady=(6, 0))
        ttk.Label(s, text="Max duration (s)").grid(row=1, column=2, sticky="w", pady=(6, 0))
        ttk.Entry(s, textvariable=self.v_maxdur, width=10).grid(row=1, column=3, sticky="w", pady=(6, 0))

        ttk.Button(s, text="Apply Workflow Settings", command=self._apply_workflow).grid(row=2, column=0, sticky="w", pady=(10, 0))

        ttk.Separator(right).pack(fill="x", pady=10)

        # steps
        mid = ttk.Frame(right); mid.pack(fill="both", expand=True)
        self.steps_lb = tk.Listbox(mid, height=16, exportselection=False)
        self.steps_lb.pack(side="left", fill="both", expand=True)
        self.steps_lb.bind("<<ListboxSelect>>", lambda e: self._on_select_step())

        sb = ttk.Frame(mid); sb.pack(side="left", fill="y", padx=(10, 0))
        ttk.Button(sb, text="Add Step", command=self._add_step).pack(fill="x")
        ttk.Button(sb, text="Remove", command=self._remove_step).pack(fill="x", pady=(6, 0))
        ttk.Button(sb, text="Move Up", command=lambda: self._move_step(-1)).pack(fill="x", pady=(16, 0))
        ttk.Button(sb, text="Move Down", command=lambda: self._move_step(1)).pack(fill="x", pady=(6, 0))
        ttk.Button(sb, text="Duplicate", command=self._dup_step).pack(fill="x", pady=(16, 0))

        # step editor
        self.step_editor = StepEditor(right, get_templates=lambda: self.get_project().templates, on_apply=self._apply_step_from_editor)
        self.step_editor.pack(fill="x", pady=(10, 0))

    def refresh(self):
        p = self.get_project()
        self.lb.delete(0, tk.END)
        for wf in p.workflows:
            flag = "✅" if wf.enabled else "⬜"
            self.lb.insert(tk.END, f"{flag} {wf.name} @ {wf.daily_time}")
        self.step_editor.refresh_templates()

    def _selected_workflow(self) -> Optional[WorkflowDef]:
        p = self.get_project()
        sel = self.lb.curselection()
        if not sel:
            return None
        i = sel[0]
        if i < 0 or i >= len(p.workflows):
            return None
        return p.workflows[i]

    def _on_select_workflow(self):
        wf = self._selected_workflow()
        if not wf:
            return
        self.v_name.set(wf.name)
        self.v_enabled.set(wf.enabled)
        self.v_sched.set(wf.schedule_enabled)
        self.v_time.set(wf.daily_time)
        self.v_maxdur.set(wf.max_duration_s)
        self._refresh_steps()

    def _add_workflow(self):
        p = self.get_project()
        p.workflows.append(WorkflowDef(id=safe_id("wf"), name="New Daily Workflow", daily_time="09:00"))
        self.refresh()
        self.on_changed()

    def _remove_workflow(self):
        wf = self._selected_workflow()
        if not wf:
            messagebox.showwarning("No selection", "Διάλεξε πρώτα workflow από τη λίστα.")
            return
        if not messagebox.askyesno("Remove", f"Remove workflow '{wf.name}'?"):
            return
        p = self.get_project()
        p.workflows = [x for x in p.workflows if x.id != wf.id]
        self.refresh()
        self.steps_lb.delete(0, tk.END)
        self.on_changed()

    def _apply_workflow(self):
        wf = self._selected_workflow()
        if not wf:
            messagebox.showwarning("No selection", "Διάλεξε πρώτα workflow από τη λίστα.")
            return
        t = self.v_time.get().strip()
        if not parse_hhmm(t):
            messagebox.showerror("Invalid time", "Daily time must be HH:MM (24h)")
            return
        wf.name = self.v_name.get().strip() or wf.name
        wf.enabled = bool(self.v_enabled.get())
        wf.schedule_enabled = bool(self.v_sched.get())
        wf.daily_time = t
        wf.max_duration_s = int(self.v_maxdur.get())
        self.refresh()
        self.on_changed()

    # steps
    def _refresh_steps(self):
        wf = self._selected_workflow()
        self.steps_lb.delete(0, tk.END)
        if not wf:
            return
        for a in wf.steps:
            flag = "✅" if a.enabled else "⬜"
            self.steps_lb.insert(tk.END, f"{flag} {a.type} (on_fail={a.on_fail})")
        self.step_editor.refresh_templates()

    def _selected_step(self) -> Optional[ActionDef]:
        wf = self._selected_workflow()
        if not wf:
            return None
        sel = self.steps_lb.curselection()
        if not sel:
            return None
        i = sel[0]
        if i < 0 or i >= len(wf.steps):
            return None
        return wf.steps[i]

    def _template_name_from_id(self, tid: str) -> str:
        for t in self.get_project().templates:
            if t.id == tid:
                return t.name
        return ""

    def _on_select_step(self):
        a = self._selected_step()
        self.step_editor.refresh_templates()
        self.step_editor.load_step(a, template_name_lookup=self._template_name_from_id)

    def _add_step(self):
        wf = self._selected_workflow()
        if not wf:
            messagebox.showwarning("No selection", "Διάλεξε πρώτα workflow από τη λίστα.")
            return
        wf.steps.append(new_default_step())
        self._refresh_steps()
        self.on_changed()

    def _remove_step(self):
        wf = self._selected_workflow()
        if not wf:
            return
        sel = self.steps_lb.curselection()
        if not sel:
            return
        del wf.steps[sel[0]]
        self._refresh_steps()
        self.on_changed()

    def _move_step(self, delta: int):
        wf = self._selected_workflow()
        if not wf:
            return
        sel = self.steps_lb.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + delta
        if j < 0 or j >= len(wf.steps):
            return
        wf.steps[i], wf.steps[j] = wf.steps[j], wf.steps[i]
        self._refresh_steps()
        self.steps_lb.selection_set(j)
        self.on_changed()

    def _dup_step(self):
        wf = self._selected_workflow()
        a = self._selected_step()
        if not wf or not a:
            return
        wf.steps.append(ActionDef(id=safe_id("act"), enabled=a.enabled, type=a.type, params=dict(a.params),
                                  on_fail=a.on_fail, timeout_s=a.timeout_s, max_retries=a.max_retries))
        self._refresh_steps()
        self.on_changed()

    def _apply_step_from_editor(self, a: ActionDef):
        # called after editor modifies current step
        self._refresh_steps()
        self.on_changed()
