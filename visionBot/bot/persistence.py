from __future__ import annotations
import os, json
from dataclasses import asdict
from typing import Any, Dict
from .models import Project, TemplateDef, WorkflowDef, WatcherDef, ActionDef, Rect, safe_id

def ensure_project_dir(base_dir: str) -> None:
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(os.path.join(base_dir, "templates"), exist_ok=True)

def project_to_dict(p: Project) -> Dict[str, Any]:
    return {
        "name": p.name,
        "global_poll_ms": p.global_poll_ms,
        "global_screenshot_mode": p.global_screenshot_mode,
        "last_run_by_workflow": p.last_run_by_workflow,
        "templates": [asdict(t) for t in p.templates],
        "workflows": [{
            "id": wf.id,
            "name": wf.name,
            "enabled": wf.enabled,
            "schedule_enabled": wf.schedule_enabled,
            "daily_time": wf.daily_time,
            "max_duration_s": wf.max_duration_s,
            "steps": [asdict(a) for a in wf.steps],
            "recovery_steps": [asdict(a) for a in wf.recovery_steps],
        } for wf in p.workflows],
        "watchers": [{
            "id": w.id,
            "name": w.name,
            "enabled": w.enabled,
            "template_id": w.template_id,
            "popup_type": w.popup_type,
            "cooldown_s": w.cooldown_s,
            "region": asdict(w.region),
            "handler_steps": [asdict(a) for a in w.handler_steps],
            "max_attempts": w.max_attempts,
        } for w in p.watchers],
    }

def dict_to_project(d: Dict[str, Any]) -> Project:
    p = Project()
    p.name = d.get("name", "bot_project")
    p.global_poll_ms = int(d.get("global_poll_ms", 350))
    p.global_screenshot_mode = d.get("global_screenshot_mode", "mss")
    p.last_run_by_workflow = d.get("last_run_by_workflow", {}) or {}

    p.templates = []
    for td in d.get("templates", []):
        r = td.get("region") or {}
        p.templates.append(TemplateDef(
            id=td["id"],
            name=td.get("name", td["id"]),
            file=td.get("file", ""),
            threshold=float(td.get("threshold", 0.85)),
            scale_min=float(td.get("scale_min", 1.0)),
            scale_max=float(td.get("scale_max", 1.0)),
            scale_step=float(td.get("scale_step", 0.05)),
            region=Rect(int(r.get("x", 0)), int(r.get("y", 0)), int(r.get("w", 0)), int(r.get("h", 0))),
            offset_dx=int(td.get("offset_dx", 0)),
            offset_dy=int(td.get("offset_dy", 0)),
        ))

    p.workflows = []
    for wfd in d.get("workflows", []):
        p.workflows.append(WorkflowDef(
            id=wfd["id"],
            name=wfd.get("name", wfd["id"]),
            enabled=bool(wfd.get("enabled", True)),
            schedule_enabled=bool(wfd.get("schedule_enabled", True)),
            daily_time=wfd.get("daily_time", "09:00"),
            max_duration_s=int(wfd.get("max_duration_s", 1800)),
            steps=[ActionDef(**ad) for ad in wfd.get("steps", [])],
            recovery_steps=[ActionDef(**ad) for ad in wfd.get("recovery_steps", [])],
        ))

    p.watchers = []
    for wd in d.get("watchers", []):
        r = wd.get("region") or {}
        p.watchers.append(WatcherDef(
            id=wd["id"],
            name=wd.get("name", wd["id"]),
            enabled=bool(wd.get("enabled", True)),
            template_id=wd.get("template_id", ""),
            popup_type=wd.get("popup_type", "modal"),
            cooldown_s=float(wd.get("cooldown_s", 10.0)),
            region=Rect(int(r.get("x", 0)), int(r.get("y", 0)), int(r.get("w", 0)), int(r.get("h", 0))),
            handler_steps=[ActionDef(**ad) for ad in wd.get("handler_steps", [])],
            max_attempts=int(wd.get("max_attempts", 0)),
        ))

    return p

def load_project(base_dir: str) -> Project:
    ensure_project_dir(base_dir)
    path = os.path.join(base_dir, "project.json")
    if not os.path.isfile(path):
        p = Project(name=os.path.basename(base_dir))
        wf = WorkflowDef(id=safe_id("wf"), name="Daily Job", daily_time="09:00")
        wf.steps.append(ActionDef(
            id=safe_id("act"),
            enabled=True,
            type="click_template",
            params={"template_id": "", "click": "left", "clicks": 1, "interval": 0.0, "post_delay": 0.2},
            on_fail="stop",
            timeout_s=10.0,
            max_retries=2,
        ))
        p.workflows.append(wf)
        save_project(base_dir, p)
        return p

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return dict_to_project(data)

def save_project(base_dir: str, p: Project) -> None:
    ensure_project_dir(base_dir)
    path = os.path.join(base_dir, "project.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(project_to_dict(p), f, ensure_ascii=False, indent=2)
