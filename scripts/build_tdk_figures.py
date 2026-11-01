"""Build publication figures and booktabs tables for the English TDK paper.

Single reproducible entry point:

    python scripts/build_tdk_figures.py

Every plotted or tabulated number is read from immutable artifacts under
``research_outputs/`` (read-only) or, for the demonstration table only, from the
in-app demonstration export ``demo_counts.json``. Nothing is estimated or typed
in by hand except the paper-reported values used for consistency checks, which
are compared against the artifacts and recorded in the manifest.

Outputs
    docs/figures/<name>.{pdf,svg,png}   (PNG at 300 dpi)
    docs/figures/src/<name>.dot          (Graphviz sources)
    docs/tables/<name>.tex               (booktabs tables)
    docs/figures/FIGURE_MANIFEST.json    (captions, sources, checksums, fonts)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
FIG_DIR = REPO / "docs" / "figures"
SRC_DIR = FIG_DIR / "src"
TAB_DIR = REPO / "docs" / "tables"

DOT_EXE = Path(
    os.environ.get(
        "MYHR_DOT_EXE",
        r"C:\WorkStation\BME\SEM 8\Project Lab\.tools\graphviz\Graphviz-12.2.1-win64\bin\dot.exe",
    )
)
DEFAULT_DEMO_COUNTS = Path(os.environ.get("LOCALAPPDATA", "")) / "Temp" / "myhr_drive" / "demo_counts.json"

DEV_DIR = REPO / "research_outputs" / "independent_development" / "independent_development_4feea4508de1bb05"
HIST_DIR = REPO / "research_outputs" / "independent_development" / "independent_development_e342bd4acf39b06b"
INTER_DIR = REPO / "research_outputs" / "independent_development" / "independent_development_db1a15646d9e76ba"
VAL_DIR = REPO / "research_outputs" / "protocol_v2_verified" / "validation_c5878ca7b927ccd2"
DIAG_DIR = REPO / "research_outputs" / "protocol_dev_30seed" / "development_8f1494e4abf2d268"
PAPER = REPO / "docs" / "TDK_PAPER_DRAFT.md"
ROADMAP = REPO / "docs" / "TDK_AUTONOMOUS_RESEARCH_ROADMAP.md"

# Physical design size. Figures are placed at 6.0 in in an A4 page with 3.5 cm margins.
FIG_WIDTH_IN = 6.0
MIN_FONT_PT = 10.0
BASE_FONT_PT = 10.0
DOT_FONT_PT = 11.0

# Okabe-Ito colour-blind-safe palette (used only where colour carries information).
OI_BLUE = "#0072B2"
OI_ORANGE = "#E69F00"
OI_VERMILLION = "#D55E00"
OI_GREEN = "#009E73"
GREY_DARK = "#4D4D4D"
GREY_MID = "#8C8C8C"
GREY_LIGHT = "#D9D9D9"

PRIMARY_METHOD = "rule_negative_isolation_forest"
PRIMARY_OP = "fixed_review_budget"

# Representation order and labels follow Section 6.7 of the paper draft.
REPRESENTATIONS = [
    # id, table label (paper wording), short plot label, family, is_full_representation
    ("raw_matched", "Raw matched", "Raw matched", "raw", True),
    ("policy_matched", "Policy matched", "Policy matched", "policy", True),
    ("wrong_policy_control", "Wrong-policy control", "Wrong-policy control", "control", True),
    ("shuffled_policy_control", "Shuffled-policy control", "Shuffled-policy control", "control", True),
    # Ablation labels follow the code (protocol_evaluation.feature_representations): each policy
    # ablation keeps the common core plus ONE policy feature, and raw_interval_ablation keeps the
    # core plus the promotion interval only. The paper's "Without ..." wording does not match the code.
    ("policy_deficit_months_ablation", "Core + policy deficit months only", "Policy, deficit months only", "policy", False),
    ("policy_deficit_ratio_ablation", "Core + policy deficit ratio only", "Policy, deficit ratio only", "policy", False),
    ("policy_unexplained_ablation", "Core + unexplained-short-promotion flag only", "Policy, short-promotion flag only", "policy", False),
    ("raw_interval_ablation", "Core + raw promotion interval only", "Raw, interval only", "raw", False),
    ("raw_without_commendation", "Raw without commendation shortcut", "Raw, no commendation count", "raw", False),
]
FAMILY_STYLE = {
    "raw": {"color": "#000000", "marker": "o", "label": "Raw family"},
    "policy": {"color": OI_BLUE, "marker": "s", "label": "Policy-aware family"},
    "control": {"color": OI_VERMILLION, "marker": "^", "label": "Falsification control"},
}

# Values stated in docs/TDK_PAPER_DRAFT.md; used ONLY for consistency checks.
PAPER_RESIDUAL_TABLE = {
    "raw_matched": (96, 36, 60, 72, 9),
    "policy_matched": (96, 39, 57, 69, 6),
    "wrong_policy_control": (96, 39, 57, 69, 6),
    "shuffled_policy_control": (96, 33, 63, 75, 7),
    "policy_deficit_months_ablation": (96, 42, 54, 66, 8),
    "policy_deficit_ratio_ablation": (96, 42, 54, 66, 8),
    "policy_unexplained_ablation": (96, 42, 54, 66, 8),
    "raw_interval_ablation": (96, 42, 54, 66, 9),
    "raw_without_commendation": (96, 40, 56, 68, 9),
}

CHECKS: list[dict] = []
MPL_SIZES: dict[str, tuple[float, float]] = {}
SHA_CACHE: dict[Path, str] = {}


# --------------------------------------------------------------------------- utilities
def sha256(path: Path) -> str:
    path = Path(path)
    if path not in SHA_CACHE:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                digest.update(block)
        SHA_CACHE[path] = digest.hexdigest()
    return SHA_CACHE[path]


def rel(path: Path) -> str:
    path = Path(path).resolve()
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def source(path: Path, columns: list[str], selector: str = "", note: str = "") -> dict:
    entry = {"path": rel(path), "sha256": sha256(path), "columns": columns}
    if selector:
        entry["selector"] = selector
    if note:
        entry["note"] = note
    return entry


def git_info() -> dict:
    def run(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()

    status = run("status", "--porcelain")
    return {
        "revision": run("rev-parse", "HEAD"),
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "worktree_dirty": bool(status),
    }


def check(description: str, paper_value, observed, decimals: int | None, src: str, column: str) -> None:
    if decimals is None:
        ok = paper_value == observed
    else:
        # Paper values are rounded half-up to `decimals`; accept any artifact value that rounds to them.
        ok = abs(float(observed) - float(paper_value)) <= 0.5 * 10 ** (-decimals) + 1e-12
    CHECKS.append(
        {
            "description": description,
            "paper_value": paper_value,
            "artifact_value": observed if decimals is None else round(float(observed), 6),
            "source": src,
            "column": column,
            "status": "match" if ok else "MISMATCH",
        }
    )


def fmt_signed(value: float, digits: int = 4) -> str:
    text = f"{value:+.{digits}f}"
    return text.replace("-", "\u2212")


def latex_escape(text: str) -> str:
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = "".join(repl.get(ch, ch) for ch in text)
    return out.replace("\u2013", "--").replace("\u2014", "---").replace("\u2212", "$-$")


def md_cell_to_latex(cell: str) -> str:
    """Convert the small Markdown subset used in Section 1.6 cells to LaTeX."""
    parts = re.split(r"(`[^`]+`|\*\*[^*]+\*\*)", cell.strip())
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`"):
            out.append(r"\texttt{" + latex_escape(part[1:-1]).replace(r"\_", r"\_\allowbreak{}") + "}")
        elif part.startswith("**") and part.endswith("**"):
            out.append(r"\textbf{" + latex_escape(part[2:-2]) + "}")
        else:
            text = latex_escape(part)
            text = re.sub(r'"([^"]+)"', r"``\1''", text)
            out.append(text)
    return "".join(out)


# --------------------------------------------------------------------------- typography
def configure_matplotlib() -> dict:
    try:
        path = font_manager.findfont(font_manager.FontProperties(family="Times New Roman"), fallback_to_default=False)
        family = "Times New Roman"
    except ValueError:
        path = font_manager.findfont(font_manager.FontProperties(family="DejaVu Serif"))
        family = "DejaVu Serif"
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": [family],
            "font.size": BASE_FONT_PT,
            "axes.titlesize": BASE_FONT_PT,
            "axes.labelsize": BASE_FONT_PT,
            "xtick.labelsize": BASE_FONT_PT,
            "ytick.labelsize": BASE_FONT_PT,
            "legend.fontsize": BASE_FONT_PT,
            "mathtext.fontset": "stix",
            "axes.unicode_minus": True,
            "axes.linewidth": 0.8,
            "axes.edgecolor": "#000000",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "hatch.linewidth": 0.6,
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "path",
            "svg.hashsalt": "myhr-tdk-figures",
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
        }
    )
    return {"family": family, "file": Path(path).name}


def pdf_base_fonts(path: Path) -> list[str]:
    data = path.read_bytes()
    names = {m.decode("latin-1") for m in re.findall(rb"/BaseFont\s*/([A-Za-z0-9+\-_,.]+)", data)}
    return sorted({n.split("+", 1)[-1] for n in names})


def save_matplotlib(fig, name: str) -> list[str]:
    width, height = fig.get_size_inches()
    assert abs(width - FIG_WIDTH_IN) < 1e-6, f"{name}: figure must be designed at {FIG_WIDTH_IN} in"
    MPL_SIZES[name] = (round(float(width), 3), round(float(height), 3))
    for text in fig.findobj(matplotlib.text.Text):
        if text.get_text().strip() and text.get_visible():
            assert text.get_fontsize() >= MIN_FONT_PT - 1e-9, f"{name}: text below {MIN_FONT_PT} pt: {text.get_text()!r}"
    outputs = []
    fig.savefig(FIG_DIR / f"{name}.pdf", metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(FIG_DIR / f"{name}.svg", metadata={"Date": None})
    fig.savefig(FIG_DIR / f"{name}.png", dpi=300, metadata={"Software": None})
    plt.close(fig)
    for ext in ("pdf", "svg", "png"):
        outputs.append(f"docs/figures/{name}.{ext}")
    return outputs


# --------------------------------------------------------------------------- Graphviz
DOT_FONTNAME = "Times-Roman"  # Graphviz/Pango on Windows resolves this alias to Times New Roman.
DOT_COMMON = f"""
  graph [fontname="{DOT_FONTNAME}", fontsize={DOT_FONT_PT:g}, nodesep=0.25, ranksep=0.3, pad=0.05, bgcolor="white", newrank=true];
  node  [fontname="{DOT_FONTNAME}", fontsize={DOT_FONT_PT:g}, shape=box, style="solid", color="#000000", penwidth=0.8, margin="0.08,0.05", height=0.3];
  edge  [fontname="{DOT_FONTNAME}", fontsize={DOT_FONT_PT:g}, color="#000000", penwidth=0.8, arrowsize=0.6];
"""


def dot_architecture() -> str:
    return f"""digraph architecture {{
{DOT_COMMON}
  rankdir=TB;
  records  [label="Administrative records\\n(employee histories, policy versions)"];
  checks   [label="Deterministic checks\\n(invariant contradictions; policy rules)"];
  findings [label="Evidence-rich findings\\n(rule, source events, calculation)"];
  model    [label="Isolation Forest score on matched\\nraw or policy-aware features"];
  topk     [label="Top-k histories within a fixed\\nadditional review budget"];
  queue    [label="Review queue\\n(recommendations only)"];
  records -> checks;
  checks -> findings [label=" finding"];
  checks -> model [label=" no invariant finding"];
  {{rank=same; findings; model;}}
  model -> topk;
  findings -> queue;
  topk -> queue;
  subgraph cluster_human {{
    label="Human-review boundary: scores never trigger automatic\\npersonnel decisions, record edits or record merges";
    labelloc=b; labeljust=c; fontcolor="{OI_VERMILLION}";
    color="{OI_VERMILLION}"; style=dashed; penwidth=1.0; margin=8;
    reviewer [label="Authorized human reviewer\\ninspects rule, evidence, score"];
    action   [label="Any personnel action only via\\nthe audited application workflow"];
    {{rank=same; reviewer; action;}}
    reviewer -> action;
  }}
  queue -> reviewer;
}}
"""


def dot_experiment_flow(split_counts: dict) -> str:
    tr, va, te = split_counts["train"], split_counts["validation"], split_counts["test"]
    return f"""digraph experiment_flow {{
{DOT_COMMON}
  rankdir=TB; nodesep=0.25; ranksep=0.25;
  subgraph cluster_families {{
    label="Scenario families"; labeljust=l;
    color="#000000"; style=solid; penwidth=0.6; margin=6;
    dev    [label="Development\\n(inspectable)"];
    valfam [label="Validation\\n(inspectable)"];
    freeze [label="Protocol freeze\\n(human approval,\\npending)", style=dashed];
    hold   [label="Final holdout\\n(locked; not\\ngenerated or\\naccessed)", color="{OI_VERMILLION}", fontcolor="{OI_VERMILLION}", penwidth=1.4, style="dashed"];
    {{rank=same; dev; valfam; freeze; hold;}}
    dev -> valfam -> freeze;
    freeze -> hold [style=dashed, color="{OI_VERMILLION}"];
  }}
  subgraph cluster_within {{
    label="Within each development scenario\\l(artifact 4feea4508de1bb05; totals over 12 scenarios)\\l"; labeljust=l;
    color="#000000"; style=solid; penwidth=0.6; margin=6;
    fit  [label="Fit models\\ntraining histories\\n(n = {tr})"];
    val  [label="Select thresholds\\nvalidation histories\\n(n = {va})"];
    eval [label="Compute metrics\\ntest histories\\n(n = {te})"];
    {{rank=same; fit; val; eval;}}
    fit -> val -> eval;
  }}
  valfam -> val [style=invis];
}}
"""


def dot_artifact_lifecycle() -> str:
    return f"""digraph artifact_lifecycle {{
{DOT_COMMON}
  rankdir=TB; nodesep=0.3;
  run     [label="Run in a process-owned\\nstaging directory"];
  write   [label="Write configuration, seeds,\\npredictions and metrics"];
  prov    [label="Record Git revision, dirty flag,\\nsource and dependency versions"];
  sums    [label="Write SHA-256 manifest\\nof every file"];
  publish [label="Atomic publish to a\\nwrite-once artifact directory"];
  audit   [label="Independent audit: checksums,\\nconfusion counts, AP, paired statistics"];
  ok      [label="Verified: arithmetic is\\nreproducible", shape=box];
  bad     [label="Failed: artifact preserved,\\ndefect recorded", shape=box];
  run -> write;
  run -> prov;
  {{rank=same; write; prov;}}
  write -> sums;
  prov -> sums;
  sums -> publish -> audit;
  audit -> ok;
  audit -> bad;
  {{rank=same; ok; bad;}}
  limit [shape=plaintext, label="Verification does not establish that the estimand,\\nscenario population or policy assumptions are valid."];
  ok -> limit [style=invis];
  bad -> limit [style=invis];
}}
"""


def render_dot(name: str, dot_text: str) -> tuple[list[str], dict]:
    if not DOT_EXE.exists():
        raise FileNotFoundError(f"Graphviz dot not found at {DOT_EXE}; set MYHR_DOT_EXE")
    src = SRC_DIR / f"{name}.dot"
    src.write_text(dot_text, encoding="utf-8", newline="\n")
    outputs = [f"docs/figures/src/{name}.dot"]
    for fmt, extra in (("pdf", []), ("svg", []), ("png", ["-Gdpi=300"])):
        out = FIG_DIR / f"{name}.{fmt}"
        # SOURCE_DATE_EPOCH makes cairo write a fixed PDF CreationDate (byte-reproducible output).
        env = {**os.environ, "SOURCE_DATE_EPOCH": "0"}
        subprocess.run([str(DOT_EXE), f"-T{fmt}", *extra, "-o", str(out), str(src)], check=True, capture_output=True, env=env)
        outputs.append(f"docs/figures/{name}.{fmt}")
    svg = (FIG_DIR / f"{name}.svg").read_text(encoding="utf-8")
    m = re.search(r'<svg width="([\d.]+)pt" height="([\d.]+)pt"', svg)
    width_in, height_in = float(m.group(1)) / 72.0, float(m.group(2)) / 72.0
    # Placed at FIG_WIDTH_IN, but never enlarged beyond 1.5x natural size in the paper.
    scale = FIG_WIDTH_IN / width_in
    layout = {
        "natural_width_in": round(width_in, 3),
        "natural_height_in": round(height_in, 3),
        "design_font_pt": DOT_FONT_PT,
        "font_pt_if_placed_at_6in_width": round(DOT_FONT_PT * scale, 2),
        "recommended_placed_width_in": round(min(FIG_WIDTH_IN, width_in * 1.0), 2) if width_in < FIG_WIDTH_IN else FIG_WIDTH_IN,
    }
    if DOT_FONT_PT * min(scale, 1.0) < MIN_FONT_PT:
        raise RuntimeError(f"{name}: natural width {width_in:.2f} in would shrink fonts below {MIN_FONT_PT} pt")
    return outputs, layout


# --------------------------------------------------------------------------- data access
def load_dev_rows() -> pd.DataFrame:
    agg = pd.read_csv(DEV_DIR / "aggregate_metrics.csv")
    rows = agg[(agg.method == PRIMARY_METHOD) & (agg.operating_point == PRIMARY_OP)].set_index("representation")
    assert set(r[0] for r in REPRESENTATIONS) <= set(rows.index)
    return rows


def stacked_outcome_axes(axes, labels, tp, fp, fn, alerts_label, positives_label, xlims):
    """Two-panel horizontal stacked bars: alerts = TP + FP and anomalies = TP + FN."""
    y = list(range(len(labels)))[::-1]
    ax_a, ax_p = axes
    style_tp = dict(facecolor=OI_BLUE, edgecolor="#000000", linewidth=0.6)
    style_fp = dict(facecolor=OI_ORANGE, edgecolor="#000000", linewidth=0.6, hatch="///")
    style_fn = dict(facecolor="white", edgecolor="#000000", linewidth=0.6, hatch="..")
    box = dict(boxstyle="square,pad=0.15", facecolor="white", edgecolor="none")
    for yi, a, b, c in zip(y, tp, fp, fn):
        ax_a.barh(yi, a, height=0.66, **style_tp)
        ax_a.barh(yi, b, left=a, height=0.66, **style_fp)
        ax_p.barh(yi, a, height=0.66, **style_tp)
        ax_p.barh(yi, c, left=a, height=0.66, **style_fn)
    ax_a.set_xlim(0, xlims[0])
    ax_p.set_xlim(0, xlims[1])
    fig = ax_a.figure
    fig.canvas.draw()
    for ax in (ax_a, ax_p):
        x0, x1 = ax.get_xlim()
        width_in = ax.get_window_extent().width / fig.dpi
        ax._min_seg = 0.32 * (x1 - x0) / width_in  # data units spanning 0.32 in (room for a 3-digit label)
    for yi, a, b, c in zip(y, tp, fp, fn):
        for ax, start, val, txtcol in ((ax_a, 0, a, "white"), (ax_a, a, b, "black"), (ax_p, 0, a, "white"), (ax_p, a, c, "black")):
            if val <= 0:
                if txtcol == "black":  # make an empty FP/FN segment explicit
                    ax.text(start + 0.01 * ax.get_xlim()[1], yi, "0", ha="left", va="center", color="black")
                continue
            if val >= ax._min_seg:
                ax.text(start + val / 2, yi, f"{val}", ha="center", va="center", color=txtcol, bbox=None if txtcol == "white" else box)
            else:  # segment too narrow: label just outside the bar end
                ax.text(start + val + 0.01 * (ax.get_xlim()[1]), yi, f"{val}", ha="left", va="center", color="black")
    for ax, lab in ((ax_a, alerts_label), (ax_p, positives_label)):
        ax.set_xlabel(lab)
        ax.set_yticks(y)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
    ax_a.set_yticklabels(labels)
    ax_p.tick_params(axis="y", labelleft=False)
    handles = [Patch(**style_tp, label="True positive"), Patch(**style_fp, label="False positive"), Patch(**style_fn, label="False negative (missed)")]
    return handles


# --------------------------------------------------------------------------- figures
def _axes_in(fig, left, bottom, width, height):
    """Add axes positioned in physical inches (keeps fonts at true size)."""
    w, h = fig.get_size_inches()
    return fig.add_axes([left / w, bottom / h, width / w, height / h])


def fig_primary_recall(rows: pd.DataFrame, paired: pd.Series) -> dict:
    fig = plt.figure(figsize=(FIG_WIDTH_IN, 4.9))
    left, width = 2.05, 3.15
    ax = _axes_in(fig, left, 2.05, width, 2.35)
    axd = _axes_in(fig, left, 0.5, width, 0.5)
    n = len(REPRESENTATIONS)
    for i, (rid, _, short, fam, full) in enumerate(REPRESENTATIONS):
        r = rows.loc[rid]
        yi = n - 1 - i
        st = FAMILY_STYLE[fam]
        m, lo, hi = r.recall_mean, r.recall_ci95_low, r.recall_ci95_high
        ax.errorbar(m, yi, xerr=[[m - lo], [hi - m]], fmt=st["marker"], color=st["color"], ecolor=st["color"], elinewidth=1.0, capsize=3, markersize=6,
                    markerfacecolor=st["color"] if full else "white", markeredgewidth=1.0)
        ax.text(1.04, yi, f"{int(r.true_positives_total)}/{int(r.positive_count_total)}", transform=ax.get_yaxis_transform(), ha="left", va="center")
    ax.text(1.04, n - 0.45, "TP/total", transform=ax.get_yaxis_transform(), ha="left", va="bottom")
    ax.set_yticks(range(n)[::-1], [r[2] for r in REPRESENTATIONS])
    ax.set_xlim(0, 0.7)
    ax.set_ylim(-0.6, n - 0.4)
    ax.axhline(n - 4.5, color=GREY_MID, linewidth=0.6, linestyle=":")
    ax.set_xlabel("Scenario-mean residual recall (95% CI; 12 scenarios)")
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    fig.text(0.02 / FIG_WIDTH_IN, 4.47 / 4.9, "(a) Per-representation recall at equal review capacity (96 alerts each)", ha="left", va="bottom")
    handles = [Line2D([], [], linestyle="none", marker=s["marker"], color=s["color"], markersize=6, label=s["label"].replace(" family", "")) for s in FAMILY_STYLE.values()]
    handles.append(Line2D([], [], linestyle="none", marker="o", color=GREY_DARK, markerfacecolor="white", markersize=6, label="Open: ablation"))
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=4, handletextpad=0.3, columnspacing=1.0, borderaxespad=0.15)

    m, lo, hi, p = paired.recall_delta_mean, paired.recall_delta_ci95_low, paired.recall_delta_ci95_high, paired.recall_delta_sign_flip_p
    axd.errorbar(m, 0, xerr=[[m - lo], [hi - m]], fmt="s", color=OI_BLUE, elinewidth=1.0, capsize=3, markersize=6)
    axd.axvline(0, color="#000000", linewidth=0.8, linestyle="--")
    axd.set_yticks([0], ["Policy \u2212 raw"])
    axd.set_ylim(-0.6, 0.6)
    axd.set_xlim(-0.06, 0.16)
    axd.tick_params(axis="y", length=0)
    axd.spines["left"].set_visible(False)
    axd.set_xlabel("Paired recall difference (95% CI; 12 paired scenarios)")
    fig.text(0.02 / FIG_WIDTH_IN, 1.12 / 4.9,
             f"(b) Primary paired comparison: {fmt_signed(m)} [{fmt_signed(lo)}, {fmt_signed(hi)}], sign-flip p = {p:.4f}", ha="left", va="bottom")
    outputs = save_matplotlib(fig, "primary_recall")
    return {
        "outputs": outputs,
        "caption": (
            "Residual recall at equal review capacity in exploratory development artifact 4feea4508de1bb05 "
            "(12 scenarios, 864 eligible test histories, 108 labelled anomalies, 96 alerts per representation). "
            "(a) Scenario-mean recall with stored 95% intervals for every representation, including the wrong-policy "
            "and shuffled-policy controls and single-feature ablations; colour and marker shape both encode the family. "
            "(b) Paired policy-matched minus raw-matched recall difference with the stored 95% bootstrap interval and "
            "sign-flip p-value. The interval crosses zero; no superiority, inferiority or equivalence claim follows."
        ),
        "sources": [
            source(DEV_DIR / "aggregate_metrics.csv", ["representation", "recall_mean", "recall_ci95_low", "recall_ci95_high", "true_positives_total", "positive_count_total"],
                   f"method == '{PRIMARY_METHOD}' and operating_point == '{PRIMARY_OP}'"),
            source(DEV_DIR / "paired_comparisons.csv", ["recall_delta_mean", "recall_delta_ci95_low", "recall_delta_ci95_high", "recall_delta_sign_flip_p"],
                   f"method == '{PRIMARY_METHOD}' and operating_point == '{PRIMARY_OP}'"),
        ],
        "evidence_status": "exploratory development evidence (inspected); not confirmatory",
    }


def fig_residual_outcomes(rows: pd.DataFrame) -> dict:
    fig, axes = plt.subplots(1, 2, figsize=(FIG_WIDTH_IN, 3.75), layout="constrained")
    reps = REPRESENTATIONS
    labels = [r[2] for r in reps]
    tp = [int(rows.loc[r[0]].true_positives_total) for r in reps]
    fp = [int(rows.loc[r[0]].false_positives_total) for r in reps]
    fn = [int(rows.loc[r[0]].false_negatives_total) for r in reps]
    alerts = {int(rows.loc[r[0]].alert_count_total) for r in reps}
    pos = {int(rows.loc[r[0]].positive_count_total) for r in reps}
    assert len(alerts) == 1 and len(pos) == 1
    handles = stacked_outcome_axes(axes, labels, tp, fp, fn, f"Alerts (n = {alerts.pop()} per representation)", f"Labelled anomalies (n = {pos.pop()})", (100, 110))
    fig.legend(handles=handles, loc="outside upper center", ncol=3, handletextpad=0.4, columnspacing=1.2)
    outputs = save_matplotlib(fig, "residual_outcomes")
    return {
        "outputs": outputs,
        "caption": (
            "Pooled residual alert outcomes at equal review capacity in development artifact 4feea4508de1bb05 "
            "(12 scenarios; rule-negative Isolation Forest, fixed review budget). Left: composition of the 96 alerts "
            "(true positives, solid; false positives, hatched). Right: the 108 labelled anomalies split into detected "
            "and missed. Counts are pooled across scenarios and are descriptive; the wrong-policy control selects the "
            "same alerts as the policy-matched representation."
        ),
        "sources": [
            source(DEV_DIR / "aggregate_metrics.csv", ["representation", "alert_count_total", "true_positives_total", "false_positives_total", "false_negatives_total", "positive_count_total"],
                   f"method == '{PRIMARY_METHOD}' and operating_point == '{PRIMARY_OP}'"),
        ],
        "evidence_status": "exploratory development evidence (inspected); not confirmatory",
    }


def fig_validation_counts() -> dict:
    agg = pd.read_csv(VAL_DIR / "aggregate_metrics.csv")
    spec = [
        ("Deterministic policy rules", "deterministic_policy_rules", "true_policy_checks", "rules_fixed"),
        ("Rules + raw Isolation Forest", "policy_rules_plus_isolation_forest", "raw_matched", "rules_first_budget_floor"),
        ("Rules + policy-aware Isolation Forest", "policy_rules_plus_isolation_forest", "policy_matched", "rules_first_budget_floor"),
    ]
    sel = []
    for label, m, r, op in spec:
        row = agg[(agg.method == m) & (agg.representation == r) & (agg.operating_point == op)]
        assert len(row) == 1
        sel.append((label, row.iloc[0]))
    paper = {"Deterministic policy rules": (351, 351, 0, 9), "Rules + raw Isolation Forest": (408, 357, 51, 3), "Rules + policy-aware Isolation Forest": (408, 358, 50, 2)}
    for label, row in sel:
        obs = (int(row.alert_count_total), int(row.true_positives_total), int(row.false_positives_total), int(row.false_negatives_total))
        check(f"Section 6.2 validation table: {label} alerts/TP/FP/FN", list(paper[label]), list(obs), None, rel(VAL_DIR / "aggregate_metrics.csv"), "alert_count_total,true_positives_total,false_positives_total,false_negatives_total")
    pos = {int(r.positive_count_total) for _, r in sel}
    scen = {int(r.scenario_count) for _, r in sel}
    hist = {int(r.evaluation_count_total) for _, r in sel}
    assert len(pos) == 1 and len(scen) == 1 and len(hist) == 1
    check("Section 6.2: validation scenarios / test histories / anomalies", [30, 3600, 360], [scen.copy().pop(), hist.copy().pop(), pos.copy().pop()], None, rel(VAL_DIR / "aggregate_metrics.csv"), "scenario_count,evaluation_count_total,positive_count_total")
    fig, axes = plt.subplots(1, 2, figsize=(FIG_WIDTH_IN, 2.25), layout="constrained")
    labels = ["Policy rules", "Rules + raw IF", "Rules + policy IF"]
    handles = stacked_outcome_axes(
        axes, labels,
        [int(r.true_positives_total) for _, r in sel], [int(r.false_positives_total) for _, r in sel], [int(r.false_negatives_total) for _, r in sel],
        "Alerts (pooled, 30 scenarios)", f"Labelled anomalies (n = {pos.pop()})", (430, 380),
    )
    fig.legend(handles=handles, loc="outside upper center", ncol=3, handletextpad=0.4, columnspacing=1.2)
    outputs = save_matplotlib(fig, "validation_counts")
    return {
        "outputs": outputs,
        "caption": (
            "Protocol-v2 validation alert outcomes (artifact validation_c5878ca7b927ccd2), pooled across 30 scenarios "
            "and 3,600 test histories containing 360 labelled anomalies. IF denotes Isolation Forest in the rules-first "
            "cascade with a 10% capacity floor. The high rules performance is partly a generator interaction and must "
            "not be generalized."
        ),
        "sources": [
            source(VAL_DIR / "aggregate_metrics.csv", ["method", "representation", "operating_point", "alert_count_total", "true_positives_total", "false_positives_total", "false_negatives_total", "positive_count_total"],
                   "(deterministic_policy_rules, true_policy_checks, rules_fixed); (policy_rules_plus_isolation_forest, raw_matched|policy_matched, rules_first_budget_floor)"),
        ],
        "evidence_status": "validation diagnostic (inspected); not confirmatory",
    }


def fig_policy_alerts() -> dict:
    vals = []
    for label, d in (("Historical", HIST_DIR), ("Intermediate", INTER_DIR), ("Repaired", DEV_DIR)):
        agg = pd.read_csv(d / "aggregate_metrics.csv")
        row = agg[(agg.method == "deterministic_policy_rules") & (agg.operating_point == "rules_fixed")]
        assert len(row) == 1
        vals.append((label, d, int(row.iloc[0].rare_legitimate_flagged_total), int(row.iloc[0].rare_legitimate_count_total)))
    for (label, d, k, n), exp in zip(vals, (39, 8, 0)):
        check(f"Section 6.6 policy-rule alerts among rare-legitimate labels: {label}", f"{exp}/72", f"{k}/{n}", None, rel(d / "aggregate_metrics.csv"), "rare_legitimate_flagged_total/rare_legitimate_count_total")
    fig, ax = plt.subplots(figsize=(FIG_WIDTH_IN, 2.9), layout="constrained")
    x = [0, 1, 2]
    ax.bar(0, vals[0][2], width=0.55, color=GREY_MID, edgecolor="#000000", linewidth=0.8)
    ax.bar(1, vals[1][2], width=0.55, color="white", edgecolor=GREY_DARK, linewidth=0.8, hatch="xx", linestyle="--")
    # Repaired value is zero: no bar is drawn, the count is printed at the baseline.
    for xi, (_, _, k, n) in zip(x, vals):
        ax.text(xi, k + 1.0, f"{k}/{n}", ha="center", va="bottom")
    ax.annotate("Interpretation invalidated:\ngenerator produced genuine\ncontradictions", xy=(1.28, 6.5), xytext=(1.42, 22), ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=GREY_DARK, linewidth=0.6))
    ax.set_xticks(x, [
        f"Historical\n{HIST_DIR.name.split('_')[-1][:8]}\nspecification counterexample",
        f"Intermediate\n{INTER_DIR.name.split('_')[-1][:8]}\nINVALIDATED",
        f"Repaired\n{DEV_DIR.name.split('_')[-1][:8]}\nexploratory",
    ])
    ax.tick_params(axis="x", length=0)
    ax.set_xlim(-0.5, 2.5)
    ax.set_ylim(0, 48)
    ax.set_ylabel("Policy-rule alerts among\n72 rare-legitimate labels")
    outputs = save_matplotlib(fig, "policy_alerts")
    return {
        "outputs": outputs,
        "caption": (
            "Audit history of deterministic policy-rule alerts among 72 generated rare-legitimate labels across three "
            "development artifacts. The historical 39/72 is a constructed specification counterexample, not a prevalence "
            "estimate. The intermediate 8/72 is drawn hatched and dashed because its false-positive interpretation was "
            "invalidated by a semantic defect in the generator; it is not a valid measurement. The repaired exploratory "
            "artifact records 0/72; its denominator includes 24 grandfathering labels without independently established "
            "employee entitlement."
        ),
        "sources": [source(d / "aggregate_metrics.csv", ["rare_legitimate_flagged_total", "rare_legitimate_count_total"], "method == 'deterministic_policy_rules' and operating_point == 'rules_fixed'") for _, d, _, _ in vals],
        "evidence_status": "historical (e342bd4a) and invalidated (db1a1564) values shown for audit transparency; repaired value is exploratory development evidence",
    }


def fig_confound_diagnostic() -> dict:
    agg = pd.read_csv(DIAG_DIR / "aggregate_metrics.csv")
    rows = agg[(agg.method == PRIMARY_METHOD) & (agg.operating_point == PRIMARY_OP)].set_index("representation")
    paired = pd.read_csv(DIAG_DIR / "paired_comparisons.csv")
    prow = paired[(paired.method == PRIMARY_METHOD) & (paired.operating_point == PRIMARY_OP)].iloc[0]
    sm = pd.read_csv(DIAG_DIR / "scenario_metrics.csv", usecols=["scenario_id", "method", "representation", "operating_point", "recall"])
    sm = sm[(sm.method == PRIMARY_METHOD) & (sm.operating_point == PRIMARY_OP)]
    wide = sm.pivot_table(index="scenario_id", columns="representation", values="recall")
    deltas = {}
    for a, b in (("policy_matched", "raw_matched"), ("wrong_policy_control", "raw_matched"), ("shuffled_policy_control", "raw_matched"), ("policy_matched", "wrong_policy_control")):
        d = (wide[a] - wide[b]).dropna()
        deltas[(a, b)] = (float(d.mean()), int(len(d)))
    # Consistency of recomputation with the stored paired comparison.
    assert abs(deltas[("policy_matched", "raw_matched")][0] - prow.recall_delta_mean) < 1e-9
    n_scen = int(prow.scenario_count)
    check("Section 6.8: 8f1494 policy-aware minus raw recall", 0.348, prow.recall_delta_mean, 3, rel(DIAG_DIR / "paired_comparisons.csv"), "recall_delta_mean")
    check("Roadmap/coordinator: 8f1494 primary 95% CI low", 0.342, prow.recall_delta_ci95_low, 3, rel(DIAG_DIR / "paired_comparisons.csv"), "recall_delta_ci95_low")
    check("Roadmap/coordinator: 8f1494 primary 95% CI high", 0.355, prow.recall_delta_ci95_high, 3, rel(DIAG_DIR / "paired_comparisons.csv"), "recall_delta_ci95_high")
    check("Section 6.8: 8f1494 wrong-policy minus raw recall", 0.284, deltas[("wrong_policy_control", "raw_matched")][0], 3, rel(DIAG_DIR / "scenario_metrics.csv"), "recall (paired mean, recomputed)")
    check("Coordinator: 8f1494 shuffled minus raw recall", -0.079, deltas[("shuffled_policy_control", "raw_matched")][0], 3, rel(DIAG_DIR / "scenario_metrics.csv"), "recall (paired mean, recomputed)")
    check("Coordinator: 8f1494 correct-policy increment (policy minus wrong-policy)", 0.064, deltas[("policy_matched", "wrong_policy_control")][0], 3, rel(DIAG_DIR / "scenario_metrics.csv"), "recall (paired mean, recomputed)")
    share = deltas[("wrong_policy_control", "raw_matched")][0] / prow.recall_delta_mean
    check("Section 6.8: wrong-policy share of apparent gain (about 82%)", 0.82, share, 2, "derived", "ratio of the two paired means")

    fig = plt.figure(figsize=(FIG_WIDTH_IN, 3.9), layout="constrained")
    gs = fig.add_gridspec(2, 1, height_ratios=[4, 4])
    ax = fig.add_subplot(gs[0])
    axd = fig.add_subplot(gs[1])
    reps = [("raw_matched", "Raw matched", "raw"), ("policy_matched", "Policy matched", "policy"), ("wrong_policy_control", "Wrong-policy control", "control"), ("shuffled_policy_control", "Shuffled-policy control", "control")]
    ci_widths = []
    for i, (rid, lab, fam) in enumerate(reps):
        r = rows.loc[rid]
        st = FAMILY_STYLE[fam]
        yi = len(reps) - 1 - i
        ci_widths.append(float(r.recall_ci95_high - r.recall_ci95_low))
        # Interval drawn first (no caps) so the marker sits cleanly on top of it.
        ax.hlines(yi, r.recall_ci95_low, r.recall_ci95_high, color=st["color"], linewidth=1.0, zorder=2)
        ax.plot(r.recall_mean, yi, linestyle="none", marker=st["marker"], color=st["color"], markersize=6, markeredgecolor="white", markeredgewidth=0.5, zorder=3)
        ax.text(r.recall_ci95_high + 0.015, yi, f"{r.recall_mean:.3f} [{r.recall_ci95_low:.3f}, {r.recall_ci95_high:.3f}]", va="center", ha="left")
    max_ci = max(ci_widths)
    ax.set_yticks(range(len(reps))[::-1], [r[1] for r in reps])
    ax.set_xlim(0.4, 1.3)
    ax.set_xticks([0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax.spines["bottom"].set_bounds(0.4, 1.0)
    ax.set_ylim(-0.6, len(reps) - 0.4)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel(f"Scenario-mean residual recall ({n_scen} scenarios)", x=(0.7 - 0.4) / (1.3 - 0.4))
    ax.set_title(f"(a) Recall [stored 95% CI]; CI lines \u2264 {max_ci:.3f} wide, behind markers", loc="left")

    items = [
        (("policy_matched", "raw_matched"), "Policy \u2212 raw", "policy", True),
        (("wrong_policy_control", "raw_matched"), "Wrong-policy \u2212 raw", "control", False),
        (("shuffled_policy_control", "raw_matched"), "Shuffled \u2212 raw", "control", False),
        (("policy_matched", "wrong_policy_control"), "Policy \u2212 wrong-policy", "policy", False),
    ]
    for i, (key, lab, fam, stored) in enumerate(items):
        st = FAMILY_STYLE[fam]
        yi = len(items) - 1 - i
        mean = deltas[key][0]
        if stored:
            lo, hi = prow.recall_delta_ci95_low, prow.recall_delta_ci95_high
            axd.hlines(yi, lo, hi, color=st["color"], linewidth=1.0, zorder=2)
            axd.plot(mean, yi, linestyle="none", marker=st["marker"], color=st["color"], markersize=6, markeredgewidth=0.0, zorder=3)
            txt = f"{fmt_signed(mean, 3)} [{fmt_signed(lo, 3)}, {fmt_signed(hi, 3)}]"
        else:
            axd.plot(mean, yi, linestyle="none", marker=st["marker"], color=st["color"], markerfacecolor="white", markersize=6, markeredgewidth=1.0)
            txt = f"{fmt_signed(mean, 3)} (no stored CI)"
        axd.text(max(mean, 0) + 0.025, yi, txt, va="center", ha="left")
    axd.axvline(0, color="#000000", linewidth=0.8, linestyle="--")
    axd.set_yticks(range(len(items))[::-1], [it[1] for it in items])
    axd.set_xlim(-0.12, 0.62)
    axd.set_ylim(-0.6, len(items) - 0.4)
    axd.tick_params(axis="y", length=0)
    axd.spines["left"].set_visible(False)
    axd.set_xlabel(f"Paired recall difference ({n_scen} paired scenarios)")
    axd.set_title("(b) Paired differences; open markers: mean only", loc="left")
    outputs = save_matplotlib(fig, "confound_diagnostic")
    return {
        "outputs": outputs,
        "caption": (
            f"Confounded 900-scenario development diagnostic (artifact 8f1494e4abf2d268, 30 conditions x 30 seeds, "
            f"holdout not accessed). (a) Scenario-mean residual recall at the fixed review budget with stored 95% intervals, "
            f"drawn as lines behind the markers and printed numerically; no interval is wider than {max_ci:.3f} recall, so most are "
            f"narrower than or comparable to the marker. "
            f"(b) Paired differences. Only the policy-minus-raw difference has a stored interval; the control differences "
            f"are paired means recomputed from per-scenario recall and have no stored interval. Wrong-policy features "
            f"reproduce about {share:.0%} of the apparent policy gain; the remaining increment is confounded with "
            f"representation dimensionality. The independent offline audit of the 8,019,000 prediction rows is incomplete. "
            f"Not confirmatory evidence."
        ),
        "sources": [
            source(DIAG_DIR / "aggregate_metrics.csv", ["representation", "recall_mean", "recall_ci95_low", "recall_ci95_high"], f"method == '{PRIMARY_METHOD}' and operating_point == '{PRIMARY_OP}'"),
            source(DIAG_DIR / "paired_comparisons.csv", ["recall_delta_mean", "recall_delta_ci95_low", "recall_delta_ci95_high", "scenario_count"], f"method == '{PRIMARY_METHOD}' and operating_point == '{PRIMARY_OP}'"),
            source(DIAG_DIR / "scenario_metrics.csv", ["scenario_id", "representation", "recall"], f"method == '{PRIMARY_METHOD}' and operating_point == '{PRIMARY_OP}'",
                   "Control paired means (wrong-policy, shuffled, policy minus wrong-policy) are computed by this script as the mean of per-scenario differences; the artifact stores no paired interval for them, so none is drawn."),
        ],
        "evidence_status": "development diagnostic; artifact checksums stored, independent offline audit of record-level predictions incomplete (docs/TDK_AUTONOMOUS_RESEARCH_ROADMAP.md); values in this figure come from artifact CSVs, not from audit text",
        "derived_values": {f"{a} minus {b}": {"paired_mean": round(m, 6), "paired_scenarios": k} for (a, b), (m, k) in deltas.items()},
    }


# --------------------------------------------------------------------------- code-described diagrams
FEATURES_PY = REPO / "src" / "services" / "anomaly_detection" / "features.py"
PROTOCOL_PY = REPO / "src" / "services" / "anomaly_detection" / "protocol_evaluation.py"
DUPLICATE_PY = REPO / "src" / "services" / "anomaly_detection" / "duplicate_detection.py"
DETERMINISTIC_PY = REPO / "src" / "services" / "anomaly_detection" / "deterministic_checks.py"
PROMOTION_PY = REPO / "src" / "services" / "promotion_policy.py"
HANDOVER = REPO / "docs" / "RESEARCH_HANDOVER.md"
HIST_COMMIT = "0ad4e962f81d69e87bf7fd4987b8a84d4b545453"  # artifact e342bd4acf39b06b metadata.json
DEV_COMMIT = "56597d3b7119dde8bbd26df4ef303f32d39d3dff"  # artifact 4feea4508de1bb05 metadata.json


def code_source(path: Path, what: str, artifact_dirs: tuple[Path, ...] = ()) -> dict:
    """Source entry for a code file described by a diagram, with the hash recorded by each artifact."""
    entry = source(path, [what], note="Diagram describes this code; sha256 is of the current working-tree file.")
    for d in artifact_dirs:
        meta = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
        entry.setdefault("artifact_recorded_sha256", {})[d.name] = meta["provenance"]["source_sha256"].get(rel(path))
    return entry


def git_blob_source(commit: str, path: Path, what: str, artifact_dir: Path) -> dict:
    blob = subprocess.run(["git", "show", f"{commit}:{rel(path)}"], cwd=REPO, capture_output=True, check=True).stdout
    meta = json.loads((artifact_dir / "metadata.json").read_text(encoding="utf-8"))
    return {
        "path": rel(path),
        "git_revision": commit,
        "git_blob_sha256": hashlib.sha256(blob).hexdigest(),
        "artifact_recorded_sha256": meta["provenance"]["source_sha256"].get(rel(path)),
        "artifact": artifact_dir.name,
        "columns": [what],
        "note": "Historical code read with `git show <revision>:<path>`; the artifact hash may differ from the blob hash by line-ending normalisation.",
    }


def parse_representations(path: Path, commit: str | None = None) -> tuple[dict, list[tuple[str, tuple[str, ...], str]]]:
    """Read the feature-name constants and feature_representations() from protocol_evaluation.py via AST."""
    import ast

    text = path.read_text(encoding="utf-8") if commit is None else subprocess.run(
        ["git", "show", f"{commit}:{rel(path)}"], cwd=REPO, capture_output=True, text=True, check=True, encoding="utf-8").stdout
    tree = ast.parse(text)
    env: dict = {"__builtins__": {"tuple": tuple}}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id.endswith("_FEATURES"):
            env[node.targets[0].id] = eval(compile(ast.Expression(node.value), str(path), "eval"), env)  # noqa: S307 - constant tuples only
    reps = []
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "feature_representations")
    for call in ast.walk(func):
        if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "FeatureRepresentation":
            name = ast.literal_eval(call.args[0])
            feats = eval(compile(ast.Expression(call.args[1]), str(path), "eval"), env)  # noqa: S307
            reps.append((name, tuple(feats), ast.literal_eval(call.args[2])))
    consts = {k: v for k, v in env.items() if k.endswith("_FEATURES")}
    return consts, reps


def _dot_lines(lines: list[str]) -> str:
    """Left-justified Graphviz label from lines; leading spaces become non-breaking indents."""
    out = []
    for ln in lines:
        stripped = ln.lstrip(" ")
        out.append("\u00a0" * (2 * (len(ln) - len(stripped))) + stripped.replace('"', '\\"'))
    return "\\l".join(out) + "\\l"


def _wrap_names(names, width: int = 40, indent: str = "  ") -> list[str]:
    lines, cur = [], ""
    for n in names:
        piece = n if not cur else cur + ", " + n
        if len(piece) > width and cur:
            lines.append(indent + cur + ",")
            cur = n
        else:
            cur = piece
    if cur:
        lines.append(indent + cur)
    return lines


def dot_feature_design(consts: dict, reps: list) -> str:
    core = consts["COMMON_CORE_FEATURES"]
    raw_add = [f for f in consts["RAW_MATCHED_FEATURES"] if f not in core]
    pol_add = [f for f in consts["POLICY_MATCHED_FEATURES"] if f not in core]
    by = {r[0]: r for r in reps}

    def ablation_lines(names):
        out = []
        for n in names:
            feats = by[n][1]
            added = [f for f in feats if f not in core]
            out.append(f"{n} ({len(feats)}): core")
            out += ["  + " + a for a in added]
        return out

    raw_abl = [r[0] for r in reps if r[2] == "raw" and r[0] != "raw_matched"]
    pol_abl = [r[0] for r in reps if r[2] == "true" and r[0] != "policy_matched"]
    assert by["wrong_policy_control"][1] == by["policy_matched"][1] == by["shuffled_policy_control"][1]
    n_pol = len(by["policy_matched"][1])
    return f"""digraph feature_design {{
{DOT_COMMON}
  rankdir=TB; nodesep=0.2; ranksep=0.3;
  node [margin="0.08,0.05"];
  core    [label="{_dot_lines([f"Common core ({len(core)} features, in every representation)"] + _wrap_names(core, 46))}"];
  rawadd  [label="{_dot_lines([f"Raw additions ({len(raw_add)})"] + ["  " + f for f in raw_add])}"];
  poladd  [label="{_dot_lines([f"Policy-aware additions ({len(pol_add)}), from", "assess_promotion_history() under the", "scenario policy and policy epochs"] + ["  " + f for f in pol_add])}", color="{OI_BLUE}", penwidth=1.2];
  {{rank=same; rawadd; poladd;}}
  rawm    [label="raw_matched ({len(by['raw_matched'][1])} features)"];
  polm    [label="policy_matched ({n_pol} features)", color="{OI_BLUE}", penwidth=1.2];
  {{rank=same; rawm; polm;}}
  core -> rawadd [style=invis]; core -> poladd [style=invis];
  core -> rawm; core -> polm;
  rawadd -> rawm; poladd -> polm;
  rawabl  [label="{_dot_lines(["Raw ablations (columns removed)"] + ablation_lines(raw_abl))}", style=dashed];
  polabl  [label="{_dot_lines(["Policy ablations (one policy feature kept)"] + ablation_lines(pol_abl))}", style=dashed, color="{OI_BLUE}"];
  {{rank=same; rawabl; polabl;}}
  rawm -> rawabl [style=dashed];
  polm -> polabl [style=dashed, color="{OI_BLUE}"];
  subgraph cluster_controls {{
    label="Falsification controls: same {n_pol} columns as policy_matched, altered policy input"; labeljust=l; labelloc=t;
    fontcolor="{OI_VERMILLION}"; color="{OI_VERMILLION}"; style=dashed; penwidth=0.8; margin=6;
  wrong   [label="{_dot_lines(["wrong_policy_control", "policy additions computed under the next", "stock policy profile, without policy", "epochs or grandfathering evidence"])}", color="{OI_VERMILLION}", penwidth=1.2];
  shuf    [label="{_dot_lines(["shuffled_policy_control", f"each history takes the {len(pol_add)} policy additions", "of another history (seeded rotation;", "value frequencies preserved)"])}", color="{OI_VERMILLION}", penwidth=1.2];
  {{rank=same; wrong; shuf;}}
  }}
  rawabl -> wrong [style=invis]; polabl -> shuf [style=invis];
}}
"""


def dot_feature_collapse(core_n: int, raw_n: int, pol_n: int, budget: float) -> str:
    return f"""digraph feature_collapse {{
{DOT_COMMON}
  rankdir=TB; nodesep=0.35; ranksep=0.28;
  subgraph cluster_hist {{
    label="Historical residual design\\n(artifact e342bd4acf39b06b, commit {HIST_COMMIT[:7]})"; labeljust=c;
    color="#000000"; style=solid; penwidth=0.6; margin=8;
    h1 [label="Residual filter: keep histories with no\\nfinding from validate_record_with_policy()"];
    h2 [label="A positive policy service deficit always\\nemits a policy finding, so every history\\nwith a positive deficit is removed"];
    h3 [label="The {pol_n} policy-specific features are 0\\nfor every retained history"];
    h4 [label="Policy model varies on {core_n} core features;\\nraw model varies on {core_n} + {raw_n} features"];
    h5 [label="Structural failure: the comparison\\ncannot test the policy hypothesis", color="{OI_VERMILLION}", fontcolor="{OI_VERMILLION}", penwidth=1.4, style=dashed];
    h1 -> h2 -> h3 -> h4 -> h5;
  }}
  subgraph cluster_fix {{
    label="Corrected residual design\\n(artifact 4feea4508de1bb05, commit {DEV_COMMIT[:7]})"; labeljust=c;
    color="#000000"; style=solid; penwidth=0.6; margin=8;
    c1 [label="Primary gate: keep histories with no\\nfinding from validate_invariant_record()\\n(structural contradictions only)"];
    c2 [label="Policy deficits are not used for\\nfiltering, so the {pol_n} policy-specific\\nfeatures can vary"];
    c3 [label="Same invariant-negative histories for\\nevery representation and control"];
    c4 [label="Equal fixed additional review budget:\\n{budget:.0%} of residual test histories,\\nrounded up, for each representation"];
    c5 [label="Policy rules reported separately\\nas a secondary queue"];
    c1 -> c2 -> c3 -> c4 -> c5;
  }}
  {{rank=same; h1; c1;}}
}}
"""


def dot_duplicate_contract() -> str:
    return f"""digraph duplicate_results {{
{DOT_COMMON}
  rankdir=TB; nodesep=0.3; ranksep=0.3;
  recs  [label="Partition-local record set: records of one split;\\nall records of one latent person share a partition"];
  truth [label="True pairs T: every pair inside a\\nduplicate_of_employee_id cluster"];
  block [label="Blocking (similarity method): pairs sharing\\ndate of birth, normalised national ID,\\nnormalised full name or first-name token"];
  univ  [label="Declared pair universe U\\nexact, normalised exact: all n(n \u2212 1)/2 pairs\\nsimilarity: blocked pairs only"];
  score [label="Predicted pairs P\\nexact: equality predicate on the partition\\nsimilarity: score \u2265 threshold chosen on the\\nvalidation split; P outside U is a contract error"];
  conf  [label="Counts from set membership within U\\nTP = |P \u2229 T \u2229 U|,  FP = |P \u2212 T|\\nFN = |(T \u2229 U) \u2212 P|,  TN = |U \u2212 P \u2212 T|"];
  brec  [label="Blocking recall, reported separately\\n|blocked \u2229 T| / |T|; true pairs outside\\nU are blocking misses, not FN in U", style=dashed];
  other [shape=plaintext, group=side, label="Also reported separately:\\lend-to-end counts over all n(n \u2212 1)/2\\lpairs, candidate pair count (workload),\\lblocking and scoring time, peak\\ltraced memory\\l"];
  recs [group=main]; block [group=main]; univ [group=main]; score [group=main]; conf [group=main];
  truth [group=side]; brec [group=side];
  recs -> block [weight=10]; recs -> truth;
  {{rank=same; truth; block;}}
  truth -> brec [style=dashed, weight=10]; block -> brec [style=dashed];
  block -> univ [weight=10];
  {{rank=same; brec; univ;}}
  univ -> score [weight=10];
  score -> conf [weight=10]; truth -> conf;
  brec -> other [style=invis, weight=10];
  {{rank=same; other; score;}}
}}
"""


def _load_promotion_policy():
    import importlib.util

    spec = importlib.util.spec_from_file_location("myhr_promotion_policy", PROMOTION_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def worked_example() -> dict:
    """B, M, C, S from docs/RESEARCH_HANDOVER.md section 5.1, evaluated by the application's pure function."""
    text = HANDOVER.read_text(encoding="utf-8")
    m = re.search(r"Example: if `B=(\d+)`, `M=(\d+)`, `C=(\d+)`, and `S=(\d+)`, then `A=(\d+)`, `R=(\d+)`", text)
    assert m, "worked example not found in docs/RESEARCH_HANDOVER.md section 5.1"
    b, mm, c, s, a_doc, r_doc = map(int, m.groups())
    mod = _load_promotion_policy()
    out = mod.calculate_promotion_race(mod.PromotionRaceInput(has_next_level=True, base_months=b, months_elapsed=mm,
                                                              commendation_credit_months=c, active_sanction_delay_months=s))
    check("RESEARCH_HANDOVER 5.1 worked example: adjusted service A and remaining R", [a_doc, r_doc],
          [out.adjusted_service_months, out.months_remaining], None, rel(PROMOTION_PY), "calculate_promotion_race(B=48, M=45, C=6, S=3)")
    return {"B": b, "M": mm, "C": c, "S": s, "A": out.adjusted_service_months, "R": out.months_remaining, "eligible": out.eligible, "progress_pct": out.progress_pct}


def fig_policy_timeline() -> dict:
    ex = worked_example()
    b, mm, c, s, a, r = ex["B"], ex["M"], ex["C"], ex["S"], ex["A"], ex["R"]
    fig = plt.figure(figsize=(FIG_WIDTH_IN, 2.75))
    ax = _axes_in(fig, 1.75, 0.5, 4.1, 1.8)
    rows_ = [
        (3, 0, mm, dict(facecolor=GREY_LIGHT, edgecolor="#000000"), f"M = {mm}"),
        (2, mm, c, dict(facecolor=OI_BLUE, edgecolor="#000000"), f"+C = +{c}"),
        (1, mm + c - s, s, dict(facecolor="white", edgecolor=OI_VERMILLION, hatch="///"), f"\u2212S = \u2212{s}"),
        (0, 0, a, dict(facecolor="white", edgecolor="#000000"), f"A = {a}"),
    ]
    for yi, left, width, style, lab in rows_:
        ax.barh(yi, width, left=left, height=0.56, linewidth=0.8, **style)
    # waterfall connectors
    for x, y0, y1 in ((mm, 3, 2), (mm + c, 2, 1), (mm + c - s, 1, 0)):
        ax.plot([x, x], [y0 - 0.28, y1 + 0.28], color=GREY_DARK, linewidth=0.6, linestyle=":")
    ax.text(mm / 2, 3, f"M = {mm}", ha="center", va="center")
    ax.text(mm + c + 0.6, 2, f"+C = +{c}", ha="left", va="center")
    ax.text(mm + c + 0.6, 1, f"\u2212S = \u2212{s}", ha="left", va="center")
    ax.text(a / 2, 0, f"A = M + C \u2212 S = {a}", ha="center", va="center")
    ax.axvline(b, color="#000000", linewidth=0.9, linestyle="--", zorder=0)
    ax.text(b, 3.55, f"B = {b}", ha="center", va="bottom")
    ax.set_yticks([3, 2, 1, 0], [
        "Elapsed service to\nthe decision date (M)",
        "Commendation credit (C)",
        "Sanction delay (S)",
        "Adjusted service (A)",
    ])
    ax.set_xlim(0, 60)
    ax.set_xticks([0, 12, 24, 36, 48, 60])
    ax.set_ylim(-0.5, 3.5)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Months since last promotion or recognized start point")
    fig.text(0.05 / FIG_WIDTH_IN, 2.5 / 2.75,
             f"B: base requirement of the policy effective at the decision date; R = max(0, B \u2212 A) = {r}",
             ha="left", va="bottom")
    outputs = save_matplotlib(fig, "policy_timeline")
    return {
        "outputs": outputs,
        "caption": (
            f"Worked promotion-race example from docs/RESEARCH_HANDOVER.md section 5.1 (B = {b}, M = {mm}, C = {c}, S = {s}). "
            f"Elapsed service to the decision date is adjusted by commendation credit and sanction delay, A = M + C \u2212 S = {a}, "
            f"and compared with the base requirement B of the policy effective at the decision date, giving R = {r}: "
            "service-eligible, which is evidence for review, not automatic approval. Calendar dates of the commendation and "
            "sanction events are not part of the documented example and are not shown."
        ),
        "sources": [
            source(HANDOVER, ["section 5.1 worked example B, M, C, S, A, R"], "Example: if `B=48`, `M=45`, `C=6`, and `S=3`"),
            source(PROMOTION_PY, ["calculate_promotion_race()"], note="A and R recomputed by the application's pure function at build time."),
            source(PAPER, ["Section 3.2 (A = M + C - S, R = max(0, B - A))", "Section 3.7 (policy effective at the decision date)"], note="Equations and temporal requirement; no numeric data."),
        ],
        "derived_values": ex,
        "evidence_status": "illustrative worked example; not experimental evidence",
    }


# --------------------------------------------------------------------------- tables
def write_table(name: str, caption: str, label: str, colspec: str, header: list[str], body: list[list[str] | None], extra_preamble: str = "") -> str:
    lines = [
        f"% Generated by scripts/build_tdk_figures.py; do not edit by hand.",
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
    ]
    if extra_preamble:
        lines.append(extra_preamble)
    lines += [f"\\begin{{tabular}}{{{colspec}}}", r"\toprule", " & ".join(header) + r" \\", r"\midrule"]
    for row in body:
        lines.append(r"\addlinespace" if row is None else " & ".join(row) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    path = TAB_DIR / f"{name}.tex"
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return f"docs/tables/{name}.tex"


def table_residual(rows: pd.DataFrame) -> dict:
    body = []
    for i, (rid, label, _, _, _) in enumerate(REPRESENTATIONS):
        r = rows.loc[rid]
        obs = (int(r.alert_count_total), int(r.true_positives_total), int(r.false_positives_total), int(r.false_negatives_total), int(r.rare_legitimate_flagged_total))
        check(f"Section 6.7 residual table: {label} alerts/TP/FP/FN/rare", list(PAPER_RESIDUAL_TABLE[rid]), list(obs), None, rel(DEV_DIR / "aggregate_metrics.csv"), "alert_count_total,true_positives_total,false_positives_total,false_negatives_total,rare_legitimate_flagged_total")
        if i in (2, 4):
            body.append(None)
        body.append([latex_escape(label), *[str(v) for v in obs[:4]], f"{obs[4]}/{int(r.rare_legitimate_count_total)}"])
    out = write_table(
        "residual_equal_budget",
        "Equal-budget residual outcomes in exploratory development artifact \\texttt{4feea4508de1bb05} (12 scenarios, 864 eligible test histories, 108 labelled anomalies, 72 generated rare-legitimate labels). Counts are pooled across scenarios for the rule-negative Isolation Forest at the fixed review budget. The wrong-policy control selected the same alerts as the policy-matched representation.",
        "tab:residual-equal-budget",
        "@{}lrrrrr@{}",
        ["Residual representation", "Alerts", "TP", "FP", "FN", "Rare labels alerted"],
        body,
    )
    return {"outputs": [out], "caption": "Equal-budget residual outcomes (Section 6.7).",
            "sources": [source(DEV_DIR / "aggregate_metrics.csv", ["representation", "alert_count_total", "true_positives_total", "false_positives_total", "false_negatives_total", "rare_legitimate_flagged_total", "rare_legitimate_count_total"], f"method == '{PRIMARY_METHOD}' and operating_point == '{PRIMARY_OP}'")]}


def table_rules() -> dict:
    agg = pd.read_csv(DEV_DIR / "aggregate_metrics.csv")
    spec = [
        ("Structural invariant checks", "deterministic_invariant_rules", "structural_contradictions"),
        ("Policy-agnostic explicit checks", "deterministic_rules", "explicit_checks"),
        ("Policy rules", "deterministic_policy_rules", "true_policy_checks"),
    ]
    body = []
    for label, m, r in spec:
        row = agg[(agg.method == m) & (agg.representation == r) & (agg.operating_point == "rules_fixed")].iloc[0]
        if m == "deterministic_policy_rules":
            check("Section 6.7: policy rules TP/FP/FN, rare flagged", [63, 0, 45, "0/72"], [int(row.true_positives_total), int(row.false_positives_total), int(row.false_negatives_total), f"{int(row.rare_legitimate_flagged_total)}/{int(row.rare_legitimate_count_total)}"], None, rel(DEV_DIR / "aggregate_metrics.csv"), "true_positives_total,false_positives_total,false_negatives_total,rare_legitimate_flagged_total")
            check("Section 6.7: scenarios / eligible test histories / anomalies / rare labels", [12, 864, 108, 72], [int(row.scenario_count), int(row.evaluation_count_total), int(row.positive_count_total), int(row.rare_legitimate_count_total)], None, rel(DEV_DIR / "aggregate_metrics.csv"), "scenario_count,evaluation_count_total,positive_count_total,rare_legitimate_count_total")
        body.append([
            latex_escape(label), str(int(row.alert_count_total)), str(int(row.true_positives_total)), str(int(row.false_positives_total)), str(int(row.false_negatives_total)),
            f"{row.recall_mean:.3f} [{row.recall_ci95_low:.3f}, {row.recall_ci95_high:.3f}]",
            f"{int(row.rare_legitimate_flagged_total)}/{int(row.rare_legitimate_count_total)}",
        ])
    out = write_table(
        "rules_outcomes",
        "Deterministic check outcomes in exploratory development artifact \\texttt{4feea4508de1bb05} (12 scenarios, 864 eligible test histories, 108 labelled anomalies). Counts are pooled; recall is the scenario mean with its stored 95\\% interval. Method identifiers: \\texttt{deterministic\\_invariant\\_rules}, \\texttt{deterministic\\_rules}, \\texttt{deterministic\\_policy\\_rules}. The rare-label denominator includes 24 grandfathering labels without independently established entitlement, so 0/72 is not a validated false-positive rate.",
        "tab:rules-outcomes",
        "@{}lrrrrcr@{}",
        ["Deterministic method", "Alerts", "TP", "FP", "FN", "Recall [95\\% CI]", "Rare alerted"],
        body,
    )
    return {"outputs": [out], "caption": "Deterministic check outcomes (Section 6.7).",
            "sources": [source(DEV_DIR / "aggregate_metrics.csv", ["method", "representation", "alert_count_total", "true_positives_total", "false_positives_total", "false_negatives_total", "recall_mean", "recall_ci95_low", "recall_ci95_high", "rare_legitimate_flagged_total", "rare_legitimate_count_total"], "operating_point == 'rules_fixed' and method in deterministic_*")]}


def table_demo(demo_path: Path) -> dict:
    raw_bytes = demo_path.read_bytes()
    encoding = "utf-16" if raw_bytes[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    data = json.loads(raw_bytes.decode(encoding))
    names = {r[0]: r[1] for r in REPRESENTATIONS}
    ns = {int(d["n"]) for d in data}
    ks = {int(d["k"]) for d in data}
    assert len(ns) == 1 and len(ks) == 1
    body, last = [], None
    for d in data:
        if last is not None and d["scenario"] != last:
            body.append(None)
        first = d["scenario"] != last
        last = d["scenario"]
        body.append([
            latex_escape(d["scenario"]) if first else "",
            latex_escape(d["population"].replace("_", " ")) if first else "",
            latex_escape(names.get(d["method"], d["method"])),
            str(d["tp"]), str(d["fp"]), str(d["fn"]),
            f"{d['recall']:.3f}", f"{d['precision']:.3f}", latex_escape(d["rare"]),
        ])
    n, k = ns.pop(), ks.pop()
    out = write_table(
        "demo_outcomes",
        f"In-app demonstration output, not experimental evidence. Each MyHR demonstration view ranks n = {n} histories from one development scenario and reviews the top k = {k}. The values illustrate the interface and must not be interpreted as performance estimates; they are a small, inspected, non-random excerpt.",
        "tab:demo-outcomes",
        "@{}lllrrrrrr@{}",
        ["Scenario", "Population", "Representation", "TP", "FP", "FN", "Recall", "Precision", "Rare alerted"],
        body,
    )
    return {"outputs": [out], "caption": "In-app demonstration outcomes (demonstration output, not experimental evidence).",
            "sources": [{"path": str(demo_path), "path_template": "%LOCALAPPDATA%/Temp/myhr_drive/demo_counts.json", "sha256": sha256(demo_path),
                         "columns": ["scenario", "population", "method", "n", "k", "tp", "fp", "fn", "recall", "precision", "rare"],
                         "note": "Exported by the in-app demonstration; outside the repository and not an audited research artifact."}],
            "evidence_status": "demonstration output only"}


def table_abstract_commitments() -> dict:
    text = PAPER.read_text(encoding="utf-8")
    start = text.index("### 1.6")
    end = text.index("\n## ", start)
    section = text[start:end]
    rows = [ln for ln in section.splitlines() if ln.strip().startswith("|")]
    cells = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in rows]
    header, data = cells[0], [c for c in cells[2:]]
    assert all(len(c) == 3 for c in data), "Section 1.6 table must have three columns"
    body = [[md_cell_to_latex(c) for c in row] for row in data]
    colspec = r"@{}>{\raggedright\arraybackslash}p{4.3cm}>{\raggedright\arraybackslash}p{2.7cm}>{\raggedright\arraybackslash}p{6.0cm}@{}"
    out = write_table(
        "abstract_commitments",
        "Status of the submitted abstract commitments. ``Implemented'' means code and tests exist in the \\texttt{research} branch; it does not mean the method was shown to work.",
        "tab:abstract-commitments",
        colspec,
        [latex_escape(h) for h in header],
        body,
    )
    return {"outputs": [out], "caption": "Status of the submitted abstract commitments (mirrors Section 1.6).",
            "sources": [source(PAPER, ["Section 1.6 Markdown table"], "### 1.6 Status of the Submitted Abstract Commitments",
                               "Parsed verbatim from the paper draft at build time; the draft is edited concurrently, so rebuild after changes.")]}


# --------------------------------------------------------------------------- main
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo-counts", type=Path, default=DEFAULT_DEMO_COUNTS, help="Path to the in-app demo_counts.json export")
    args = parser.parse_args()
    for d in (FIG_DIR, SRC_DIR, TAB_DIR):
        d.mkdir(parents=True, exist_ok=True)
    if not args.demo_counts.exists():
        raise FileNotFoundError(f"Demonstration export not found: {args.demo_counts} (pass --demo-counts)")

    font = configure_matplotlib()
    git = git_info()
    dot_version = subprocess.run([str(DOT_EXE), "-V"], capture_output=True, text=True).stderr.strip()

    rows = load_dev_rows()
    paired = pd.read_csv(DEV_DIR / "paired_comparisons.csv")
    prow = paired[(paired.method == PRIMARY_METHOD) & (paired.operating_point == PRIMARY_OP)].iloc[0]
    pc = rel(DEV_DIR / "paired_comparisons.csv")
    check("Section 6.7: primary recall difference", 0.0278, prow.recall_delta_mean, 4, pc, "recall_delta_mean")
    check("Section 6.7: primary recall 95% CI low", -0.0278, prow.recall_delta_ci95_low, 4, pc, "recall_delta_ci95_low")
    check("Section 6.7: primary recall 95% CI high", 0.1019, prow.recall_delta_ci95_high, 4, pc, "recall_delta_ci95_high")
    check("Section 6.7: primary sign-flip p", 0.6875, prow.recall_delta_sign_flip_p, 4, pc, "recall_delta_sign_flip_p")
    check("Section 6.7: precision difference", 0.0313, prow.precision_delta_mean, 4, pc, "precision_delta_mean")
    check("Section 6.7: precision CI low", -0.0313, prow.precision_delta_ci95_low, 4, pc, "precision_delta_ci95_low")
    check("Section 6.7: precision CI high", 0.1042, prow.precision_delta_ci95_high, 4, pc, "precision_delta_ci95_high")
    check("Section 6.7: exploratory Holm-adjusted recall p", 1.0, prow.recall_delta_holm_all_p, 4, pc, "recall_delta_holm_all_p")

    truth = pd.read_csv(DEV_DIR / "record_truth.csv", usecols=["split"])
    split_counts = truth["split"].value_counts().to_dict()
    check("Section 6.7: test histories (record_truth split == test)", 864, int(split_counts["test"]), None, rel(DEV_DIR / "record_truth.csv"), "split")

    consts, reps = parse_representations(PROTOCOL_PY)
    consts_dev, reps_dev = parse_representations(PROTOCOL_PY, DEV_COMMIT)
    consts_hist, _ = parse_representations(PROTOCOL_PY, HIST_COMMIT)
    assert (consts, reps) == (consts_dev, reps_dev), "feature representations changed since artifact 4feea4508de1bb05; update Figure 5"
    assert consts == consts_hist, "feature constants differ from the historical commit; update Figure 11"
    assert [r[0] for r in reps] and {r[0] for r in reps} == {r[0] for r in REPRESENTATIONS}
    features_text = FEATURES_PY.read_text(encoding="utf-8")
    for names in consts.values():
        for f in names:
            assert f'"{f}"' in features_text, f"{f} is not a feature key in features.py"
    core_n = len(consts_hist["COMMON_CORE_FEATURES"])
    pol_n = len([f for f in consts_hist["POLICY_MATCHED_FEATURES"] if f not in consts_hist["COMMON_CORE_FEATURES"]])
    raw_n = len([f for f in consts_hist["RAW_MATCHED_FEATURES"] if f not in consts_hist["COMMON_CORE_FEATURES"]])
    check("Section 6.5: historical common core / policy-specific / extra raw feature counts", [6, 3, 3], [core_n, pol_n, raw_n], None,
          f"git show {HIST_COMMIT[:7]}:{rel(PROTOCOL_PY)}", "COMMON_CORE_FEATURES, POLICY_MATCHED_FEATURES, RAW_MATCHED_FEATURES")
    dev_meta = json.loads((DEV_DIR / "metadata.json").read_text(encoding="utf-8"))
    review_budget = float(dev_meta["review_budget"])

    entries: dict[str, dict] = {}
    # Graphviz diagrams
    for name, text, caption, srcs in (
        ("feature_design", dot_feature_design(consts, reps),
         "Matched feature representations and controls as defined in protocol_evaluation.feature_representations(). "
         "Raw and policy-aware representations share the common core and add three features each. Raw ablations remove columns; "
         "policy ablations keep the core plus one policy feature. The wrong-policy and shuffled-policy controls use the same "
         "columns as policy_matched but alter the policy input. Feature names are those of features.py.",
         [code_source(PROTOCOL_PY, "COMMON_CORE_FEATURES, RAW_MATCHED_FEATURES, POLICY_MATCHED_FEATURES, feature_representations(), _vectors(), _wrong_policy(), _frequency_preserving_policy_permutation()", (DEV_DIR,)),
          code_source(FEATURES_PY, "feature keys of extract_raw_features() and _promotion_service_context()", (DEV_DIR,)),
          git_blob_source(DEV_COMMIT, PROTOCOL_PY, "feature constants and representations identical to the current file (asserted at build time)", DEV_DIR)]),
        ("feature_collapse", dot_feature_collapse(core_n, raw_n, pol_n, review_budget),
         "Historical residual design failure and corrected design. In the historical design the residual filter removed every "
         "history with a positive policy deficit, so the three policy-specific features were zero for every retained history "
         "and the comparison could not test the policy hypothesis. The corrected design gates only on invariant contradictions "
         "and gives every representation the same fixed additional review budget over the same residual histories.",
         [git_blob_source(HIST_COMMIT, PROTOCOL_PY, "residual filter on validate_record_with_policy() scores; feature constants", HIST_DIR),
          code_source(PROTOCOL_PY, "residual filter on validate_invariant_record() scores; _top_budget_predictions()", (DEV_DIR,)),
          code_source(DETERMINISTIC_PY, "validate_invariant_record(), validate_record_with_policy()", (HIST_DIR, DEV_DIR)),
          source(DEV_DIR / "metadata.json", ["review_budget"]),
          source(PAPER, ["Sections 4.6 and 6.5 (text)"], note="Zero-valued policy features after filtering are stated in Section 6.5 and docs/RESEARCH_HANDOVER.md section 5.2; not recomputed from record-level features here.")]),
        ("duplicate_results", dot_duplicate_contract(),
         "Duplicate-evaluation contract implemented in duplicate_detection.evaluate_duplicate_detection(). Truth pairs come from "
         "entity clusters within one partition; each method declares its pair universe, and TP, FP, FN and TN are counted by set "
         "membership within it. Blocking recall and end-to-end, workload, runtime and memory figures are reported separately. "
         "No duplicate-performance claim is made.",
         [code_source(DUPLICATE_PY, "evaluate_duplicate_detection(), confusion_counts_for_pairs(), _true_duplicate_pairs(), _blocked_similarity_pairs(), select_similarity_threshold()", (DEV_DIR,))]),
        ("architecture", dot_architecture(),
         "Rules-first, ML-second decision-support architecture. Deterministic checks produce evidence-rich findings; histories "
         "without an invariant finding receive matched raw or policy-aware features, an Isolation Forest score and a top-k "
         "position within a fixed additional review budget. Both paths end in a review queue. The dashed boundary marks the "
         "only decision point: an authorized human reviewer. Anomaly scores never trigger automatic personnel decisions.",
         [source(PAPER, ["Sections 4.6, 4.9, 4.16 (text)"], note="Conceptual diagram; no numeric data.")]),
        ("experiment_flow", dot_experiment_flow(split_counts),
         "Evaluation lifecycle. Within each scenario, models are fitted on training histories, thresholds are selected on "
         "validation histories and metrics are computed on test histories (counts from artifact 4feea4508de1bb05). "
         "Development and validation scenario families remain inspectable; the final holdout is not generated and has never "
         "been accessed, and stays locked until a human-approved protocol freeze.",
         [source(DEV_DIR / "record_truth.csv", ["split"], note="Counts of train/validation/test histories."), source(PAPER, ["Section 4.3 (text)"], note="Boundary definitions.")]),
        ("artifact_lifecycle", dot_artifact_lifecycle(),
         "Write-once artifact lifecycle. Runs execute in a process-owned staging directory, record provenance and a SHA-256 "
         "manifest, and are atomically published. An independent audit recomputes checksums and statistics; failed artifacts "
         "are preserved with the defect recorded. Verification establishes reproducible arithmetic, not scientific validity.",
         [source(PAPER, ["Section 4.14 (text)"], note="Conceptual diagram; no numeric data.")]),
    ):
        outs, layout = render_dot(name, text)
        fonts = pdf_base_fonts(FIG_DIR / f"{name}.pdf")
        if font["family"] == "Times New Roman" and not all("TimesNewRoman" in f for f in fonts):
            raise RuntimeError(f"{name}: Graphviz did not embed Times New Roman (embedded: {fonts})")
        entries[name] = {"kind": "graphviz", "outputs": outs, "caption": caption, "sources": srcs, "layout": layout, "pdf_embedded_fonts": fonts}

    for name, fn in (
        ("primary_recall", lambda: fig_primary_recall(rows, prow)),
        ("residual_outcomes", lambda: fig_residual_outcomes(rows)),
        ("validation_counts", fig_validation_counts),
        ("policy_alerts", fig_policy_alerts),
        ("confound_diagnostic", fig_confound_diagnostic),
        ("policy_timeline", fig_policy_timeline),
    ):
        e = fn()
        e["kind"] = "matplotlib"
        e["layout"] = {"width_in": FIG_WIDTH_IN, "height_in": MPL_SIZES[name][1], "min_font_pt_at_design_size": MIN_FONT_PT}
        e["pdf_embedded_fonts"] = pdf_base_fonts(FIG_DIR / f"{name}.pdf")
        entries[name] = e

    tables = {
        "residual_equal_budget": table_residual(rows),
        "rules_outcomes": table_rules(),
        "demo_outcomes": table_demo(args.demo_counts),
        "abstract_commitments": table_abstract_commitments(),
    }
    for t in tables.values():
        t["kind"] = "latex_booktabs"

    for e in list(entries.values()) + list(tables.values()):
        e["output_sha256"] = {o: sha256(REPO / o) for o in e["outputs"]}

    used_fonts = sorted({f for e in entries.values() for f in e["pdf_embedded_fonts"]})
    manifest = {
        "generator": "scripts/build_tdk_figures.py",
        "generator_sha256": sha256(Path(__file__)),
        "git": git,
        "font": {"requested": "Times New Roman", "matplotlib_family_used": font["family"], "matplotlib_font_file": font["file"], "graphviz_fontname": "Times New Roman", "pdf_embedded_fonts": used_fonts},
        "tools": {"python": sys.version.split()[0], "matplotlib": matplotlib.__version__, "pandas": pd.__version__, "graphviz": dot_version},
        "design": {"placed_width_in": FIG_WIDTH_IN, "min_font_pt": MIN_FONT_PT, "png_dpi": 300, "palette": "Okabe-Ito where colour encodes information; otherwise black/grey"},
        "figures": entries,
        "tables": tables,
        "paper_consistency_checks": CHECKS,
        "mismatch_count": sum(c["status"] != "match" for c in CHECKS),
        "holdout_accessed": False,
    }
    (FIG_DIR / "FIGURE_MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"font: {font['family']} ({font['file']}); embedded: {', '.join(used_fonts)}")
    for c in CHECKS:
        if c["status"] != "match":
            print("MISMATCH:", c)
    print(f"checks: {len(CHECKS)} total, {manifest['mismatch_count']} mismatches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
