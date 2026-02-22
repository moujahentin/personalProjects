from __future__ import annotations
import os
from typing import Any, Dict, Optional
from .models import TemplateDef, Rect

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

try:
    import mss
    HAS_MSS = True
except Exception:
    HAS_MSS = False

try:
    from PIL import ImageGrab
    HAS_PIL = True
except Exception:
    HAS_PIL = False

class VisionError(Exception):
    pass

class ScreenCapturer:
    def __init__(self, mode: str = "mss"):
        self.mode = mode

    def capture(self, region: Optional[Rect] = None):
        if np is None or cv2 is None:
            raise VisionError("NumPy/OpenCV not available. Install opencv-python numpy")

        if region and region.is_valid():
            left, top, width, height = region.x, region.y, region.w, region.h
        else:
            left = top = 0
            width = height = 0

        if self.mode == "mss" and HAS_MSS:
            with mss.mss() as sct:
                mon = sct.monitors[1]  # primary
                if width <= 0 or height <= 0:
                    bbox = {"left": mon["left"], "top": mon["top"], "width": mon["width"], "height": mon["height"]}
                else:
                    bbox = {"left": left, "top": top, "width": width, "height": height}
                img = np.array(sct.grab(bbox))  # BGRA
                bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                return bgr

        if not HAS_PIL:
            raise VisionError("No screen capture backend. Install mss or pillow.")
        if width <= 0 or height <= 0:
            pil_img = ImageGrab.grab()
        else:
            pil_img = ImageGrab.grab(bbox=(left, top, left + width, top + height))
        arr = np.array(pil_img)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return bgr

class TemplateMatcher:
    def __init__(self, templates_dir: str, capturer: ScreenCapturer, logger):
        self.templates_dir = templates_dir
        self.capturer = capturer
        self.logger = logger
        self._cache: Dict[str, Any] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    def _load_template(self, rel_path: str):
        path = os.path.join(self.templates_dir, rel_path)
        if not os.path.isfile(path):
            raise VisionError(f"Template file not found: {path}")
        if rel_path in self._cache:
            return self._cache[rel_path]
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            raise VisionError(f"Failed to read image: {path}")
        self._cache[rel_path] = img
        return img

    def find_best(self, tmpl: TemplateDef, region_override: Optional[Rect] = None) -> Optional[Dict[str, Any]]:
        if cv2 is None or np is None:
            raise VisionError("OpenCV/NumPy missing.")

        region = region_override if (region_override and region_override.is_valid()) else (tmpl.region if tmpl.region.is_valid() else None)

        screen = self.capturer.capture(region)
        template = self._load_template(tmpl.file)

        best = None
        smin, smax, sstep = tmpl.scale_min, tmpl.scale_max, tmpl.scale_step
        if sstep <= 0:
            sstep = 0.05
        if smin <= 0 or smax <= 0:
            smin = smax = 1.0

        scales = []
        if abs(smax - smin) < 1e-6:
            scales = [smin]
        else:
            cur = smin
            while cur <= smax + 1e-9:
                scales.append(cur)
                cur += sstep

        for scale in scales:
            if abs(scale - 1.0) < 1e-6:
                t = template
            else:
                new_w = max(1, int(template.shape[1] * scale))
                new_h = max(1, int(template.shape[0] * scale))
                t = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)

            if t.shape[0] > screen.shape[0] or t.shape[1] > screen.shape[1]:
                continue

            res = cv2.matchTemplate(screen, t, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if best is None or max_val > best["score"]:
                x, y = max_loc
                h, w = t.shape[0], t.shape[1]
                best = {"x": x, "y": y, "w": w, "h": h, "score": float(max_val), "scale": float(scale)}

        if best is None:
            return None
        if best["score"] < tmpl.threshold:
            return None

        rx = region.x if region else 0
        ry = region.y if region else 0
        best["x_full"] = best["x"] + rx
        best["y_full"] = best["y"] + ry
        best["center_x"] = best["x_full"] + best["w"] // 2 + tmpl.offset_dx
        best["center_y"] = best["y_full"] + best["h"] // 2 + tmpl.offset_dy
        best["used_region"] = {"x": rx, "y": ry, "w": region.w, "h": region.h} if region else None
        return best
