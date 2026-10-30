# TDK Supervisor Package Verification

Date: 30 October 2026

Status: development evidence only; draft protocol; final holdout locked.

## Source And Tracker State

- Branch: `research/policy-aware-anomaly`
- Scientific implementation checkpoint: `1942718e69ccf34d3e628767b5316e0467f63a52`
- Pull request: #1 remains open, draft, and unmerged.
- Issue #10 remains the scientific protocol blocker.
- No holdout command was executed.

## Current Artifact

- ID: `independent_development_b866ae2aa1b4b479`
- Provenance: clean commit `1942718`; Python 3.13.5; NumPy 2.5.4; pandas 2.3.3; scikit-learn 1.9.1; SciPy 1.18.1.
- Audit: verified with complete manifest, source hashes, stored denominators, paired comparisons, and `holdout_accessed: false`.
- Data: 12 scenarios; 864 test histories; 108 anomalies; 72 rare-legitimate histories.
- Deterministic result: 63 TP, 0 FP, 45 FN; 0/72 rare-legitimate alerts.
- Primary exploratory comparison: recall delta +0.0278, 95% CI [-0.0278, +0.1019], sign-flip p=0.6875.
- Interpretation: no advantage demonstrated; no equivalence claim.

## Required Verification Commands

```powershell
python -m unittest discover tests
python scripts/verify_tdk_citations.py --require-local-artifact
python -m scripts.audit_tdk_protocol_artifact research_outputs/independent_development/independent_development_b866ae2aa1b4b479
python scripts/generate_tdk_supervisor_package.py
```

## Final Execution Record

- Manuscript/package source revision: `f1f00b38711a2225d3d05a99195dcb1ec5adb5f7`.
- Full local suite: 256 tests passed in 126.742 seconds.
- Package regression tests: 3 passed.
- Citation verification: valid; 18 bibliography entries, 18 provenance records, 15 claim records, local artifacts verified. Two claims remain explicitly metadata-only and are not presented as verified evidence.
- Artifact audit: `verified`; 12 scenarios; 46,656 prediction rows; complete truth sidecars; `holdout_accessed: false`.
- Document render: 38 total pages, introduction starts on page 3, references start on page 36, 33 pages of main text.
- Visual inspection: all 38 manuscript pages plus the one-page decision sheet inspected at page-image resolution; no clipping, overlap, unreadable figure labels, or broken tables found after the final correction pass.
- GitHub CI for source revision: push run `41003519077` passed. The matching pull-request run is recorded separately by GitHub.

### Package SHA-256

| File | SHA-256 |
| --- | --- |
| `MyHR_TDK_Paper_Draft_EN.docx` | `C3E1E9EED970F6763F57B97F138B6402E1F78C9E556350B38691C2417D4AD0F9` |
| `MyHR_TDK_Paper_Draft_EN.pdf` | `CE8BFC0013B6D7025B73AB918BAF50539D7EBE4765211F942CD26CFB734F72B7` |
| `Supervisor_Decision_Sheet.pdf` | `41063C42479EEB1E477F749FC715705F86224C9781573BF2875F98624A187653` |
| `README.md` | `66AB75CE848BD68A1DEE173F08E810412F28CFB4396D168AF50B09915959B752` |

A package should not be treated as final if a hash changes without a corresponding regenerated verification record.

Source wording and UI-lifecycle corrections made after the execution record above are intentionally not represented by those rendered files or hashes. The recorded package remains a historical supervisor draft; do not regenerate or relabel it as current until the coordinator integrates the bounded changes and starts a new verification pass.

## Claims Explicitly Excluded

- The historical `39/72` is the `deterministic_policy_rules` result in artifact `e342bd4acf39b06b`; `deterministic_rules` recorded 0/72. It is a constructed specification counterexample, not a prevalence estimate or current model-performance result, and the artifact omits employee-specific entitlement evidence and per-record realized mechanisms.
- The intermediate `8/72` false-positive interpretation is invalidated because the later generator produced contradictory histories.
- The historical constant-feature comparison is not a null, tie, or equivalence result.
- The secondary AP result is not confirmatory.
- Synthetic rates are not estimates of organizational prevalence.
- No final holdout or real-world validation result exists.

## UI Screenshot Provenance

- Figure 2 uses `docs/media/screenshots/employee.png`; the package generator copies that exact file to its temporary `myhr_ui.png` asset.
- The screenshot first entered the repository in commit `44e5f45` on 22 May 2026. No automated capture command, viewport, theme, demo-data revision, or redaction record was preserved, so it should be treated as illustrative product media rather than reproducible research evidence.
- A replacement capture should use only authorized synthetic/demo records: initialize the local demo database, launch `python main.py`, select the Employees page in the light theme at a recorded display size and scale, verify that no private data or credentials are visible, capture the application window, and record the source revision, database seed command, viewport, scale, theme, and output SHA-256 beside the image.

## Remaining Human Gates

Scenario proposals 1 and 3-6, grandfathering semantics, temporal views, expert reviewers and sampling, protocol-scale design, multiplicity, protocol freeze, holdout access, scientific conclusions, and PR merge remain human decisions.
