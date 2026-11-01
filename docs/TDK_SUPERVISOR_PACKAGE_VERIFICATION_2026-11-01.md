# TDK Supervisor Package Verification, 1 November 2026 (v2)

This record covers the package at `TDK/final/2026-11-01-v2-supervisor`. Earlier
packages (`2026-10-30-supervisor`, `2026-11-01-supervisor`) and their reports
are preserved unchanged; the earlier report is
[TDK_SUPERVISOR_PACKAGE_VERIFICATION_2026-10-30.md](TDK_SUPERVISOR_PACKAGE_VERIFICATION_2026-10-30.md).

Status: development evidence only. The protocol is draft, the final holdout has
not been generated or accessed, and no human expert review or supervisor
endorsement is recorded.

## What changed since the previous package

- Manuscript prose revised for clear academic English and length (main-text
  word count reduced by about 11%); no numerical value, artifact ID, or table
  number was changed by that revision.
- Section 1.6 added: status of every commitment in the registered abstract.
  The optional user study and the confirmatory holdout evaluation are marked
  **not conducted**.
- Section 5.6 expanded: the in-app demonstration is described as a
  demonstration, not a research experiment, with its outcomes for all three
  demonstration scenarios.
- Citation corrections from `TDK_CITATION_AUDIT_2026-11-01.md` applied: full
  venue, volume, and page metadata for references 1 to 16, Holm [17] and
  Krippendorff [18] added, the partially supported [9] sentence rescoped, and
  [11] and [13] are now cited in the text.
- Ablation labels corrected to match the code: the single-feature
  representations keep the six-feature common core plus one feature; they do
  not remove one feature. Counts are unchanged.
- Figures 1, 3, 4, 5, 9, 10, 11, 12, 13, 14, and 15 are rebuilt by
  `scripts/build_tdk_figures.py` (Graphviz diagrams and Matplotlib plots, Times
  New Roman, at least 10 pt at placed size, colour only where it encodes
  information). Figure 15 (confounded 900-scenario diagnostic) is new.
- Figures 2 and 6 to 8 are fresh captures of the running application (live
  window, local demo account, synthetic data only).
- The traceability table and the threats-to-validity summary moved to
  Appendices C and D.

## Checks performed

| Check | Result |
| --- | --- |
| Paper numbers against artifact CSVs (`build_tdk_figures.py`) | 36 checks, 0 mismatches |
| Figure build reproducibility | two consecutive runs byte-identical |
| 900-scenario prediction row count | 8,019,000 data rows counted in `record_predictions.csv` |
| Demonstration outcomes (Section 5.6 table) | regenerated from `run_demo_scenario` for `ind-dev-01`, `ind-dev-07`, `ind-dev-12`; each has 24 evaluation records, 3 reviews per method, 3 injected errors |
| Citation verifier (`verify_tdk_citations.py --require-local-artifact`) | valid; 16 documented legacy text-hash mismatches; `lit-reliability-method` unverified; audit state pending independent re-audit |
| Full test suite (`python -m unittest discover -s tests`) | run on the UI-repair commit `f3cb0f2`: 329 tests OK |
| Page layout | A4, single column, Times New Roman 12 pt, single spacing, 3.0 cm / 3.5 cm margins; embedded fonts are Times New Roman and Consolas (code) only |

The generated-package record below states the exact source revision, page
counts, and file hashes. Visual inspection is recorded separately after the
rendered PDF pages were rasterized and reviewed.

## Known limitations of this package

- The independent citation re-audit has not been performed; the bibliography
  corrections were made by the citation-specialist role only.
- Krippendorff's full text could not be retrieved; the related claim stays
  unverified.
- The LNCS volume number for reference [9] is not confirmed.
- The offline audit of the 900-scenario artifact's prediction rows is
  incomplete.
- Screenshot text in Figures 2 and 6 to 8 is small at print size; the figures
  illustrate the interface and are not the source of any reported number.
