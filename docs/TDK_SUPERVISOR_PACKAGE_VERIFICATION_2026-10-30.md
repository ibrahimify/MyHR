# TDK Supervisor Package Verification

Date: 29 October 2026

Status: supervisor-review draft; development evidence only; draft protocol; final holdout locked.

## Frozen Source State

- Branch: `research/policy-aware-anomaly`
- Manuscript and package source revision: `94868c26a556105f9b21754b1eb066d373f7b5e6`
- Pull request: #1, open, draft, and unmerged
- Scientific blocker: Issue #10 remains open
- Holdout: not generated, inspected, scored, or unlocked
- Paid services: none enabled
- Kiro review: not run because `kiro` and `kiro-cli` are unavailable in this environment; no Kiro credits were consumed

## Deliverables

The supervisor package is stored outside the repository at `TDK/final/2026-10-30-supervisor/`. It contains only:

| File | SHA-256 |
| --- | --- |
| `README.md` | `09C5A41E3BD070269713C4F9A5374D8720A94AF09048C7993EDC4FEAF34157D1` |
| `MyHR_TDK_Paper_Draft_EN.docx` | `AE47C55ED9BA3430413C2688187582EDE97115E490AD7A3CD7FF1456F5EDCB47` |
| `MyHR_TDK_Paper_Draft_EN.pdf` | `6A4C4196B93BC1EC65C4BCA2534CFAC84D82BDC5E10FDD4C21E60EB5C0EAB663` |
| `Supervisor_Decision_Sheet.pdf` | `0F6BF77A76EC96F42D6CE7011FCC5091D57736190F3E56C4B07C0988A0AE3A34` |

This report is copied into the package after its own creation and is therefore not included in the four-file build manifest above.

## Paper Compliance

- Language: English
- Title: `MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression`
- Total PDF length: 35 pages
- Main text: 31 pages, PDF pages 3-33
- Excluded material: title and abstract pages 1-2; references and appendices pages 34-35
- Layout: A4, single column, Times New Roman 12 pt body text, single spacing, 3.5 cm margins
- Visual inspection: every PDF page and the one-page landscape decision sheet were rasterized and inspected; no overflow, clipping, broken captions, unreadable tables, or inherited Hungarian instructions were found
- Text inspection: no `TODO`, `TBD`, `PLACEHOLDER`, Markdown emphasis markers, or common Hungarian template instructions remain in the DOCX text

Microsoft Word COM produced the authoritative PDF. The document-skill LibreOffice renderer could not be used because LibreOffice is not installed. PyMuPDF rasterization was used for the complete page-by-page fallback inspection. This is a tooling limitation, not an omitted visual review.

## Software Verification

- Local full suite: 168 tests passed in 103.463 seconds
- Package regression tests: included in the 168-test run
- Python compilation: `scripts/generate_tdk_supervisor_package.py` and `tests/test_tdk_supervisor_package.py` passed `py_compile`
- Git whitespace check: clean after the final documentation correction
- GitHub CI for revision `94868c2`: passed for both the [pull-request run](https://github.com/ibrahimify/MyHR/actions/runs/40799670904) and [push run](https://github.com/ibrahimify/MyHR/actions/runs/40799666877)
- GitGuardian security check: passed for revision `94868c2`

## Artifact Verification

| Artifact | Purpose | Result |
| --- | --- | --- |
| `5f0f99d3ffe8dc9e` | canonical development run | verified; 30 scenarios; 188,676 prediction rows; `holdout_accessed=false` |
| `c5878ca7b927ccd2` | canonical validation run | verified; 30 scenarios; 188,694 prediction rows; `holdout_accessed=false` |
| `e342bd4acf39b06b` | independent development stress test | verified; 12 scenarios; 45,162 prediction rows; `holdout_accessed=false` |
| `f79f81f2c2b1` | literature metadata | 32 files verified; checksums and credential scan passed; no paid service or holdout access |
| `4b354b03c1af` | legally available literature full text | 34 files verified; checksums and credential scan passed; no paid service or holdout access |

The read-only evidence inventory found 35 artifact directories and 444 files: 29 complete artifacts and six preserved legacy or incomplete artifacts. It did not inspect holdout content, private-note contents, or private-note names.

## Citation Verification

- 18 bibliography entries and 18 provenance records passed the citation registry check
- 15 claim-evidence records were checked
- The local full-text artifact was verified
- `lit-holm-procedure` and `lit-reliability-method` remain explicitly marked metadata-only and are not presented as full-text-verified manuscript evidence
- DOI and source metadata are centralized in the bibliography and evidence ledger

## Independent Audit And Corrections

The fresh-context reviewer independently reproduced the central arithmetic and found no critical defect. Before supervisor delivery, the following findings were corrected:

1. Duplicate evidence now reports 20 duplicate-labelled records and 19 ground-truth duplicate pairs, not 20 relationships.
2. Section 6.3 now states that 24 of 30 validation scenarios have no rule-negative positives, making the stored zero-AP convention explicit.
3. The generator-detector circularity warning is labelled as a MyHR design inference rather than attributed directly to Steinbuss and Bohm.
4. Duplicate detection is identified as legacy metric-level evidence without a write-once manifest or pair-truth sidecar.
5. Literal Markdown markers were removed from the references.
6. Generated QA folders were removed from the professor-facing package after inspection.

The reviewer reproduced the independent residual AP values `0.36162347` and `0.36211577`, delta `+0.00049230`, paired interval `[-0.11725460, 0.10791824]`, and sign-flip `p=1.0`. It also reproduced 39 false alerts among 72 constructed rare-legitimate histories. These figures are retained as development diagnostics, not evidence of superiority, equivalence, or real-world prevalence.

## Remaining Scientific Boundaries

- The residual comparison cannot test the central hypothesis because the three policy-specific residual features are constant zero after deterministic filtering.
- The original generator is conceptually coupled to the policy representation.
- The stored independent artifact does not preserve the realized transition mechanism per record; the `39/39` transition attribution depends on deterministic source regeneration and is qualified accordingly.
- Duplicate evidence is preliminary and lacks the primary experiment artifact contract.
- No organizational data or blinded expert realism review is available.
- The protocol, primary endpoint, zero-positive handling, historical-policy contract, expert-review plan, and holdout design require human approval.

## Repository Actions Not Taken

No PR was marked ready or merged. No issue was closed. No branch was deleted. No protocol decision was approved. Issue-disposition and branch-cleanup commands remain proposals behind Ibrahim's approval gate.
