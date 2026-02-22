from __future__ import annotations
import os, queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ..models import Project, EngineEvent
from ..persistence import load_project, save_project, ensure_project_dir
from ..engine import Engine

from .templates_tab import TemplatesTab
from .workflows_tab import WorkflowsTab
from .watchers_tab import WatchersTab
from .runner_tab import RunnerTab
from .settings_tab import SettingsTab

APP_TITLE = "Vision Helper Bot v2"
APP_VERSION = "2.0"

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("1180x740")
        self.minsize(1020, 640)

        self.base_dir = os.path.join(os.getcwd(), "bot_project")
        ensure_project_dir(self.base_dir)

        self.event_q: "queue.Queue[EngineEvent]" = queue.Queue()
        self.project: Project = load_project(self.base_dir)
        self.engine = Engine(self.project, self.base_dir, self.event_q)

        self._build_ui()
        self._refresh_all()
        self.after(120, self._poll_events)

        self.bind("<Escape>", lambda e: self._on_stop())

    def _build_ui(self):
        top = ttk.Frame(self, padding=8); top.pack(fill="x")
        ttk.Button(top, text="Load Project…", command=self._on_load_project).pack(side="left")
        ttk.Button(top, text="Save Project", command=self._on_save_project).pack(side="left", padx=(8, 0))
        self.lbl_folder = ttk.Label(top, text=f"Folder: {self.base_dir}")
        self.lbl_folder.pack(side="left", padx=(12, 0))

        ttk.Separator(self).pack(fill="x")

        self.nb = ttk.Notebook(self); self.nb.pack(fill="both", expand=True)

        self.tab_templates = ttk.Frame(self.nb); self.nb.add(self.tab_templates, text="Templates")
        self.tab_workflows = ttk.Frame(self.nb); self.nb.add(self.tab_workflows, text="Daily Workflows")
        self.tab_watchers = ttk.Frame(self.nb); self.nb.add(self.tab_watchers, text="Watchers (Popups/Triggers)")
        self.tab_runner = ttk.Frame(self.nb); self.nb.add(self.tab_runner, text="Runner / Logs")
        self.tab_settings = ttk.Frame(self.nb); self.nb.add(self.tab_settings, text="Settings")

        # Tabs
        self.templates_tab = TemplatesTab(self.tab_templates, get_project=lambda: self.project, on_changed=self._persist, get_engine=lambda: self.engine)
        self.templates_tab.frame.pack(fill="both", expand=True)

        self.workflows_tab = WorkflowsTab(self.tab_workflows, get_project=lambda: self.project, on_changed=self._persist)
        self.workflows_tab.frame.pack(fill="both", expand=True)

        self.watchers_tab = WatchersTab(self.tab_watchers, get_project=lambda: self.project, on_changed=self._persist)
        self.watchers_tab.frame.pack(fill="both", expand=True)

        self.runner_tab = RunnerTab(self.tab_runner, on_start=self._on_start, on_pause=self._on_pause, on_resume=self._on_resume, on_stop=self._on_stop)
        self.runner_tab.frame.pack(fill="both", expand=True)

        self.settings_tab = SettingsTab(self.tab_settings, get_project=lambda: self.project, on_apply=self._apply_settings)
        self.settings_tab.frame.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(8, 4)).pack(fill="x")

    def _refresh_all(self):
        self.templates_tab.refresh()
        self.workflows_tab.refresh()
        self.watchers_tab.refresh()
        self.settings_tab.refresh()

    def _persist(self):
        try:
            save_project(self.base_dir, self.project)
            # Refresh combos/lists across tabs when templates change
            self.workflows_tab.refresh()
            self.watchers_tab.refresh()
            self.status_var.set("Saved project.")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def _on_save_project(self):
        self._persist()

    def _on_load_project(self):
        folder = filedialog.askdirectory(title="Select project folder")
        if not folder:
            return
        self.base_dir = folder
        ensure_project_dir(self.base_dir)
        self.project = load_project(self.base_dir)
        self.engine.stop()
        self.engine = Engine(self.project, self.base_dir, self.event_q)
        self.lbl_folder.configure(text=f"Folder: {self.base_dir}")
        self._refresh_all()
        self.status_var.set(f"Loaded: {folder}")

    # Engine control
    def _on_start(self):
        try:
            self.engine.project = self.project
            self.engine.start()
            self.status_var.set("Engine started.")
        except Exception as e:
            messagebox.showerror("Start failed", str(e))

    def _on_pause(self):
        self.engine.pause()

    def _on_resume(self):
        self.engine.resume()

    def _on_stop(self):
        self.engine.stop()
        self.status_var.set("Stop requested.")

    def _apply_settings(self):
        was_running = self.engine.is_running()
        if was_running:
            self.engine.stop()
        self.engine = Engine(self.project, self.base_dir, self.event_q)
        self._persist()
        self.status_var.set("Applied global settings (engine recreated).")

    # Events
    def _poll_events(self):
        try:
            while True:
                ev: EngineEvent = self.event_q.get_nowait()
                if ev.type in ("LOG", "WARN", "ERROR", "STATUS", "STEP", "INTERRUPT"):
                    self.runner_tab.append_log(f"[{ev.ts}] {ev.type}: {ev.message}")
                    if ev.type == "STATUS":
                        self.status_var.set(ev.message)
        except queue.Empty:
            pass
        self.after(120, self._poll_events)

def run_app():
    app = MainWindow()
    app.mainloop()
