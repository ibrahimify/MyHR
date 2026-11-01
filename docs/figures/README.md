# TDK paper figures

Regenerate every figure, Graphviz source, booktabs table and the manifest with:

```powershell
python scripts/build_tdk_figures.py
```

Optional overrides:

- `MYHR_DOT_EXE` sets the path to Graphviz `dot.exe`. The default is
  `C:\WorkStation\BME\SEM 8\Project Lab\.tools\graphviz\Graphviz-12.2.1-win64\bin\dot.exe`.
- `--demo-counts PATH` sets the path to the in-app `demo_counts.json`. The
  default is `%LOCALAPPDATA%\Temp\myhr_drive\demo_counts.json`.

The script only reads `research_outputs/`. It also checks every number that
the paper draft states for these figures against the artifact CSVs. The
results go into `paper_consistency_checks` in `FIGURE_MANIFEST.json`, and any
mismatch is printed.

## Outputs

Each figure is written as `.pdf` (vector, with embedded TrueType fonts),
`.svg` and `.png` (300 dpi).

| Figure | Type | Data |
| --- | --- | --- |
| `architecture` | Graphviz (`src/architecture.dot`) | conceptual |
| `experiment_flow` | Graphviz (`src/experiment_flow.dot`) | split counts from `record_truth.csv` (4feea4508de1bb05) |
| `artifact_lifecycle` | Graphviz (`src/artifact_lifecycle.dot`) | conceptual |
| `primary_recall` | Matplotlib | 4feea4508de1bb05 `aggregate_metrics.csv`, `paired_comparisons.csv` |
| `residual_outcomes` | Matplotlib | 4feea4508de1bb05 `aggregate_metrics.csv` |
| `validation_counts` | Matplotlib | validation_c5878ca7b927ccd2 `aggregate_metrics.csv` |
| `policy_alerts` | Matplotlib | e342bd4acf39b06b, db1a15646d9e76ba, 4feea4508de1bb05 `aggregate_metrics.csv` |
| `confound_diagnostic` | Matplotlib | 8f1494e4abf2d268 `aggregate_metrics.csv`, `paired_comparisons.csv`, `scenario_metrics.csv` |

## Typography and placement

- Font: Times New Roman for Matplotlib, and for Graphviz through the
  `Times-Roman` alias, which Pango resolves to Times New Roman on Windows.
  The PDF fonts that were actually embedded are recorded in the manifest.
- Matplotlib figures are drawn at their final width of 6.0 in, with all text
  at 10 pt or larger. Place them at `width=6in` (15.2 cm).
- Graphviz diagrams use 11 pt text. Place each one at its natural width or
  wider, never narrower. The width is `layout.natural_width_in` in the
  manifest, and every diagram is at most 6.0 in wide.
- Colour is used only where it carries meaning, from the Okabe-Ito palette,
  and always together with a second cue (marker shape, hatching or a dashed
  outline). Vermillion is reserved for the human-review boundary and the
  locked holdout.

Captions for the paper are stored under `figures.<name>.caption` in
`FIGURE_MANIFEST.json`.
