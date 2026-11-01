"""Record the README demo of the real MyHR desktop application.

What it does
------------
1. Launches the app exactly as a user would: ``python main.py`` from the
   repository root (the repository interpreter, miniconda base). The process
   is started detached from any console so the anomaly worker does not borrow
   a terminal; QT_QPA_PLATFORM is not set, so the app renders on the real
   display.
2. Logs in with the local demo account. The login happens BEFORE screen
   capture starts, so the username and password are never recorded.
3. Starts FFmpeg ``gdigrab`` on the MyHR client area (window title bar and
   desktop excluded) with the real mouse cursor drawn.
4. Drives the real window with PyAutoGUI (real mouse moves, clicks, typing,
   wheel scrolling): Dashboard -> Employees -> search "Peter Ahmed"
   (synthetic seed employee EMP-0034) -> profile -> Performance tab ->
   Anomaly Review -> Run analysis -> Review Queue -> select row -> Employee
   Evidence (policy calculation) -> Method Comparison -> Synthetic Evaluation.
5. Writes ``raw.mp4`` and ``marks.json`` (event timestamps relative to the
   capture start) to the scratch directory, then closes the app.

The editing step (speed ramps, cuts, GIF) is in
``scripts/make_readme_demo_media.py`` and consumes ``marks.json``.

Requirements / assumptions
--------------------------
* Windows, 1920x1080 physical display at 125 % scaling, MyHR maximised on the
  primary monitor (client area 1860x1050 below the title bar when a 60 px
  right-hand taskbar is present). Coordinates below are physical pixels
  measured from screenshots of that layout; the script aborts if the window
  geometry differs.
* Run with the media venv that has PyAutoGUI + mss (NOT the repo interpreter):
  ``<Project Lab>/.tools/media-venv/Scripts/python.exe scripts/record_readme_demo.py``
* Do not touch mouse or keyboard while it runs (about 70 s). Foreign mouse
  movement is detected and logged in ``marks.json``.

Privacy: the database's employee list contains a non-seed record on the first
page, so the unfiltered list is recorded only in the raw scratch file; the
editing script starts the Employees segment after the search has filtered the
table to the single synthetic seed result.
"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

ctypes.windll.shcore.SetProcessDpiAwareness(2)  # physical pixel coordinates

import mss  # noqa: E402
import pyautogui  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO.parent / ".tools"
FFMPEG = TOOLS / "ffmpeg" / "ffmpeg-9.0.2-essentials_build" / "bin" / "ffmpeg.exe"
SCRATCH = Path(os.environ.get("MYHR_DEMO_SCRATCH", Path(os.environ["LOCALAPPDATA"]) / "Temp" / "myhr_demo_rec"))
REPO_PYTHON = os.environ.get("MYHR_REPO_PYTHON", str(Path.home() / "miniconda3" / "python.exe"))
DEMO_USER = os.environ.get("MYHR_DEMO_USER", "admin")
DEMO_PASSWORD = os.environ.get("MYHR_DEMO_PASSWORD", "admin123")  # local synthetic demo account

# Capture region: MyHR client area below the title bar (physical px).
CAP_X, CAP_Y, CAP_W, CAP_H = 0, 30, 1860, 1050
FPS = 30

# Physical-pixel coordinates of widgets in the maximised window.
P = {
    "login_user": (930, 601),
    "login_pass": (930, 708),
    "nav_employees": (112, 289),
    "nav_anomaly": (134, 644),
    "emp_search": (715, 268),
    "emp_row1_view": (1704, 505),
    "tab_performance": (603, 372),
    "run_analysis": (1706, 277),
    "queue_row2": (1000, 917),
    "evidence_button": (1703, 1054),
    "tab_queue": (441, 568),
    "tab_evidence": (614, 568),
    "tab_comparison": (811, 568),
    "tab_evaluation": (1012, 568),
    "scroll_anchor": (1100, 700),
}

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0
user32 = ctypes.windll.user32


class Recorder:
    def __init__(self):
        self.t0 = None
        self.marks: dict[str, float] = {}
        self.warnings: list[str] = []
        self.last_pos = None
        self.grab = mss.MSS() if hasattr(mss, "MSS") else mss.mss()

    # ---------------------------------------------------------------- utils
    def mark(self, name: str):
        self.marks[name] = round(time.perf_counter() - self.t0, 3) if self.t0 else 0.0
        print(f"  mark {name:28s} {self.marks[name]:7.2f}s", flush=True)

    def warn(self, msg: str):
        stamp = f"{time.perf_counter() - self.t0:.2f}s" if self.t0 else "pre"
        self.warnings.append(f"{stamp}: {msg}")
        print("  WARNING", msg, flush=True)

    @staticmethod
    def windows(prefix: str):
        found = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cb(h, _l):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(h, buf, 256)
            if buf.value.startswith(prefix) and user32.IsWindowVisible(h):
                found.append((h, buf.value))
            return True

        user32.EnumWindows(cb, 0)
        return found

    def wait_window(self, title: str, exact: bool, timeout: float = 60.0):
        end = time.time() + timeout
        while time.time() < end:
            for h, t in self.windows("MyHR."):
                if (t == title) if exact else t.startswith(title):
                    return h
            time.sleep(0.2)
        raise RuntimeError(f"window {title!r} did not appear")

    def focus(self, h):
        if user32.GetForegroundWindow() == h:
            return
        pyautogui.press("alt")  # allows SetForegroundWindow from this process
        user32.ShowWindow(h, 3)  # SW_MAXIMIZE
        user32.SetWindowPos(h, -1, 0, 0, 0, 0, 0x0003)  # HWND_TOPMOST, no move/size
        user32.SetForegroundWindow(h)
        time.sleep(0.4)

    def check_geometry(self, h):
        r = wintypes.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        if (sw, sh) != (1920, 1080) or r.right - r.left < 1860 or r.bottom - r.top < 1080:
            raise RuntimeError(f"unexpected geometry screen={sw}x{sh} window={r.left},{r.top},{r.right},{r.bottom}")

    def ensure_focus(self):
        if user32.GetForegroundWindow() != self.main:
            self.warn("MyHR lost foreground; refocusing")
            self.focus(self.main)

    def move(self, key_or_xy, duration=0.45):
        x, y = P[key_or_xy] if isinstance(key_or_xy, str) else key_or_xy
        if self.last_pos is not None:
            cur = pyautogui.position()
            if abs(cur[0] - self.last_pos[0]) > 3 or abs(cur[1] - self.last_pos[1]) > 3:
                self.warn(f"foreign mouse movement detected at {tuple(cur)}")
        self.ensure_focus()
        pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)
        self.last_pos = (x, y)

    def click(self, key_or_xy, duration=0.45):
        self.move(key_or_xy, duration)
        time.sleep(0.08)
        pyautogui.click()

    def scroll(self, notches: int, gap=0.05):
        self.move("scroll_anchor", 0.25)
        step = -120 if notches < 0 else 120
        for _ in range(abs(notches)):
            pyautogui.scroll(step)
            time.sleep(gap)

    def pixel(self, x, y):
        img = self.grab.grab({"left": x, "top": y, "width": 1, "height": 1})
        b, g, r = img.raw[0], img.raw[1], img.raw[2]
        return r, g, b

    def region_uniform(self, left, top, width, height, tol=6):
        img = self.grab.grab({"left": left, "top": top, "width": width, "height": height})
        raw = img.raw
        first = raw[0:3]
        for i in range(0, len(raw), 4 * 7):
            px = raw[i:i + 3]
            if any(abs(px[k] - first[k]) > tol for k in range(3)):
                return False
        return True

    def wait_until(self, pred, timeout: float, label: str, poll=0.05):
        end = time.time() + timeout
        while time.time() < end:
            if pred():
                return True
            time.sleep(poll)
        self.warn(f"timeout waiting for {label}")
        return False

    def hide_worker_console(self, before: set, app_pid: int, seconds=10.0):
        """The multiprocessing worker of the detached app opens its own console
        window; minimise any new non-MyHR top-level window as soon as it shows
        (do not close it: that would kill the analysis worker)."""
        end = time.time() + seconds
        first = True
        while first or time.time() < end:
            first = False
            hits = []
            for h, t in self._all_visible():
                if h in before:
                    continue
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                r = wintypes.RECT()
                user32.GetWindowRect(h, ctypes.byref(r))
                if pid.value == app_pid or (r.right - r.left) < 300 or (r.bottom - r.top) < 200:
                    continue
                hits.append((h, t))
            for h, t in hits:
                user32.ShowWindow(h, 6)  # SW_MINIMIZE
                print("  minimised", repr(t), flush=True)
            if hits:
                self.warn("a new window opened during the run and was minimised: "
                          + ", ".join(repr(t) for _h, t in hits))
                time.sleep(0.15)
                self.focus(self.main)
                before |= {h for h, _t in hits}
            time.sleep(0.02)

    @staticmethod
    def _all_visible():
        out = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cb(h, _l):
            if user32.IsWindowVisible(h):
                buf = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(h, buf, 256)
                out.append((h, buf.value))
            return True

        user32.EnumWindows(cb, 0)
        return out

    # ------------------------------------------------------------- workflow
    def run(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        if self.windows("MyHR. - ") or [w for w in self.windows("MyHR.") if w[1] == "MyHR."]:
            raise RuntimeError("a MyHR window is already open; close it first")

        print("launching app", flush=True)
        app_log = open(SCRATCH / "app_stderr.log", "w", encoding="utf-8")
        # Render on the real display: drop any inherited headless Qt platform
        # (some shells used for offscreen test runs export QT_QPA_PLATFORM).
        env = {k: v for k, v in os.environ.items() if k.upper() != "QT_QPA_PLATFORM"}
        app = subprocess.Popen(
            [REPO_PYTHON, "main.py"], cwd=REPO, env=env,
            # A console without a window (like a terminal kept off-screen): the
            # multiprocessing analysis worker inherits it instead of opening a
            # new terminal window over the app.
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdin=subprocess.DEVNULL, stdout=app_log, stderr=subprocess.STDOUT,
        )
        ff = None
        try:
            login = self.wait_window("MyHR.", exact=True)
            time.sleep(1.5)
            self.focus(login)
            # --- login: NOT recorded (capture starts after the dashboard) ---
            pyautogui.click(*P["login_user"]); time.sleep(0.3)
            pyautogui.write(DEMO_USER, interval=0.04)
            pyautogui.click(*P["login_pass"]); time.sleep(0.3)
            pyautogui.write(DEMO_PASSWORD, interval=0.04)
            pyautogui.press("enter")
            self.main = self.wait_window("MyHR. - ", exact=False)
            time.sleep(1.0)
            self.focus(self.main)
            self.check_geometry(self.main)
            pyautogui.moveTo(1200, 650)
            self.last_pos = (1200, 650)
            time.sleep(2.5)  # dashboard charts finish rendering

            raw = SCRATCH / "raw.mp4"
            ff = subprocess.Popen(
                [str(FFMPEG), "-hide_banner", "-y", "-f", "gdigrab", "-framerate", str(FPS),
                 "-offset_x", str(CAP_X), "-offset_y", str(CAP_Y),
                 "-video_size", f"{CAP_W}x{CAP_H}", "-draw_mouse", "1", "-i", "desktop",
                 "-c:v", "libx264", "-preset", "ultrafast", "-crf", "14", "-pix_fmt", "yuv420p", str(raw)],
                stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
            )
            # t0 = moment ffmpeg starts grabbing (first progress line appears right after)
            for line in ff.stderr:
                if line.lstrip().startswith("Press [q]") or "frame=" in line:
                    break
            self.t0 = time.perf_counter()
            # drain stderr in background so ffmpeg never blocks
            import threading
            threading.Thread(target=lambda: [None for _ in ff.stderr], daemon=True).start()
            self.mark("rec_start")
            time.sleep(0.6)
            self.mark("dash_ready")
            time.sleep(1.6)

            # --- Employees and search ---
            self.click("nav_employees")
            self.mark("employees_click")
            time.sleep(1.5)
            # the list page shows a skeleton first; wait for the real table
            def list_loaded():
                return (not self.region_uniform(370, 85, 420, 45)          # page title
                        and not self.region_uniform(380, 480, 1400, 50)    # row 1
                        and not self.region_uniform(380, 560, 1400, 50))   # row 2

            self.wait_until(list_loaded, 30, "employee list")
            time.sleep(1.0)
            self.mark("employees_loaded")
            self.click("emp_search", 0.35)
            time.sleep(0.3)
            for ch in "Peter Ahmed":
                pyautogui.write(ch)
                time.sleep(0.15)

            def filtered():
                return (not self.region_uniform(380, 480, 1400, 50)
                        and self.region_uniform(380, 560, 1400, 50))

            # filtered = exactly one result row (row 2 area blank), stable for 1 s
            for _ in range(3):
                self.wait_until(filtered, 30, "search filter")
                time.sleep(1.0)
                if filtered():
                    break
            self.mark("search_filtered")
            time.sleep(0.5)
            self.click("emp_row1_view", 0.6)
            self.mark("eye_click")
            time.sleep(1.6)
            self.click("tab_performance", 0.55)
            self.mark("perf_click")
            time.sleep(1.0)
            self.mark("perf_ready")
            time.sleep(3.0)

            # --- Anomaly Review ---
            self.click("nav_anomaly", 0.6)
            self.mark("anomaly_click")
            time.sleep(2.5)
            self.mark("anomaly_loaded")
            before = {h for h, _t in self._all_visible()}
            self.click("run_analysis", 0.6)
            self.mark("run_click")
            self.hide_worker_console(before, app.pid, seconds=4.0)

            def export_enabled():
                self.hide_worker_console(before, app.pid, seconds=0)  # keep guarding
                r, g, b = self.pixel(1450, 80)
                return r < 60 and g < 90 and b < 80

            self.wait_until(export_enabled, 90, "analysis completion", poll=0.1)
            time.sleep(0.5)
            self.mark("run_done")
            pyautogui.moveTo(1000, 760, duration=0.3)
            self.last_pos = (1000, 760)
            time.sleep(2.8)
            self.mark("queue_hold_end")

            # --- Employee Evidence ---
            self.click("queue_row2", 0.5)
            self.mark("row_click")
            time.sleep(0.7)
            self.click("evidence_button", 0.5)
            self.mark("evidence_click")
            time.sleep(1.0)
            self.scroll(-5, 0.07)
            time.sleep(0.7)
            self.mark("evidence_ready")
            time.sleep(3.0)

            # --- Method Comparison ---
            self.scroll(10, 0.02)
            time.sleep(0.5)
            self.click("tab_comparison", 0.45)
            self.mark("comparison_click")
            time.sleep(1.0)
            self.scroll(-3, 0.08)
            time.sleep(0.7)
            self.mark("comparison_ready")
            time.sleep(3.4)

            # --- Synthetic Evaluation ---
            self.scroll(10, 0.02)
            time.sleep(0.5)
            self.click("tab_evaluation", 0.45)
            self.mark("evaluation_click")
            time.sleep(1.0)
            self.mark("evaluation_ready")
            time.sleep(1.4)
            self.scroll(-3, 0.08)
            time.sleep(0.7)
            self.mark("evaluation_scrolled")
            time.sleep(3.0)
            self.mark("rec_end")
        finally:
            if ff is not None and ff.poll() is None:
                try:
                    ff.stdin.write("q"); ff.stdin.flush()
                except OSError:
                    pass
                try:
                    ff.wait(30)
                except subprocess.TimeoutExpired:
                    ff.kill()
            subprocess.run(["taskkill", "/PID", str(app.pid), "/T", "/F"], capture_output=True)

        meta = {
            "marks": self.marks,
            "warnings": self.warnings,
            "capture": {"x": CAP_X, "y": CAP_Y, "w": CAP_W, "h": CAP_H, "fps": FPS, "source": "gdigrab desktop region, draw_mouse=1"},
            "capture_date_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "app_command": "python main.py (cwd=repo root; interpreter " + REPO_PYTHON + ")",
            "login_recorded": False,
        }
        (SCRATCH / "marks.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print("wrote", SCRATCH / "raw.mp4", "and marks.json; warnings:", len(self.warnings), flush=True)


if __name__ == "__main__":
    if not FFMPEG.exists():
        sys.exit(f"ffmpeg not found: {FFMPEG}")
    Recorder().run()
