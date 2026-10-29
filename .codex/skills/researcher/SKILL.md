---
name: researcher
description: Discover, verify, record, and audit scientific literature for MyHR research while preserving citation provenance and claim-level evidence.
---

# Researcher

Use this skill whenever scientific literature informs a MyHR research claim, method, design recommendation, limitation, or protocol proposal.

## Required workflow

1. Read `AGENTS.md` and `docs/TDK_RESEARCH_AGENT_WORKFLOW.md` before research work.
2. Search the free official OpenAlex, Semantic Scholar, arXiv, and Crossref integrations in `src/research/literature.py`. Prefer direct official APIs; do not enable paid access.
3. Verify identity with persistent identifiers and metadata from at least one authoritative registry. For important claims, inspect legally accessible full text. Titles, abstracts, and citation counts are discovery evidence only.
4. Before using a paper, add or update its unique entry in `docs/TDK_REFERENCES.bib` and its provenance in `docs/TDK_CITATION_PROVENANCE.json`.
5. Record each literature-supported claim with `scripts/record_tdk_claim.py`. Include the claim, citation key, exact source locator, evidence type, and a bounded description of what the source supports.
6. Run `python scripts/verify_tdk_citations.py --require-local-artifact`. Resolve errors; preserve unresolved or conflicting evidence explicitly. CI may run without ignored local papers, but an Independent Auditor may not waive the strict artifact check.

Do not infer global novelty from an unsuccessful search. Do not treat metadata as proof of a scientific finding. Do not silently change the experiment protocol. The final holdout remains locked.

For the evidence schema and source-selection rules, read [references/evidence-policy.md](references/evidence-policy.md).
