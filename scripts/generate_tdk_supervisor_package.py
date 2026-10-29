from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


TITLE = "MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression"
AUTHOR = "Muhammad Ibrahim Shoeb"
SUPERVISOR = "Dr. Husam Al-Magsoosi"
GREEN = "0B6B45"
LIGHT_GREEN = "E8F5EE"
LIGHT_GRAY = "F2F2F2"
BORDER = "D9D9D9"


def _save_figure(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close()


def _diagram_box(ax, x, y, width, height, text, color=LIGHT_GREEN, edge=GREEN):
    rect = plt.Rectangle((x, y), width, height, facecolor=f"#{color}", edgecolor=f"#{edge}", linewidth=1.5)
    ax.add_patch(rect)
    ax.text(x + width / 2, y + height / 2, text, ha="center", va="center", fontsize=10, wrap=True)


def generate_figures(repo: Path, assets: Path) -> None:
    assets.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    boxes = [
        (0.2, 3.2, 1.7, 1.0, "Administrative\nrecords"),
        (2.3, 3.2, 1.7, 1.0, "Deterministic\nvalidation"),
        (4.4, 3.2, 1.7, 1.0, "Raw and policy-aware\nfeatures"),
        (6.5, 3.2, 1.4, 1.0, "Isolation\nForest"),
        (8.3, 3.2, 1.5, 1.0, "Review\npriority"),
        (3.2, 0.8, 2.0, 1.0, "Evidence-rich\nexplanation"),
        (6.2, 0.8, 2.0, 1.0, "Authorized human\nreview"),
    ]
    for box in boxes:
        _diagram_box(ax, *box)
    arrows = [((1.9, 3.7), (2.3, 3.7)), ((4.0, 3.7), (4.4, 3.7)), ((6.1, 3.7), (6.5, 3.7)), ((7.9, 3.7), (8.3, 3.7)), ((3.2, 3.2), (4.1, 1.8)), ((8.9, 3.2), (7.5, 1.8)), ((5.2, 1.3), (6.2, 1.3))]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "color": "#4A4A4A", "lw": 1.3})
    ax.text(5, 4.65, "Rules-first, ML-second decision-support architecture", ha="center", fontsize=13, fontweight="bold")
    _save_figure(assets / "architecture.png")

    screenshot = repo / "docs" / "media" / "screenshots" / "employee.png"
    if screenshot.exists():
        shutil.copy2(screenshot, assets / "myhr_ui.png")
    else:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.axis("off")
        ax.text(0.5, 0.5, "MyHR employee performance interface", ha="center", va="center", fontsize=18)
        _save_figure(assets / "myhr_ui.png")

    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 48)
    ax.set_ylim(-1.2, 3.5)
    ax.axis("off")
    ax.hlines(1.0, 0, 48, color="#333333", linewidth=2)
    for month, label in [(0, "Role start"), (12, "Annual\nincrement"), (24, "Commendation\n+3 months"), (33, "Sanction\n+3 months delay"), (36, "Policy\nchange"), (39, "Decision")]:
        ax.vlines(month, 0.75, 1.25, color=f"#{GREEN}", linewidth=2)
        ax.text(month, 0.55 if month % 24 else 1.45, label, ha="center", va="top" if month % 24 else "bottom", fontsize=10)
    ax.annotate("Effective policy must be resolved at the decision date", xy=(39, 1.0), xytext=(20, 3.0), arrowprops={"arrowstyle": "->", "color": "#B42318"}, fontsize=11, color="#B42318")
    ax.set_title("Progression evidence across service and policy time", fontsize=13, fontweight="bold")
    _save_figure(assets / "policy_timeline.png")

    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    stages = [(0.2, "Development\ninspectable"), (2.25, "Validation\nthresholds and design"), (4.65, "Human protocol\napproval"), (6.75, "Frozen\nrevision and analysis"), (8.45, "One-time\nholdout")]
    for x, label in stages:
        color = "FDECEC" if "holdout" in label.lower() else LIGHT_GREEN
        edge = "B42318" if "holdout" in label.lower() else GREEN
        _diagram_box(ax, x, 1.45, 1.35, 1.0, label, color, edge)
    for x1, x2 in zip([1.55, 3.6, 6.0, 8.1], [2.25, 4.65, 6.75, 8.45]):
        ax.annotate("", xy=(x2, 1.95), xytext=(x1, 1.95), arrowprops={"arrowstyle": "->", "lw": 1.4})
    ax.text(9.1, 0.8, "LOCKED", ha="center", color="#B42318", fontsize=11, fontweight="bold")
    ax.set_title("Research evaluation lifecycle", fontsize=13, fontweight="bold")
    _save_figure(assets / "experiment_flow.png")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.axis("off")
    raw = ["event counts", "raw intervals", "administrative density", "commendation count", "sanction count"]
    policy = ["common core", "service deficit", "deficit ratio", "short-promotion evidence", "policy identity"]
    controls = ["wrong policy", "shuffled policy", "single-feature ablations", "raw without shortcut"]
    for x, title, values, color in [(0.05, "Raw representation", raw, "EAF2FF"), (0.37, "Policy-aware representation", policy, LIGHT_GREEN), (0.72, "Controls", controls, "FFF4D6")]:
        rect = plt.Rectangle((x, 0.12), 0.25, 0.76, transform=ax.transAxes, facecolor=f"#{color}", edgecolor="#555555")
        ax.add_patch(rect)
        ax.text(x + 0.125, 0.81, title, transform=ax.transAxes, ha="center", va="top", fontweight="bold", fontsize=11)
        for i, value in enumerate(values):
            ax.text(x + 0.03, 0.68 - i * 0.12, f"• {value}", transform=ax.transAxes, fontsize=10)
    ax.text(0.5, 0.97, "Matched representations and falsification controls", transform=ax.transAxes, ha="center", fontsize=13, fontweight="bold")
    _save_figure(assets / "feature_design.png")

    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.axis("off")
    stages = ["Run in owned\nstaging directory", "Write configuration,\npredictions, metrics", "Create SHA-256\nmanifest", "Atomic publish to\nwrite-once directory", "Independent\nrecomputation"]
    for i, label in enumerate(stages):
        x = 0.03 + i * 0.195
        _diagram_box(ax, x, 0.38, 0.16, 0.28, label)
        if i < len(stages) - 1:
            ax.annotate("", xy=(x + 0.19, 0.52), xytext=(x + 0.16, 0.52), xycoords=ax.transAxes, textcoords=ax.transAxes, arrowprops={"arrowstyle": "->", "lw": 1.2})
    ax.text(0.5, 0.85, "Reproducible artifact lifecycle", transform=ax.transAxes, ha="center", fontsize=13, fontweight="bold")
    _save_figure(assets / "artifact_lifecycle.png")

    methods = ["Rules", "Rules + raw IF", "Rules + policy IF"]
    tp = [351, 357, 358]
    fp = [0, 51, 50]
    fn = [9, 3, 2]
    x = range(len(methods))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar([i - 0.25 for i in x], tp, width=0.25, label="True positives", color="#16834F")
    ax.bar(x, fp, width=0.25, label="False positives", color="#C58A00")
    ax.bar([i + 0.25 for i in x], fn, width=0.25, label="False negatives", color="#C92A2A")
    ax.set_xticks(list(x), methods)
    ax.set_ylabel("Pooled count across 30 validation scenarios")
    ax.legend(frameon=False, ncol=3, loc="upper center")
    ax.grid(axis="y", alpha=0.25)
    _save_figure(assets / "validation_counts.png")

    metrics_path = repo / "research_outputs" / "independent_development" / "independent_development_e342bd4acf39b06b" / "scenario_metrics.csv"
    metrics = pd.read_csv(metrics_path)
    selected = metrics[(metrics["method"] == "rule_negative_isolation_forest") & (metrics["operating_point"] == "fixed_review_budget")]
    scenario_col = "scenario_id" if "scenario_id" in selected.columns else "scenario"
    pivot = selected.pivot_table(index=scenario_col, columns="representation", values="average_precision", aggfunc="first").sort_index()
    positives = selected.groupby(scenario_col)["positive_count"].max() if "positive_count" in selected.columns else pd.Series(1, index=pivot.index)
    fig, ax = plt.subplots(figsize=(10, 5.2))
    positions = range(len(pivot))
    ax.plot(positions, pivot.get("raw_matched"), marker="o", label="Raw", color="#333333")
    ax.plot(positions, pivot.get("policy_matched"), marker="s", label="Policy-labelled", color="#16834F")
    for i, scenario in enumerate(pivot.index):
        if positives.get(scenario, 1) == 0:
            ax.axvspan(i - 0.35, i + 0.35, color="#FDECEC", alpha=0.8)
    ax.set_xticks(list(positions), [str(x).replace("ind-dev-", "") for x in pivot.index])
    ax.set_xlabel("Independent development scenario")
    ax.set_ylabel("Stored scenario average precision")
    ax.set_ylim(-0.03, 1.05)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    ax.text(0.01, -0.22, "Red bands mark scenarios with no residual positives; their stored AP=0 convention is disputed.", transform=ax.transAxes, fontsize=10)
    _save_figure(assets / "independent_ap.png")

    fig, ax = plt.subplots(figsize=(9, 4.6))
    feature_names = ["Service deficit", "Deficit ratio", "Unexplained short promotion"]
    ax.bar(feature_names, [0, 0, 0], color="#16834F")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Number of distinct positive values after filtering")
    ax.text(1, 0.45, "All policy-specific residual features\nare constant zero", ha="center", va="center", fontsize=16, fontweight="bold", color="#B42318")
    ax.grid(axis="y", alpha=0.2)
    _save_figure(assets / "feature_collapse.png")

    fig, ax = plt.subplots(figsize=(9, 4.8))
    labels = ["Grandfathered\npolicy", "Recognized prior\nservice", "Delayed bulk\nrecording"]
    values = [19, 20, 0]
    bars = ax.bar(labels, values, color=["#C58A00", "#C58A00", "#16834F"])
    ax.set_ylim(0, 24)
    ax.set_ylabel("False alerts among 24 nominal rare cases")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.7, f"{value}/24", ha="center", fontsize=11, fontweight="bold")
    ax.grid(axis="y", alpha=0.25)
    _save_figure(assets / "policy_alerts.png")

    duplicate_path = repo / "research_outputs" / "ff34fffafa77" / "duplicate_metrics.csv"
    duplicate = pd.read_csv(duplicate_path)
    names = ["Exact", "Normalized exact", "Similarity 0.70"]
    x = range(3)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar([i - 0.18 for i in x], duplicate["precision"], width=0.36, label="Precision", color="#16834F")
    ax.bar([i + 0.18 for i in x], duplicate["recall"], width=0.36, label="Recall", color="#4C78A8")
    ax.set_xticks(list(x), names)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Metric value")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    ax.text(0.01, -0.20, "Single-seed development diagnostic; not a validated entity-resolution benchmark.", transform=ax.transAxes, fontsize=10)
    _save_figure(assets / "duplicate_results.png")


def _set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def _set_cell_borders(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), BORDER)


def _add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char1, instr_text, fld_char2])


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.5)
    section.bottom_margin = Cm(3.5)
    section.left_margin = Cm(3.5)
    section.right_margin = Cm(3.5)

    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.0
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    heading_sizes = {1: 16, 2: 14, 3: 12}
    for level, size in heading_sizes.items():
        style = document.styles[f"Heading {level}"]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.keep_with_next = True

    if "Code Block" not in [style.name for style in document.styles]:
        code = document.styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
        code.font.name = "Consolas"
        code._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        code.font.size = Pt(10)
        code.paragraph_format.left_indent = Cm(0.7)
        code.paragraph_format.right_indent = Cm(0.7)
        code.paragraph_format.space_before = Pt(4)
        code.paragraph_format.space_after = Pt(6)

    for doc_section in document.sections:
        _add_page_number(doc_section.footer.paragraphs[0])


def add_title_pages(document: Document, lines: list[str]) -> None:
    document.add_paragraph("Budapest University of Technology and Economics", style="Subtitle").alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph("Faculty of Electrical Engineering and Informatics", style="Subtitle").alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph()
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(80)
    run = title.add_run(TITLE)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(20)
    subtitle = document.add_paragraph("TDK Paper Supervisor Review Draft")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].font.size = Pt(14)
    document.add_paragraph()
    for label, value in [("Author", AUTHOR), ("Supervisor", SUPERVISOR), ("Date", "30 October 2026")]:
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.add_run(f"{label}: ").bold = True
        paragraph.add_run(value)
    warning = document.add_paragraph()
    warning.alignment = WD_ALIGN_PARAGRAPH.CENTER
    warning.paragraph_format.space_before = Pt(80)
    run = warning.add_run("Development evidence only. Draft protocol. Final holdout locked.")
    run.bold = True
    run.font.color.rgb = RGBColor(180, 35, 24)
    document.add_page_break()


def _parse_table(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    if len(rows) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in rows[1]):
        rows.pop(1)
    return rows


def add_table(document: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    width = max(len(row) for row in rows)
    table = document.add_table(rows=len(rows), cols=width)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for row_index, row in enumerate(rows):
        cant_split = OxmlElement("w:cantSplit")
        table.rows[row_index]._tr.get_or_add_trPr().append(cant_split)
        if row_index == 0:
            repeat_header = OxmlElement("w:tblHeader")
            repeat_header.set(qn("w:val"), "true")
            table.rows[row_index]._tr.get_or_add_trPr().append(repeat_header)
        for column_index in range(width):
            cell = table.cell(row_index, column_index)
            text = row[column_index] if column_index < len(row) else ""
            cell.text = text
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _set_cell_borders(cell)
            if row_index == 0:
                _set_cell_shading(cell, GREEN)
                for run in cell.paragraphs[0].runs:
                    run.font.color.rgb = RGBColor(255, 255, 255)
                    run.bold = True
            elif row_index % 2 == 0:
                _set_cell_shading(cell, LIGHT_GRAY)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(2)
                paragraph.paragraph_format.space_before = Pt(2)
                paragraph.paragraph_format.line_spacing = 1.0
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(9.5)
    if len(rows) <= 6:
        for row in table.rows[:-1]:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True
    document.add_paragraph()


def add_figure(document: Document, assets: Path, name: str, caption: str) -> None:
    path = assets / name
    if not path.exists():
        raise FileNotFoundError(path)
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run()
    width = 5.0 if name == "myhr_ui.png" else 6.0
    run.add_picture(str(path), width=Inches(width))
    caption_paragraph = document.add_paragraph(caption)
    caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption_paragraph.paragraph_format.keep_with_next = False
    for run in caption_paragraph.runs:
        run.italic = True
        run.font.size = Pt(10)


def build_docx(source: Path, assets: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    document = Document()
    configure_document(document)
    add_title_pages(document, lines)

    in_code = False
    code_lines: list[str] = []
    paragraph_lines: list[str] = []
    table_lines: list[str] = []
    seen_intro = False
    seen_references = False
    after_heading = False

    def add_hidden_marker(text: str, bookmark_name: str, bookmark_id: int) -> None:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 0.1
        run = paragraph.add_run(text)
        run.font.hidden = True
        run.font.size = Pt(1)
        bookmark_start = OxmlElement("w:bookmarkStart")
        bookmark_start.set(qn("w:id"), str(bookmark_id))
        bookmark_start.set(qn("w:name"), bookmark_name)
        bookmark_end = OxmlElement("w:bookmarkEnd")
        bookmark_end.set(qn("w:id"), str(bookmark_id))
        paragraph._p.insert(0, bookmark_start)
        paragraph._p.append(bookmark_end)

    def flush_paragraph() -> None:
        nonlocal paragraph_lines, after_heading
        if paragraph_lines:
            content = " ".join(line.strip() for line in paragraph_lines).strip()
            if content:
                paragraph = document.add_paragraph()
                paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                if after_heading:
                    paragraph.paragraph_format.keep_together = True
                paragraph.add_run(content)
                after_heading = False
            paragraph_lines = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            add_table(document, _parse_table(table_lines))
            table_lines = []

    for line in lines:
        if line.startswith("# "):
            continue
        if line.startswith("**Author:") or line.startswith("**Supervisor:") or line.startswith("**Institution:") or line.startswith("**Paper language:") or line.startswith("**Status:"):
            continue
        if line.strip().startswith("```"):
            flush_paragraph()
            flush_table()
            if in_code:
                paragraph = document.add_paragraph("\n".join(code_lines), style="Code Block")
                for run in paragraph.runs:
                    run.font.name = "Consolas"
                    run.font.size = Pt(10)
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.startswith("|"):
            flush_paragraph()
            table_lines.append(line)
            continue
        flush_table()
        figure = re.fullmatch(r"\[\[FIGURE:([^|]+)\|(.+)\]\]", line.strip())
        if figure:
            flush_paragraph()
            add_figure(document, assets, figure.group(1), figure.group(2))
            continue
        if line.startswith("## "):
            flush_paragraph()
            heading = line[3:].strip()
            if heading.startswith("1 Introduction") and not seen_intro:
                document.add_page_break()
                add_hidden_marker("MYHR_MAIN_TEXT_START_2026", "MYHR_MAIN_TEXT_START", 100)
                seen_intro = True
            elif heading == "References" and not seen_references:
                document.add_page_break()
                add_hidden_marker("MYHR_MAIN_TEXT_END_2026", "MYHR_MAIN_TEXT_END", 101)
                seen_references = True
            elif re.match(r"^[278] ", heading):
                document.add_page_break()
            heading_paragraph = document.add_heading(heading, level=1)
            heading_paragraph.paragraph_format.keep_with_next = True
            after_heading = True
            continue
        if line.startswith("### "):
            flush_paragraph()
            heading_paragraph = document.add_heading(line[4:].strip(), level=2)
            heading_paragraph.paragraph_format.keep_with_next = True
            after_heading = True
            continue
        if line.startswith("#### "):
            flush_paragraph()
            heading_paragraph = document.add_heading(line[5:].strip(), level=3)
            heading_paragraph.paragraph_format.keep_with_next = True
            after_heading = True
            continue
        if re.match(r"^\d+\. ", line):
            flush_paragraph()
            paragraph = document.add_paragraph(line.strip())
            paragraph.paragraph_format.left_indent = Cm(0.7)
            paragraph.paragraph_format.first_line_indent = Cm(-0.5)
            continue
        if line.startswith("- "):
            flush_paragraph()
            document.add_paragraph(line[2:].strip(), style="List Bullet")
            continue
        if not line.strip():
            flush_paragraph()
            continue
        paragraph_lines.append(line)

    flush_paragraph()
    flush_table()
    output.parent.mkdir(parents=True, exist_ok=True)
    document.core_properties.title = TITLE
    document.core_properties.author = AUTHOR
    document.core_properties.subject = "BME VIK TDK 2026 supervisor review draft"
    document.core_properties.keywords = "machine learning, anomaly detection, Isolation Forest, workforce progression, MyHR"
    document.save(output)


def build_decision_sheet(output: Path) -> None:
    document = Document()
    configure_document(document)
    section = document.sections[0]
    section.page_width = Cm(29.7)
    section.page_height = Cm(21)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("MyHR TDK Supervisor Decision Sheet")
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(16)
    status = document.add_paragraph("Nothing is approved until a human records a decision. The final holdout remains locked.")
    status.alignment = WD_ALIGN_PARAGRAPH.CENTER
    status.runs[0].bold = True
    status.runs[0].font.color.rgb = RGBColor(180, 35, 24)
    identity = document.add_paragraph("Date: ____________________    Reviewer: __________________________________________")
    identity.alignment = WD_ALIGN_PARAGRAPH.LEFT
    identity.paragraph_format.space_after = Pt(6)

    rows = [
        ("1. Primary estimand", "Redesign the residual task, or make the end-to-end rules-plus-ML queue primary.", "Recommendation: redesign; preserve the current run as development evidence."),
        ("2. Primary endpoint", "Choose scenario-level AP only for predeclared positive-eligible scenarios, or use fixed-capacity outcomes.", "Recommendation: predeclare eligibility and never remove scenarios after inspection."),
        ("3. Review capacity", "Report all deterministic findings, then allocate the same fixed ML budget among rule-negative histories.", "Recommendation: keep rule evidence and isolate the ML comparison."),
        ("4. Historical policy", "Store policy version, jurisdiction, effective time, recorded time, recognized service, and correction provenance.", "Recommendation: approve the complete temporal evidence contract."),
        ("5. Expert realism review", "Use two independent blinded reviewers with recorded reasons, disagreement, and adjudication.", "Recommendation: approve only after reviewer qualifications and sampling are fixed."),
        ("6. Holdout design", "Freeze a conceptually independent matrix with repeated seeds and per-record causal truth.", "Recommendation: do not reuse the inspected development generator as confirmatory evidence."),
    ]
    table = document.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Cm(5.0)
    table.columns[1].width = Cm(21.5)
    table.cell(0, 0).text = "Decision"
    table.cell(0, 1).text = "Evidence-based choice"
    for cell in table.rows[0].cells:
        _set_cell_shading(cell, GREEN)
        _set_cell_borders(cell)
        for run in cell.paragraphs[0].runs:
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.bold = True
    for index, (name, choice, recommendation) in enumerate(rows, start=1):
        cells = table.add_row().cells
        cells[0].text = name
        cells[1].text = f"{choice}\n{recommendation}\n[ ] Approve   [ ] Reject   [ ] Modify: ______________________________"
        for cell in cells:
            _set_cell_borders(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if index % 2 == 0:
                _set_cell_shading(cell, LIGHT_GRAY)
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                paragraph.paragraph_format.space_before = Pt(1)
                paragraph.paragraph_format.space_after = Pt(1)
                paragraph.paragraph_format.line_spacing = 0.92
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(9.2)
        cells[0].paragraphs[0].runs[0].bold = True
    for row in table.rows:
        row.cells[0].width = Cm(5.0)
        row.cells[1].width = Cm(21.5)
    footer = document.add_paragraph("Protocol freeze: [ ] No   [ ] Yes, after recorded modifications\nSignature: ______________________________    Date: ____________________")
    footer.alignment = WD_ALIGN_PARAGRAPH.LEFT
    footer.paragraph_format.space_before = Pt(5)
    footer.runs[0].bold = True
    document.save(output)


def convert_with_word(docx_path: Path, pdf_path: Path, report_path: Path) -> dict:
    ps1 = docx_path.parent / "_convert_tdk_document.ps1"
    script = f"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {{
    $document = $word.Documents.Open('{str(docx_path).replace("'", "''")}')
    $document.Repaginate()
    foreach ($field in $document.Fields) {{ try {{ $field.Update() | Out-Null }} catch {{ }} }}
    $total = $document.ComputeStatistics(2)
    $introPage = if ($document.Bookmarks.Exists('MYHR_MAIN_TEXT_START')) {{ $document.Bookmarks.Item('MYHR_MAIN_TEXT_START').Range.Information(3) }} else {{ 0 }}
    $refsPage = if ($document.Bookmarks.Exists('MYHR_MAIN_TEXT_END')) {{ $document.Bookmarks.Item('MYHR_MAIN_TEXT_END').Range.Information(3) }} else {{ 0 }}
    $mainPages = if ($introPage -gt 0 -and $refsPage -gt $introPage) {{ $refsPage - $introPage }} else {{ 0 }}
    $document.Save()
    $document.ExportAsFixedFormat('{str(pdf_path).replace("'", "''")}', 17)
    $result = [ordered]@{{ total_pages = $total; intro_page = $introPage; references_page = $refsPage; main_text_pages = $mainPages }}
    $result | ConvertTo-Json | Set-Content -Encoding UTF8 '{str(report_path).replace("'", "''")}'
    $document.Close($false)
}} finally {{
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}}
"""
    ps1.write_text(script, encoding="utf-8-sig")
    try:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)], check=True)
    finally:
        ps1.unlink(missing_ok=True)
    return json.loads(report_path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the MyHR TDK supervisor review package.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = args.output or (repo.parent / "TDK" / "final" / "2026-10-30-supervisor")
    output.mkdir(parents=True, exist_ok=True)
    docx_path = output / "MyHR_TDK_Paper_Draft_EN.docx"
    pdf_path = output / "MyHR_TDK_Paper_Draft_EN.pdf"
    page_report_path = output / "page_report.json"
    with tempfile.TemporaryDirectory(prefix="myhr_tdk_assets_") as directory:
        assets = Path(directory)
        generate_figures(repo, assets)
        build_docx(repo / "docs" / "TDK_PAPER_DRAFT.md", assets, docx_path)
    page_report = convert_with_word(docx_path, pdf_path, page_report_path)
    decision_docx = output / "_Supervisor_Decision_Sheet.docx"
    decision_pdf = output / "Supervisor_Decision_Sheet.pdf"
    decision_report = output / "_decision_page_report.json"
    build_decision_sheet(decision_docx)
    convert_with_word(decision_docx, decision_pdf, decision_report)
    decision_docx.unlink(missing_ok=True)
    decision_report.unlink(missing_ok=True)
    page_report_path.unlink(missing_ok=True)
    shutil.copy2(repo / "docs" / "TDK_SUPERVISOR_BRIEF_2026-10-30.md", output / "README.md")
    verification = repo / "docs" / "TDK_SUPERVISOR_PACKAGE_VERIFICATION_2026-10-30.md"
    if verification.exists():
        shutil.copy2(verification, output / "Verification_Report.md")
    print(json.dumps({"docx": str(docx_path), "pdf": str(pdf_path), "decision_sheet": str(decision_pdf), **page_report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
