# Evidence Policy

## Source roles

- Crossref and OpenAlex: DOI identity, publication metadata, and citation graph metadata.
- arXiv: preprint identity and legally accessible author-submitted full text.
- Semantic Scholar: discovery, related works, citation metadata, and open-access links.
- Publisher or author-hosted full text: scientific evidence after the relevant passage, method, result, or limitation is inspected.

Cross-check disputed metadata. Preserve all source identifiers and retrieval artifacts. A DOI match verifies identity, not the paper's scientific conclusion.

## Evidence types

- `full_text`: the relevant passage or result was inspected in legally accessible full text.
- `metadata`: identity or bibliographic metadata only; it cannot support a scientific finding.
- `repository_artifact`: a MyHR code, test, experiment, or report artifact.
- `expert_judgment`: a documented human assessment; never relabel it as empirical ground truth.

## Agent boundary

The Research & Citation Specialist maintains discovery, provenance, bibliography deduplication, and claim recording. The Independent Auditor independently checks identifiers, locators, claim scope, artifact reproducibility, and conflicting evidence before recommending a research change for human review. Neither role can approve protocol decisions.
