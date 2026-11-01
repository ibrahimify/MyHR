"""Edit the raw MyHR demo capture into the README MP4 + GIF.

Input : ``<scratch>/raw.mp4`` and ``<scratch>/marks.json`` written by
        ``scripts/record_readme_demo.py`` (scratch defaults to
        ``%LOCALAPPDATA%/Temp/myhr_demo_rec``; raw files never enter the repo).
Output: ``docs/media/demo/myhr_demo.mp4`` (native capture resolution, H.264
        yuv420p, faststart), ``docs/media/demo/myhr_demo.gif`` (gifski) and
        ``docs/media/demo/myhr_demo.provenance.json``.

Editing rules applied: idle time removed; waits (page loads, the analysis run)
accelerated; important screens held at 1x for about 2-2.6 s; one short
crossfade where the recording jumps from the dashboard to the filtered
employee search (the unfiltered employee list is never used); no overlays,
captions or edited pixels.

Run with any Python 3.10+ (only the standard library is used):
``python scripts/make_readme_demo_media.py``
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO.parent / ".tools"
FFBIN = TOOLS / "ffmpeg" / "ffmpeg-9.0.2-essentials_build" / "bin"
FFMPEG, FFPROBE = FFBIN / "ffmpeg.exe", FFBIN / "ffprobe.exe"
GIFSKI = TOOLS / "gifski" / "win" / "gifski.exe"
SCRATCH = Path(os.environ.get("MYHR_DEMO_SCRATCH", Path(os.environ["LOCALAPPDATA"]) / "Temp" / "myhr_demo_rec"))
OUT_DIR = REPO / "docs" / "media" / "demo"
MP4, GIF, PROV = OUT_DIR / "myhr_demo.mp4", OUT_DIR / "myhr_demo.gif", OUT_DIR / "myhr_demo.provenance.json"

FPS = 30
XFADE = 0.4
GIF_FPS, GIF_WIDTH, GIF_QUALITY = 12, 1440, 85


def segments(m: dict) -> list[dict]:
    """(label, raw start, raw end, speed) built from recorder marks."""
    perf_hold_end = m["perf_ready"] + 2.2
    queue_hold_end = m["run_done"] + 2.0
    evidence_hold_end = m["evidence_ready"] + 2.3
    comparison_hold_end = m["comparison_ready"] + 2.6
    eval_top_end = m["evaluation_ready"] + 0.8
    run_start = m["run_click"] + 0.3
    run_out = 1.5  # seconds of output for the whole analysis run
    seg = [
        ("Dashboard after login (login not recorded)", m["dash_ready"], m["dash_ready"] + 1.4, 1.0),
        ("Employees: search 'Peter Ahmed' filtered, open profile", m["search_filtered"], m["perf_click"], 1.6),
        ("Peter Ahmed: Performance tab (hold)", m["perf_click"], perf_hold_end, 1.0),
        ("Sidebar -> Anomaly Review, click Run analysis", perf_hold_end, run_start, 3.0),
        ("Analysis running (accelerated)", run_start, m["run_done"], (m["run_done"] - run_start) / run_out),
        ("Review Queue (hold)", m["run_done"], queue_hold_end, 1.0),
        ("Select row, open Employee Evidence, scroll to policy calculation", queue_hold_end, m["evidence_ready"], 2.0),
        ("Employee Evidence: policy calculation (hold)", m["evidence_ready"], evidence_hold_end, 1.0),
        ("Open Method Comparison, scroll to charts and exact table", evidence_hold_end, m["comparison_ready"], 2.0),
        ("Method Comparison: charts + exact values (hold)", m["comparison_ready"], comparison_hold_end, 1.0),
        ("Open Synthetic Evaluation", comparison_hold_end, m["evaluation_ready"], 2.0),
        ("Synthetic Evaluation: summary (hold)", m["evaluation_ready"], eval_top_end, 1.0),
        ("Scroll to method outcomes", eval_top_end, m["evaluation_scrolled"], 1.5),
        ("Synthetic Evaluation: outcome tables (hold)", m["evaluation_scrolled"], m["evaluation_scrolled"] + 2.2, 1.0),
    ]
    out = []
    for label, a, b, s in seg:
        out.append({"label": label, "raw_start_s": round(a, 3), "raw_end_s": round(b, 3), "speed": round(s, 3),
                    "out_duration_s": round((b - a) / s, 3)})
    return out


def run(cmd, **kw):
    print(">", " ".join(str(c) for c in cmd[:6]), "...", flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def probe_duration(path: Path) -> float:
    r = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def version(cmd) -> str:
    try:
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr).strip().splitlines()[0]
    except Exception as exc:  # pragma: no cover - informational only
        return f"unknown ({exc})"


def main():
    raw = SCRATCH / "raw.mp4"
    meta = json.loads((SCRATCH / "marks.json").read_text(encoding="utf-8"))
    m = meta["marks"]
    segs = segments(m)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ MP4
    parts, labels = [], []
    for i, s in enumerate(segs):
        parts.append(
            f"[0:v]trim=start={s['raw_start_s']}:end={s['raw_end_s']},setpts=(PTS-STARTPTS)/{s['speed']},"
            f"fps={FPS},settb=1/{FPS},format=yuv420p[v{i}]"
        )
        labels.append(f"[v{i}]")
    rest = "".join(labels[1:])
    parts.append(f"{rest}concat=n={len(labels) - 1}:v=1:a=0,settb=1/{FPS}[rest]")
    offset = segs[0]["out_duration_s"] - XFADE
    parts.append(f"[v0][rest]xfade=transition=fade:duration={XFADE}:offset={offset:.3f},format=yuv420p[out]")
    graph = ";".join(parts)
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", raw, "-filter_complex", graph, "-map", "[out]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-r", str(FPS), MP4])

    # ---------------------------------------------------------------- times
    t = 0.0
    for i, s in enumerate(segs):
        if i == 1:
            t -= XFADE  # crossfade overlap
        s["out_start_s"] = round(t, 3)
        t += s["out_duration_s"]
        s["out_end_s"] = round(t, 3)
    s0 = segs[0]
    s0["transition_after"] = f"crossfade {XFADE}s (cut over the unfiltered employee list and the typing)"

    # ------------------------------------------------------------------ GIF
    frames = SCRATCH / "gif_frames"
    if frames.exists():
        shutil.rmtree(frames)
    frames.mkdir()
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", MP4, "-vf",
         f"fps={GIF_FPS},scale={GIF_WIDTH}:-2:flags=lanczos", str(frames / "f%04d.png")])
    pngs = sorted(frames.glob("f*.png"))
    run([GIFSKI, "--fps", str(GIF_FPS), "--quality", str(GIF_QUALITY), "--width", str(GIF_WIDTH), "-o", GIF, *pngs])

    # ------------------------------------------------------------ provenance
    rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "src", "main.py"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    media_py = TOOLS / "media-venv" / "Scripts" / "python.exe"
    w = subprocess.run([str(FFPROBE), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,codec_name,pix_fmt",
                        "-of", "json", str(MP4)], capture_output=True, text=True).stdout
    stream = json.loads(w)["streams"][0]
    gif_dims = None
    with open(GIF, "rb") as f:
        head = f.read(10)
        gif_dims = {"width": int.from_bytes(head[6:8], "little"), "height": int.from_bytes(head[8:10], "little")}
    prov = {
        "artifact": "MyHR README demo (real desktop application, real window, real mouse/keyboard input)",
        "files": {
            "mp4": {"path": "docs/media/demo/myhr_demo.mp4", "bytes": MP4.stat().st_size, "sha256": sha256(MP4),
                    "duration_s": round(probe_duration(MP4), 3), "width": stream["width"], "height": stream["height"],
                    "codec": stream["codec_name"], "pix_fmt": stream["pix_fmt"], "fps": FPS, "faststart": True, "crf": 20},
            "gif": {"path": "docs/media/demo/myhr_demo.gif", "bytes": GIF.stat().st_size, "sha256": sha256(GIF),
                    "duration_s": round(len(pngs) / GIF_FPS, 3), **gif_dims, "fps": GIF_FPS,
                    "gifski_quality": GIF_QUALITY, "frames": len(pngs)},
        },
        "source": {"git_branch": branch, "git_revision": rev,
                   "app_source_dirty_at_edit_time": bool(dirty),
                   "app_command": meta.get("app_command"),
                   "capture_date_local": meta.get("capture_date_local"),
                   "edit_date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "capture": {**meta.get("capture", {}), "display": "1920x1080 physical, 125% scaling; capture = MyHR client area below title bar",
                    "raw_duration_s": round(probe_duration(raw), 3), "raw_kept_outside_repo": str(raw),
                    "recorder_warnings": meta.get("warnings", [])},
        "tools": {
            "ffmpeg": version([FFMPEG, "-version"]),
            "gifski": version([GIFSKI, "--version"]),
            "recorder_python": version([media_py, "--version"]),
            "pyautogui": version([media_py, "-c", "import pyautogui;print(pyautogui.__version__)"]),
            "mss": version([media_py, "-c", "import importlib.metadata as m;print(m.version('mss'))"]),
            "app_python": version(["python", "--version"]) if shutil.which("python") else "see app_command",
            "scripts": ["scripts/record_readme_demo.py", "scripts/make_readme_demo_media.py"],
        },
        "segments": segs,
        "recorder_marks_s": m,
        "statements": {
            "data": "Only synthetic data is shown: the seeded demo company employee EMP-0034 'Peter Ahmed' "
                    "(scripts/seed_demo_company.py) and the anomaly page's synthetic 'Stable administration' "
                    "development scenario. The unfiltered employee list was not used in the edited output.",
            "credentials": "Credentials are not visible: login was performed before screen capture started, so "
                           "neither the username nor the password field was ever recorded. The sidebar user card "
                           "shows the account's display name and role label, not a credential field.",
            "authenticity": "No overlays, captions or pixel edits; only cuts, one crossfade and playback-speed changes.",
            "research_scope": "Development scenario demo only; not holdout evidence. Anomaly scores support human "
                              "review and never change personnel records.",
        },
    }
    PROV.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(json.dumps({k: {kk: v[kk] for kk in ("bytes", "duration_s", "width", "height")} for k, v in prov["files"].items()}, indent=2))


if __name__ == "__main__":
    for tool in (FFMPEG, FFPROBE, GIFSKI):
        if not tool.exists():
            sys.exit(f"missing tool: {tool}")
    main()
