# MyHR Documentation

This index separates current research authority from historical development
records. Start with the result, then read the protocol and implementation.

## Recommended Reading Order

1. [Current research status](TDK_CURRENT_RESEARCH_STATUS.md)
2. [Frozen holdout results](results/TDK_HOLDOUT_RESULTS.md)
3. [Experiment protocol](TDK_EXPERIMENT_PROTOCOL.md)
4. [Independent scenario specification](TDK_INDEPENDENT_SCENARIO_SPEC.md)
5. [Literature review](TDK_LITERATURE_REVIEW.md)
6. [Archived research roadmap](archive/research-history/TDK_RESEARCH_ROADMAP_2026-11-25.md), only when the implementation history is needed

## Current Research Authority

| Document | Purpose |
| --- | --- |
| [TDK_CURRENT_RESEARCH_STATUS.md](TDK_CURRENT_RESEARCH_STATUS.md) | Concise final result, limitations, and evidence map |
| [results/TDK_HOLDOUT_RESULTS.md](results/TDK_HOLDOUT_RESULTS.md) | RQ1-RQ3 answers derived from the verified frozen holdout |
| [TDK_EXPERIMENT_PROTOCOL.md](TDK_EXPERIMENT_PROTOCOL.md) | Frozen hypotheses, endpoints, scenario matrix, and analysis boundary |
| [TDK_INDEPENDENT_SCENARIO_SPEC.md](TDK_INDEPENDENT_SCENARIO_SPEC.md) | Synthetic populations, policies, errors, and lawful rare patterns |
| [TDK_LITERATURE_REVIEW.md](TDK_LITERATURE_REVIEW.md) | Verified scientific background and evidence limits |
| [TDK_REFERENCES.bib](TDK_REFERENCES.bib) | Deduplicated bibliography |
| [TDK_CITATION_PROVENANCE.json](TDK_CITATION_PROVENANCE.json) | Identifier and retrieval provenance |
| [TDK_CLAIM_EVIDENCE_LEDGER.json](TDK_CLAIM_EVIDENCE_LEDGER.json) | Claim-to-source evidence mapping |

## Results And Reproduction

| Location | Contents |
| --- | --- |
| [tables/](tables/README.md) | Primary, secondary, workflow, robustness, and model-sensitivity CSV tables |
| [figures/](figures/README.md) | Publication figures in PNG, PDF, and SVG formats |
| [results/holdout_report_manifest.json](results/holdout_report_manifest.json) | Source and output checksums for the final report |
| [TDK_RESEARCH_VERIFICATION.md](TDK_RESEARCH_VERIFICATION.md) | Verification commands and artifact-handling rules |
| [Archived research roadmap](archive/research-history/TDK_RESEARCH_ROADMAP_2026-11-25.md) | Detailed chronology, failures, repairs, and retained negative findings |

The large immutable artifact, one-time ledger, and authorization evidence remain
outside Git. The repository contains the code, compact derived tables, figures,
checksums, and scientific interpretation required to verify the reported result.

## Manuscripts

| Document | Status |
| --- | --- |
| [paper/MyHR_TDK_Paper_Revised_2026-11-25.pdf](paper/MyHR_TDK_Paper_Revised_2026-11-25.pdf) | Revised manuscript PDF |
| [paper/MyHR_TDK_Paper_Revised_2026-11-25.docx](paper/MyHR_TDK_Paper_Revised_2026-11-25.docx) | Editable revised manuscript |
| [TDK_PAPER_DRAFT.md](TDK_PAPER_DRAFT.md) | Editable revised manuscript source |
| Tag `tdk-2026-submission` | Immutable submitted 2026 version |

The submitted paper is preserved for academic history. It predates the frozen
holdout and should not be used as the current result summary.

## Engineering Documentation

| Document | Purpose |
| --- | --- |
| [UI_RULES.md](UI_RULES.md) | Desktop interface conventions |
| [QA_CHECKLIST.md](QA_CHECKLIST.md) | Manual release and demonstration checks |
| [ARCHITECTURE_ROADMAP.md](ARCHITECTURE_ROADMAP.md) | Application architecture priorities |
| [SCOPE_AUDIT.md](SCOPE_AUDIT.md) | Thesis, research, and packaging boundaries |
| [LICENSING_AND_IP.md](LICENSING_AND_IP.md) | Licensing and intellectual-property status |
| [guides/MyHR_User_Guide.docx](guides/MyHR_User_Guide.docx) | User guide |
| [guides/MyHR_Developer_Guide.docx](guides/MyHR_Developer_Guide.docx) | Developer guide |

## Historical Evidence

`archive/` preserves superseded findings and corrective history. Its contents
are not current scientific claims. The archived roadmap explains which
defects were found, how they were repaired, and why invalid or inconclusive
results remain visible rather than being silently removed.
