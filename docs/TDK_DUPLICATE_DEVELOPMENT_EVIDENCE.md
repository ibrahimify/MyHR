# Duplicate Development Evidence

Status: implementation and focused verification only. No new benchmark result,
independent validation campaign, protocol freeze, or final holdout assessment is
claimed. Issue #16 remains open until its complete acceptance criteria are met.

## Scope

`scripts/run_tdk_duplicate_development.py` uses the existing synthetic generator
and exact, normalized-exact, and weighted-similarity matchers. It does not change
their weights, normalization, blocking, corruption mechanisms, or the protocol.
The only run purpose is `duplicate_development`; there is no holdout option.

Partition roles are explicit:

| Partition | Role |
| --- | --- |
| `train` | Retained for provenance, unused by duplicate matchers |
| `validation` | Similarity threshold selection only |
| `test` | Development evaluation, never the final holdout |

Threshold selection retains the existing candidate-F1 objective and its
precision, recall, and higher-threshold tie breakers. Empty validation, no
blocked pairs, or no blocked positive pairs produces a named unavailable status
and a null threshold, not an invented fallback. Similarity predictions and
threshold-dependent metrics are then null. Candidate AP can still be reported
when its own denominator exists. The validation metric rows are calibration
diagnostics, not independent performance estimates.

## Evidence Contract

- `identities.json`: synthetic identity fields and partition, without truth tags.
- `truth.json`: parent links, independently reconstructable cluster roots,
  latent-person identifiers, and explicit hard-negative kind/anchor records.
- `pairs.json`: every unordered pair in validation and development evaluation,
  including blocking membership, all three scores, and predictions. Unblocked
  similarity scores are null. Matchers receive truth-stripped records.
- `threshold_search.json`: every observed validation candidate-score threshold,
  candidate confusion counts, objective values, selection and availability.
- `metrics.json`: six partition/method rows. Full-pair confusion counts are
  distinct from candidate-universe counts; workload uses record denominators.
- `metadata.json`: complete generator configuration, actual partition counts,
  coupled dataset/split seed, no model seed, command, Python, installed package
  versions, source revision, working-tree status, and source snapshot identity.
- `sources/`: exact relevant working-copy source and protocol snapshots. A source
  revision is not represented as clean when snapshots differ or are uncommitted.
- `manifest.json`: SHA-256 checksums for the complete expected file set.

Exact methods use the complete partition pair universe and binary scores.
Similarity uses its blocked universe. Candidate AP therefore has different
universes across methods and must not be presented as a common end-to-end AP.
End-to-end recall includes blocking misses; candidate recall does not. Rates
with zero denominators are null. F1 is computed directly from confusion counts,
and is null only when its own denominator is zero.

Resources cover identity projection, pair construction, matching and metric
calculation, but exclude generation, calibration and serialization. Exact
methods have no blocking phase. Memory is peak Python allocation, not native
process RSS. Caller-owned tracing makes the call-scoped memory measurement
unavailable (null). The auditor checks instrumentation structure and scope,
not the reproducibility of observed timings or memory values.

## Commands

After code review, a permitted development run can be produced with:

```powershell
python scripts/run_tdk_duplicate_development.py --seed 2026 --employee-count 1000
python scripts/audit_tdk_duplicate_artifact.py research_outputs/duplicate_development/<run-directory>
python -m pytest tests/test_duplicate_evidence.py -q
```

The runner reserves a new directory and refuses any existing path. It writes
the completion manifest last and rejects source/revision drift during generation.
If a failure leaves an incomplete directory,
preserve it for investigation; it is not an accepted artifact and is never
overwritten. Existing research artifacts are not read, changed, or replaced.

The separate auditor imports neither producer nor matcher. It reconstructs
identity blocking and scores, validates entity containment and link graphs,
derives threshold selection, and recomputes both confusion universes, tied-score
AP and workload from stored evidence. Score and threshold comparisons preserve
exact binary64 values; derived rate arithmetic allows numerical rounding.
Rehashed semantic tampering is covered by tests. Checksums detect corruption,
not a coordinated forgery of an entire self-consistent artifact.

## Remaining Limits

- The generator still couples dataset and partition seeds. This is recorded,
  not silently redesigned.
- Four existing duplicate variants and four hard-negative mechanisms are not
  the complete protocol coverage matrix; explicit diacritics, shared contacts
  and conflicting-field coverage remain incomplete.
- Hard negatives preferentially populate development evaluation, not validation.
- The auditor validates declared truth consistency, not real-world identity
  realism or an independently regenerated causal ledger.
- A single artifact is infrastructure evidence, not a repeated-seed result or
  an independent validation campaign. No model superiority claim follows.
- Full-suite verification and CI are deferred during this focused task. No
  commit, push, issue closure, or protocol approval is implied.

## Focused Verification - 2026-11-20

- 39 focused evidence tests passed on Python 3.13.5 in 98.51 seconds. They cover
  identity truth, candidate universes, hard negatives, calibration, missing
  values, instrumentation, tampering and source drift.
- A temporary 80-record fixture exercised the actual runner and standalone
  auditor commands, including refusal to overwrite the generated output.
  This was a software test, not new research performance evidence.
- No full suite, benchmark campaign or holdout operation was run. CI remains
  pending until the implementation is committed and reviewed.
