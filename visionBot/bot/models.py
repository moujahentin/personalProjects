from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, date
import time

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def today_iso() -> str:
    return date.today().isoformat()

def safe_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}"

@dataclass
class Rect:
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    def is_valid(self) -> bool:
        return self.w > 0 and self.h > 0

@dataclass
class TemplateDef:
    id: str
    name: str
    file: str  # relative to templates folder
    threshold: float = 0.85
    scale_min: float = 1.0
    scale_max: float = 1.0
    scale_step: float = 0.05
    region: Rect = field(default_factory=Rect)
    offset_dx: int = 0
    offset_dy: int = 0

@dataclass
class ActionDef:
    id: str
    enabled: bool = True
    type: str = "click_template"
    params: Dict[str, Any] = field(default_factory=dict)
    on_fail: str = "stop"  # stop / skip
    timeout_s: float = 10.0
    max_retries: int = 2

@dataclass
class WorkflowDef:
    id: str
    name: str
    enabled: bool = True
    schedule_enabled: bool = True
    daily_time: str = "09:00"  # HH:MM
    max_duration_s: int = 1800
    steps: List[ActionDef] = field(default_factory=list)
    recovery_steps: List[ActionDef] = field(default_factory=list)

@dataclass
class WatcherDef:
    id: str
    name: str
    enabled: bool = True
    template_id: str = ""
    popup_type: str = "modal"  # modal / non_blocking
    cooldown_s: float = 10.0
    region: Rect = field(default_factory=Rect)
    handler_steps: List[ActionDef] = field(default_factory=list)
    max_attempts: int = 0  # 0 => unlimited

@dataclass
class Project:
    name: str = "bot_project"
    templates: List[TemplateDef] = field(default_factory=list)
    workflows: List[WorkflowDef] = field(default_factory=list)
    watchers: List[WatcherDef] = field(default_factory=list)
    global_poll_ms: int = 350
    global_screenshot_mode: str = "mss"  # mss / pil
    last_run_by_workflow: Dict[str, str] = field(default_factory=dict)

@dataclass
class EngineEvent:
    type: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=now_str)

def parse_hhmm(s: str) -> Optional[Tuple[int, int]]:
    try:
        parts = s.strip().split(":")
        if len(parts) != 2:
            return None
        hh = int(parts[0]); mm = int(parts[1])
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return None
        return hh, mm
    except Exception:
        return None
