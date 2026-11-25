"""Build the revised TDK manuscript package from the verified research record."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from generate_tdk_supervisor_package import (
    build_docx,
    convert_with_word,
    generate_figures,
)


HOLDOUT_FIGURES = (
    "holdout_primary_comparison",
    "holdout_model_sensitivity",
    "holdout_robustness",
)
RESULT_TABLES = (
    "holdout_primary_results.csv",
    "holdout_endpoint_contrasts.csv",
    "holdout_complete_workflow.csv",
    "holdout_model_sensitivity.csv",
    "holdout_robustness.csv",
)


def build_package(repo: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    docx = output / "MyHR_TDK_Paper_Revised_2026-11-25.docx"
    pdf = output / "MyHR_TDK_Paper_Revised_2026-11-25.pdf"
    page_report = output / "page_report.json"

    with tempfile.TemporaryDirectory(prefix="myhr_tdk_revised_") as directory:
        assets = Path(directory)
        generate_figures(repo, assets)
        for stem in HOLDOUT_FIGURES:
            for suffix in (".png", ".pdf", ".svg"):
                source = repo / "docs" / "figures" / f"{stem}{suffix}"
                if source.exists():
                    shutil.copy2(source, assets / source.name)
        build_docx(repo / "docs" / "TDK_PAPER_DRAFT.md", assets, docx)

    pages = convert_with_word(docx, pdf, page_report)
    (output / "figures").mkdir(exist_ok=True)
    (output / "tables").mkdir(exist_ok=True)
    for stem in HOLDOUT_FIGURES:
        for suffix in (".png", ".pdf", ".svg"):
            source = repo / "docs" / "figures" / f"{stem}{suffix}"
            if source.exists():
                shutil.copy2(source, output / "figures" / source.name)
    for name in RESULT_TABLES:
        shutil.copy2(repo / "docs" / "tables" / name, output / "tables" / name)

    manifest = json.loads(
        (repo / "docs" / "results" / "holdout_report_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    (output / "START_HERE.md").write_text(
        "\n".join(
            (
                "# MyHR TDK Revised Research Package",
                "",
                "This package replaces the research interpretation in the submitted paper; the submitted archive remains unchanged.",
                "",
                "## Reading Order",
                "",
                "1. Read the abstract and Sections 6 to 8 in the revised PDF.",
                "2. Inspect the three figures in `figures/`.",
                "3. Use the CSV files in `tables/` to verify every reported denominator and comparison.",
                "",
                "## Main Finding",
                "",
                "At equal review capacity, policy-aware Isolation Forest improved scenario-mean recall by 6.81 percentage points in the frozen synthetic holdout. The rare-legitimate false-alert result remained inconclusive, and external validity remains limited.",
                "",
                f"Verified artifact: `{manifest['artifact_id']}`.",
                f"Frozen scientific implementation: `{manifest['frozen_git_commit']}`.",
                "",
            )
        ),
        encoding="utf-8",
        newline="\n",
    )
    page_report.unlink(missing_ok=True)
    return {"docx": str(docx), "pdf": str(pdf), **pages}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    print(json.dumps(build_package(repo, args.output.resolve()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
