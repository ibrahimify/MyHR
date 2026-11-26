# Research Evidence Preservation

This document defines the non-destructive inventory boundary for local MyHR research evidence. It does not authorize deletion, protocol changes, holdout access, or publication of private notes.

## Preservation Rules

- The final holdout remains locked. The inventory tool does not enter any path whose name contains `holdout`.
- Research artifacts are read-only inputs. The tool never deletes, renames, repairs, or rewrites them.
- Integrity verification reads `manifest.json` or release `.sha256` sidecars and computes SHA-256 over the files they explicitly list. It does not interpret experiment rows or evaluate results.
- Private notes under `docs/research/` are represented only by aggregate file count and byte size. Their filenames and contents are not emitted.
- Canonical evidence is labelled from citations in the current roadmap, methods draft, and development/validation report. A canonical label means "currently cited," not "scientifically approved."
- Empty directories, missing manifests, checksum failures, and unlisted files are findings for review. They are never cleaned automatically.

## Canonical Cited Evidence

The inventory labels these local artifacts when present:

| Label | Artifact |
| --- | --- |
| `protocol-development` | `protocol_v2_verified/development_5f0f99d3ffe8dc9e` |
| `protocol-validation` | `protocol_v2_verified/validation_c5878ca7b927ccd2` |
| `independent-development` | `independent_development/independent_development_e342bd4acf39b06b` |
| `literature-metadata` | `literature/20261017T215024Z_f79f81f2c2b1` |
| `literature-fulltext` | `literature_fulltext/20261017T215119Z_4b354b03c1af` |

These artifacts must be preserved with their manifests and documented negative or inconclusive findings. Inventory status does not replace the dedicated protocol or literature artifact auditors.

## Verified Local Inventory - 2026-10-29

The read-only inventory found 34 artifact candidates containing 434 files and
642,648,992 bytes. Twenty-eight candidates passed manifest or release-sidecar
verification. All five canonical cited artifacts were present and complete.
Six candidates require human review: four legacy/full-text runs without
manifests, one older multi-seed run without a manifest, and one empty interrupted
independent-development directory. Seven private-note files were counted only
in aggregate. No holdout-like entry was encountered or inspected.

The complete JSON snapshot is stored locally under the Git-ignored
`tmp_research_inventory/` directory. It is a maintenance aid, not a research
result or protocol decision.

## Usage

Print JSON to standard output:

```powershell
python scripts/inventory_research_evidence.py
```

Write a new inventory to an explicitly supplied Git-ignored path:

```powershell
python scripts/inventory_research_evidence.py `
  --output tmp_research_inventory/evidence-2026-10-29.json
```

The output file is created once. The command refuses tracked paths and existing files, preventing accidental replacement of a prior inventory. Use a new dated filename for each saved snapshot.

## JSON Interpretation

- `complete`: the artifact has a SHA-256 manifest or complete release checksum sidecars, every listed file matches, and no unlisted file is present.
- `integrity_problem`: a manifest is invalid, a file is missing, a checksum differs, or an extra file is present.
- `incomplete_missing_manifest`: files exist but the candidate artifact has no manifest.
- `orphan_empty`: the candidate directory contains no files.
- `review_required_opaque_entries`: the artifact contains a holdout-like or symbolic-link entry that was counted but deliberately not inspected; it cannot be classified complete.
- `canonical_artifacts`: presence and state of evidence cited by current documentation.
- `private_notes`: aggregate metadata only; absence from Git is not a backup guarantee.

The inventory reports skipped holdout-like entries and symbolic links as counts without exposing their names. A nonzero count requires human review, not automated inspection.

## Review Before Cleanup

Before any artifact is archived or removed, a human maintainer must:

1. Confirm it is not canonical, cited, or required to reproduce a documented result.
2. Verify its manifest and retain a checksum-bearing archive inventory.
3. Preserve negative and inconclusive findings and the source revision that produced them.
4. Confirm private notes have an authorized backup without committing their contents.
5. Request explicit approval before deleting any research artifact or private file.

This tool supplies evidence for that decision. It does not make the decision.
