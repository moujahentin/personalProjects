from __future__ import annotations
import os, time, threading, queue, traceback
from datetime import datetime
from typing import Dict, Any, Optional, List

from .models import Project, WorkflowDef, WatcherDef, ActionDef, EngineEvent, parse_hhmm, today_iso
from .vision import ScreenCapturer, TemplateMatcher, VisionError

try:
    import pyautogui
    pyautogui.FAILSAFE = True
except Exception:
    pyautogui = None

class Engine:
    def __init__(self, project: Project, base_dir: str, event_q: "queue.Queue[EngineEvent]"):
        self.project = project
        self.base_dir = base_dir
        self.templates_dir = os.path.join(base_dir, "templates")
        self.event_q = event_q

        self._stop = threading.Event()
        self._pause = threading.Event()
        self._pause.clear()

        self._engine_thread: Optional[threading.Thread] = None
        self._watcher_thread: Optional[threading.Thread] = None

        self._interrupt_q: "queue.Queue[Dict[str, Any]]" = queue.Queue()

        # IMPORTANT: Re-entrant lock so watcher handler can run steps that also take input lock.
        self._lock_input = threading.RLock()

        mode = project.global_screenshot_mode
        self.capturer = ScreenCapturer(mode=mode)
        self.matcher = TemplateMatcher(self.templates_dir, self.capturer, self._log)

        self._watcher_last_fire: Dict[str, float] = {}
        self._watcher_attempts: Dict[str, int] = {}

    def _emit(self, etype: str, msg: str, **data):
        self.event_q.put(EngineEvent(type=etype, message=msg, data=data))

    def _log(self, msg: str, **data):
        self._emit("LOG", msg, **data)

    def start(self):
        if pyautogui is None:
            raise RuntimeError("Missing pyautogui. Install: pyautogui")
        if self._engine_thread and self._engine_thread.is_alive():
            return
        self._stop.clear()
        self._pause.clear()
        self._engine_thread = threading.Thread(target=self._engine_loop, daemon=True)
        self._watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._engine_thread.start()
        self._watcher_thread.start()
        self._emit("STATUS", "Engine started")

    def stop(self):
        self._stop.set()
        self._pause.clear()
        self._emit("STATUS", "Stopping...")

    def pause(self):
        self._pause.set()
        self._emit("STATUS", "Paused")

    def resume(self):
        self._pause.clear()
        self._emit("STATUS", "Running")

    def is_running(self) -> bool:
        return self._engine_thread is not None and self._engine_thread.is_alive()

    # ---------------- Watchers ----------------
    def _watcher_loop(self):
        self._emit("STATUS", "Watchers started")
        while not self._stop.is_set():
            try:
                if self._pause.is_set():
                    time.sleep(0.15)
                    continue

                poll_ms = max(80, int(self.project.global_poll_ms))
                for w in self.project.watchers:
                    if self._stop.is_set() or self._pause.is_set():
                        break
                    if not w.enabled or not w.template_id:
                        continue

                    now = time.time()
                    last = self._watcher_last_fire.get(w.id, 0.0)
                    if now - last < max(0.0, float(w.cooldown_s)):
                        continue

                    tmpl = self._get_template_by_id(w.template_id)
                    if tmpl is None:
                        continue

                    hit = self.matcher.find_best(tmpl, region_override=w.region if w.region.is_valid() else None)
                    if hit:
                        intr = {
                            "watcher_id": w.id,
                            "popup_type": w.popup_type,
                            "priority": 100 if w.popup_type == "modal" else 10,
                            "hit": hit,
                            "template_id": tmpl.id,
                            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        self._interrupt_q.put(intr)
                        self._watcher_last_fire[w.id] = now
                        self._emit("INTERRUPT", f"Watcher detected: {w.name}", watcher_id=w.id, popup_type=w.popup_type, score=hit["score"])

                time.sleep(poll_ms / 1000.0)
            except Exception as e:
                self._emit("ERROR", f"Watcher error: {e}", trace=traceback.format_exc())
                time.sleep(0.5)

        self._emit("STATUS", "Watchers stopped")

    # ---------------- Scheduler/Runner ----------------
    def _engine_loop(self):
        self._emit("STATUS", "Scheduler/Runner started")
        while not self._stop.is_set():
            try:
                if self._pause.is_set():
                    time.sleep(0.2)
                    continue

                # modal first
                self._handle_interrupts(hard_only=True)

                wf = self._pick_due_workflow()
                if wf is None:
                    # idle: handle non-blocking interrupts too
                    self._handle_interrupts(hard_only=False, budget=1)
                    time.sleep(0.25)
                    continue

                self._run_workflow(wf)

            except Exception as e:
                self._emit("ERROR", f"Engine loop error: {e}", trace=traceback.format_exc())
                time.sleep(0.5)

        self._emit("STATUS", "Scheduler/Runner stopped")

    def _pick_due_workflow(self) -> Optional[WorkflowDef]:
        now = datetime.now()
        for wf in self.project.workflows:
            if not wf.enabled or not wf.schedule_enabled:
                continue
            t = parse_hhmm(wf.daily_time)
            if not t:
                continue
            hh, mm = t
            due_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if now < due_dt:
                continue
            last = self.project.last_run_by_workflow.get(wf.id, "")
            if last == today_iso():
                continue
            return wf
        return None

    def _handle_interrupts(self, hard_only: bool, budget: int = 2):
        processed = 0
        items: List[Dict[str, Any]] = []
        try:
            while True:
                items.append(self._interrupt_q.get_nowait())
        except queue.Empty:
            pass

        if not items:
            return

        items.sort(key=lambda x: x.get("priority", 0), reverse=True)

        keep = []
        for intr in items:
            if self._stop.is_set() or self._pause.is_set():
                keep.append(intr)
                continue
            is_modal = (intr.get("popup_type") == "modal")
            if hard_only and not is_modal:
                keep.append(intr)
                continue
            if (not hard_only) and processed >= budget:
                keep.append(intr)
                continue

            ok = self._run_watcher_handler(intr)
            processed += 1

            if not ok:
                # allow later retries
                pass

        for intr in keep:
            self._interrupt_q.put(intr)

    def _run_watcher_handler(self, intr: Dict[str, Any]) -> bool:
        w = self._get_watcher_by_id(intr["watcher_id"])
        if w is None or not w.enabled:
            return False

        # attempts: 0 or negative => unlimited
        att = self._watcher_attempts.get(w.id, 0) + 1
        self._watcher_attempts[w.id] = att
        limit = int(w.max_attempts)
        if limit > 0 and att > limit:
            self._emit("WARN", f"Watcher '{w.name}' exceeded max attempts; ignoring for session.", watcher_id=w.id)
            return False

        if not self._lock_input.acquire(timeout=2.0):
            return False

        try:
            self._emit("STATUS", f"Handling popup: {w.name}", watcher_id=w.id, popup_type=w.popup_type)

            # Default behavior: first click the detected location (fast + stable)
            hit = intr.get("hit")
            if not hit:
                return False
            cx, cy = hit["center_x"], hit["center_y"]
            ok_first = self._click(cx, cy, click_type="left", clicks=1, interval=0.0)

            # Then run optional handler steps (your sequence)
            if w.handler_steps:
                ok_steps = self._run_steps(w.handler_steps, context={"mode": "watcher", "watcher_id": w.id})
                ok = ok_first and ok_steps
            else:
                ok = ok_first

            # Reset attempts on success (so it can run all day)
            if ok:
                self._watcher_attempts[w.id] = 0

            # Verify best-effort (don't block the world if it stays visible)
            tmpl = self._get_template_by_id(w.template_id)
            if tmpl:
                try:
                    hit2 = self.matcher.find_best(tmpl, region_override=w.region if w.region.is_valid() else None)
                    if hit2 is not None:
                        self._emit("WARN", f"Popup may still be present: {w.name}", watcher_id=w.id)
                except Exception:
                    pass

            self._emit("LOG", f"Popup handled: {w.name} (ok={ok})", watcher_id=w.id)
            return ok

        except Exception as e:
            self._emit("ERROR", f"Watcher handler error: {e}", trace=traceback.format_exc(), watcher_id=w.id)
            return False
        finally:
            self._lock_input.release()

    def _run_workflow(self, wf: WorkflowDef):
        self._emit("STATUS", f"Running daily workflow: {wf.name}", workflow_id=wf.id)
        start = time.time()
        ok = False
        try:
            ok = self._run_steps(wf.steps, context={"mode": "workflow", "workflow_id": wf.id}, max_duration_s=wf.max_duration_s)
        except Exception as e:
            self._emit("ERROR", f"Workflow error: {e}", trace=traceback.format_exc(), workflow_id=wf.id)
            ok = False

        if not ok and wf.recovery_steps:
            self._emit("STATUS", f"Running recovery for: {wf.name}", workflow_id=wf.id)
            try:
                self._run_steps(wf.recovery_steps, context={"mode": "recovery", "workflow_id": wf.id}, max_duration_s=min(300, wf.max_duration_s))
            except Exception as e:
                self._emit("ERROR", f"Recovery error: {e}", trace=traceback.format_exc(), workflow_id=wf.id)

        self.project.last_run_by_workflow[wf.id] = today_iso()
        dur = int(time.time() - start)
        self._emit("STATUS", f"Workflow finished: {wf.name} (ok={ok}, {dur}s)", workflow_id=wf.id, ok=ok, duration_s=dur)

    def _run_steps(self, steps: List[ActionDef], context: Dict[str, Any], max_duration_s: int = 1800) -> bool:
        started = time.time()
        for a in steps:
            if self._stop.is_set():
                return False
            if self._pause.is_set():
                while self._pause.is_set() and not self._stop.is_set():
                    time.sleep(0.2)
                if self._stop.is_set():
                    return False

            # modal interrupts before each step
            self._handle_interrupts(hard_only=True)

            if (time.time() - started) > max_duration_s:
                self._emit("WARN", "Max duration exceeded; stopping steps.", **context)
                return False

            if not a.enabled:
                continue

            self._emit("STEP", f"Step: {a.type}", action_id=a.id, action_type=a.type, **context)
            ok = self._run_action(a)
            if not ok:
                if a.on_fail == "skip":
                    self._emit("WARN", f"Step failed (skip): {a.type}", action_id=a.id, **context)
                    continue
                self._emit("ERROR", f"Step failed (stop): {a.type}", action_id=a.id, **context)
                return False

            # cooperative non-blocking interrupts after step
            self._handle_interrupts(hard_only=False, budget=1)

        return True

    def _run_action(self, a: ActionDef) -> bool:
        t0 = time.time()
        retries = max(0, int(a.max_retries))
        timeout = max(0.1, float(a.timeout_s))

        for attempt in range(retries + 1):
            if self._stop.is_set() or self._pause.is_set():
                return False
            if time.time() - t0 > timeout:
                return False

            try:
                if a.type == "sleep":
                    sec = float(a.params.get("seconds", 1.0))
                    time.sleep(max(0.0, sec))
                    return True

                # IMPORTANT: wait_template does NOT need input lock (so other watchers can click while waiting)
                needs_input = a.type in ("click_template", "type_text", "press_key")
                if needs_input:
                    if not self._lock_input.acquire(timeout=3.0):
                        continue

                try:
                    if a.type == "wait_template":
                        tmpl_id = a.params.get("template_id", "")
                        return self._wait_template(tmpl_id, timeout_s=timeout)

                    if a.type == "click_template":
                        tmpl_id = a.params.get("template_id", "")
                        click_type = a.params.get("click", "left")
                        clicks = int(a.params.get("clicks", 1))
                        interval = float(a.params.get("interval", 0.0))
                        post_delay = float(a.params.get("post_delay", 0.2))
                        ok = self._click_template(tmpl_id, click_type=click_type, clicks=clicks, interval=interval)
                        if ok:
                            time.sleep(max(0.0, post_delay))
                        return ok

                    if a.type == "type_text":
                        text = str(a.params.get("text", ""))
                        interval = float(a.params.get("interval", 0.02))
                        self._type(text, interval=interval)
                        return True

                    if a.type == "press_key":
                        key = str(a.params.get("key", "enter"))
                        self._press_key(key)
                        return True

                    self._emit("WARN", f"Unknown action type: {a.type}", action_id=a.id)
                    return False

                finally:
                    if needs_input:
                        self._lock_input.release()

            except Exception as e:
                self._emit("WARN", f"Action error (attempt {attempt+1}): {e}", action_id=a.id, trace=traceback.format_exc())
                time.sleep(0.2)

        return False

    # ---------------- low level ----------------
    def _get_template_by_id(self, tid: str):
        for t in self.project.templates:
            if t.id == tid:
                return t
        return None

    def _get_watcher_by_id(self, wid: str):
        for w in self.project.watchers:
            if w.id == wid:
                return w
        return None

    def _wait_template(self, template_id: str, timeout_s: float = 10.0) -> bool:
        tmpl = self._get_template_by_id(template_id)
        if tmpl is None:
            return False
        t0 = time.time()
        while time.time() - t0 <= timeout_s:
            if self._stop.is_set() or self._pause.is_set():
                return False

            # While waiting, keep handling other watchers
            self._handle_interrupts(hard_only=True)
            self._handle_interrupts(hard_only=False, budget=1)

            hit = self.matcher.find_best(tmpl)
            if hit:
                self._emit("LOG", f"Wait found template: {tmpl.name} score={hit['score']:.3f}")
                return True
            time.sleep(0.15)
        return False

    def _click_template(self, template_id: str, click_type="left", clicks=1, interval=0.0) -> bool:
        tmpl = self._get_template_by_id(template_id)
        if tmpl is None:
            return False
        hit = self.matcher.find_best(tmpl)
        if not hit:
            self._emit("LOG", f"Template not found: {tmpl.name}")
            return False
        return self._click(hit["center_x"], hit["center_y"], click_type=click_type, clicks=clicks, interval=interval)

    def _click(self, x: int, y: int, click_type="left", clicks=1, interval=0.0) -> bool:
        self._emit("LOG", f"Click ({x},{y}) {click_type} x{clicks}")
        pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=click_type)
        return True

    def _type(self, text: str, interval: float = 0.02):
        self._emit("LOG", f"Type text len={len(text)}")
        pyautogui.write(text, interval=max(0.0, interval))

    def _press_key(self, key: str):
        self._emit("LOG", f"Press key: {key}")
        pyautogui.press(key)
