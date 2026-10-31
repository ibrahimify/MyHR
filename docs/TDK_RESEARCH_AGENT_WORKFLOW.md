# TDK Research Agent Workflow

Status: active research governance. This document adds process controls only; it does not change the draft protocol or unlock the holdout.

## Roles

| Role | Responsibility | Write boundary |
| --- | --- | --- |
| Synthetic Data Specialist | Scenario implementation and generator tests | Assigned generator files and development artifacts only |
| Model Specialist | Baselines, representations, and model tests | Assigned model files only |
| Experiment Pipeline Specialist | Reproducible execution and artifact production | Pipeline and artifact-schema files only |
| Documentation Specialist | Synchronize methods and reports with verified implementation | Assigned documentation only |
| Independent Auditor | Re-derive results and challenge leakage, claims, citations, and reproducibility | Audit report only; read-only for implementation |
| **Research & Citation Specialist** | Discover literature, verify identifiers and full text, deduplicate the bibliography, preserve provenance, and maintain claim evidence | Bibliography, citation provenance, literature artifacts, and claim ledger only |

Agents receive disjoint tasks and write scopes. No agent can approve a protocol decision or personnel decision. Human approval remains mandatory.

## Literature Gate

Any agent using scientific literature must invoke the repository `researcher` skill and, in the same change:

1. use only free official API access or legally accessible full text;
2. add the paper once to `TDK_REFERENCES.bib`;
3. record identity and retrieval provenance in `TDK_CITATION_PROVENANCE.json`;
4. record each claim and exact evidence locator in `TDK_CLAIM_EVIDENCE_LEDGER.json` using `scripts/record_tdk_claim.py`;
5. distinguish full-text evidence from metadata-only verification;
6. run `scripts/verify_tdk_citations.py`.

After registering a paper in the bibliography and provenance registry, record each use through the append-only helper:

```powershell
python scripts/record_tdk_claim.py `
  --claim-id lit-example `
  --claim "Bounded scientific statement" `
  --document "docs/TDK_LITERATURE_REVIEW.md#section" `
  --status verified `
  --citation-key example2026 `
  --evidence-type full_text `
  --artifact-id example2026_fulltext `
  --locator "PDF pages 4-5" `
  --supports "What those pages directly establish" `
  --support-type direct
```

Recording a new claim resets the ledger to `pending_independent_audit`. A successful independent audit is bound to a fingerprint of the bibliography, provenance, and claims, so later evidence changes cannot inherit an earlier audit verdict.

The Independent Auditor must verify citation identity, source accessibility, locator accuracy, claim scope, conflicting evidence, and reproducibility before recommending a research-related change as ready for human review. An audit pass is not protocol approval.

## Free Integrations

Direct clients are used instead of third-party MCP servers because the official APIs are read-only, small, auditable, and need no additional trust boundary. Supported services are OpenAlex, Semantic Scholar, arXiv, and Crossref. Optional free keys remain environment-only. Paid endpoints are prohibited without explicit user permission.

## Required checks

```powershell
python scripts/verify_tdk_citations.py --require-local-artifact
python -m unittest tests.test_literature_workflow tests.test_citation_governance
```
