from __future__ import annotations
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Optional
from ..models import Project, TemplateDef, Rect, safe_id
from ..persistence import ensure_project_dir

class TemplatesTab:
    def __init__(self, parent, get_project: Callable[[], Project], on_changed: Callable[[], None], get_engine):
        self.parent = parent
        self.get_project = get_project
        self.on_changed = on_changed
        self.get_engine = get_engine

        self.frame = ttk.Frame(parent, padding=10)

        self._build()

    def _build(self):
        left = ttk.Frame(self.frame)
        left.pack(side="left", fill="y")

        ttk.Label(left, text="Templates").pack(anchor="w")
        self.lb = tk.Listbox(left, width=38, height=26, exportselection=False)
        self.lb.pack(fill="y")
        self.lb.bind("<<ListboxSelect>>", lambda e: self._on_select())

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Add", command=self._add).pack(side="left")
        ttk.Button(btns, text="Remove", command=self._remove).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Test Find", command=self._test_find).pack(side="left", padx=(8, 0))

        right = ttk.LabelFrame(self.frame, text="Template Settings", padding=10)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self.v_name = tk.StringVar()
        self.v_file = tk.StringVar()
        self.v_thr = tk.DoubleVar()
        self.v_smin = tk.DoubleVar()
        self.v_smax = tk.DoubleVar()
        self.v_sstep = tk.DoubleVar()
        self.v_dx = tk.IntVar()
        self.v_dy = tk.IntVar()
        self.v_rx = tk.IntVar()
        self.v_ry = tk.IntVar()
        self.v_rw = tk.IntVar()
        self.v_rh = tk.IntVar()

        g = ttk.Frame(right)
        g.pack(fill="x")

        def row(label, var, r, w=26):
            ttk.Label(g, text=label).grid(row=r, column=0, sticky="w", pady=4)
            ttk.Entry(g, textvariable=var, width=w).grid(row=r, column=1, sticky="w", pady=4)

        row("Name", self.v_name, 0)
        row("PNG file (in templates/)", self.v_file, 1, w=36)
        row("Threshold (0-1)", self.v_thr, 2)
        row("Scale min", self.v_smin, 3)
        row("Scale max", self.v_smax, 4)
        row("Scale step", self.v_sstep, 5)
        row("Click offset dx", self.v_dx, 6)
        row("Click offset dy", self.v_dy, 7)

        ttk.Label(g, text="ROI (x,y,w,h) - 0 = FULL SCREEN").grid(row=8, column=0, sticky="w", pady=(10, 4))
        roi = ttk.Frame(g); roi.grid(row=9, column=0, columnspan=2, sticky="w")
        ttk.Entry(roi, textvariable=self.v_rx, width=6).pack(side="left")
        ttk.Entry(roi, textvariable=self.v_ry, width=6).pack(side="left", padx=4)
        ttk.Entry(roi, textvariable=self.v_rw, width=6).pack(side="left", padx=4)
        ttk.Entry(roi, textvariable=self.v_rh, width=6).pack(side="left", padx=4)

        ttk.Button(right, text="Apply Changes", command=self._apply).pack(anchor="w", pady=(12, 0))

    def refresh(self):
        p = self.get_project()
        self.lb.delete(0, tk.END)
        for t in p.templates:
            self.lb.insert(tk.END, f"{t.name} (thr={t.threshold:.2f})")

    def _selected(self) -> Optional[TemplateDef]:
        p = self.get_project()
        sel = self.lb.curselection()
        if not sel:
            return None
        i = sel[0]
        if i < 0 or i >= len(p.templates):
            return None
        return p.templates[i]

    def _on_select(self):
        t = self._selected()
        if not t:
            return
        self.v_name.set(t.name)
        self.v_file.set(t.file)
        self.v_thr.set(t.threshold)
        self.v_smin.set(t.scale_min)
        self.v_smax.set(t.scale_max)
        self.v_sstep.set(t.scale_step)
        self.v_dx.set(t.offset_dx)
        self.v_dy.set(t.offset_dy)
        self.v_rx.set(t.region.x); self.v_ry.set(t.region.y); self.v_rw.set(t.region.w); self.v_rh.set(t.region.h)

    def _add(self):
        path = filedialog.askopenfilename(title="Choose PNG template", filetypes=[("PNG", "*.png"), ("All files", "*.*")])
        if not path:
            return
        # copy to templates folder
        engine = self.get_engine()
        base_dir = engine.base_dir
        templates_dir = os.path.join(base_dir, "templates")
        ensure_project_dir(base_dir)
        fname = os.path.basename(path)
        dst = os.path.join(templates_dir, fname)
        if os.path.abspath(path) != os.path.abspath(dst):
            try:
                with open(path, "rb") as fsrc: data = fsrc.read()
                with open(dst, "wb") as fdst: fdst.write(data)
            except Exception as e:
                messagebox.showerror("Copy failed", str(e)); return

        p = self.get_project()
        p.templates.append(TemplateDef(id=safe_id("tmpl"), name=os.path.splitext(fname)[0], file=fname))
        engine.matcher.clear_cache()
        self.refresh()
        self.on_changed()

    def _remove(self):
        t = self._selected()
        if not t:
            return
        if not messagebox.askyesno("Remove", f"Remove template '{t.name}' from project? (PNG file stays)"):
            return
        p = self.get_project()
        p.templates = [x for x in p.templates if x.id != t.id]
        self.refresh()
        self.on_changed()

    def _apply(self):
        t = self._selected()
        if not t:
            messagebox.showwarning("No selection", "Διάλεξε πρώτα template από τη λίστα.")
            return
        t.name = self.v_name.get().strip() or t.name
        t.file = self.v_file.get().strip() or t.file
        t.threshold = float(self.v_thr.get())
        t.scale_min = float(self.v_smin.get())
        t.scale_max = float(self.v_smax.get())
        t.scale_step = float(self.v_sstep.get())
        t.offset_dx = int(self.v_dx.get())
        t.offset_dy = int(self.v_dy.get())
        t.region = Rect(int(self.v_rx.get()), int(self.v_ry.get()), int(self.v_rw.get()), int(self.v_rh.get()))
        self.get_engine().matcher.clear_cache()
        self.refresh()
        self.on_changed()

    def _test_find(self):
        t = self._selected()
        if not t:
            return
        try:
            hit = self.get_engine().matcher.find_best(t)
            if hit:
                messagebox.showinfo("Found", f"Found '{t.name}' score={hit['score']:.3f} at ({hit['center_x']},{hit['center_y']}) scale={hit['scale']:.2f}")
            else:
                messagebox.showwarning("Not found", f"Did not find '{t.name}'. Try lower threshold or set ROI.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
