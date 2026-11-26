"""Build the revised TDK manuscript package from the verified research record."""

from __future__ import annotations

import argparse
from hashlib import sha256
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
PUBLIC_FIGURE_NAMES = {
    "holdout_primary_comparison": "primary_comparison",
    "holdout_model_sensitivity": "model_sensitivity",
    "holdout_robustness": "robustness",
}
RESULT_TABLES = (
    "holdout_primary_results.csv",
    "holdout_endpoint_contrasts.csv",
    "holdout_complete_workflow.csv",
    "holdout_model_sensitivity.csv",
    "holdout_robustness.csv",
)


def build_package(repo: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    docx = output / "MyHR_TDK_Paper.docx"
    pdf = output / "MyHR_TDK_Paper.pdf"
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
                shutil.copy2(
                    source,
                    output / "figures" / f"{PUBLIC_FIGURE_NAMES[stem]}{suffix}",
                )
    for name in RESULT_TABLES:
        shutil.copy2(repo / "docs" / "tables" / name, output / "tables" / name)

    (output / "README.md").write_text(
        "\n".join(
            (
                "# MyHR TDK Research Package",
                "",
                "This package contains the revised manuscript and the verified tables and figures used for its final synthetic evaluation.",
                "",
                "## Reading Order",
                "",
                "1. Read the abstract and research questions in `MyHR_TDK_Paper.pdf`.",
                "2. Read Sections 4 and 6 for the method and results.",
                "3. Read Sections 7 and 8 for limits and conclusions.",
                "4. Inspect the three publication figures in `figures/`.",
                "5. Use the CSV files in `tables/` to verify reported denominators and comparisons.",
                "",
                "## Main Finding",
                "",
                "At equal review capacity, policy-aware Isolation Forest improved scenario-mean recall by 6.81 percentage points in the protected synthetic evaluation. The rare-legitimate false-alert result remained inconclusive, and performance on real organizational data has not been established.",
                "",
                "`SHA256SUMS.txt` records the checksum of every delivered file. Technical provenance remains in the repository report manifest.",
                "",
            )
        ),
        encoding="utf-8",
        newline="\n",
    )
    page_report.unlink(missing_ok=True)
    checksum_path = output / "SHA256SUMS.txt"
    files = sorted(
        path for path in output.rglob("*")
        if path.is_file() and path != checksum_path
    )
    checksum_path.write_text(
        "".join(
            f"{sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
        newline="\n",
    )
    return {"docx": str(docx), "pdf": str(pdf), **pages}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    result = build_package(repo, args.output.resolve())
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
