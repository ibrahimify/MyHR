# TDK Citation Audit - 2026-10-29

Role: Research & Citation Specialist

Scope: all 18 entries in `TDK_REFERENCES.bib`, their preserved literature artifacts, identifiers, use in the literature review, and claim-level traceability. This audit did not access the experimental holdout or change the protocol.

## Outcome

- 18 unique bibliography keys and 18 unique paper identities.
- 16 legally accessible full texts preserved in the existing checksummed artifact.
- 15 bounded claim records now map literature statements to source locators.
- No duplicate bibliography entry was found.
- OpenAlex, arXiv, and Crossref passed live real-query checks on 2026-10-29.
- Semantic Scholar client tests pass, but anonymous live access returned HTTP 429. A free API key remains optional setup; no paid service was enabled.

## Corrections Applied

1. Added Kevin Kammler and Emmanuel Mueller to the Rochner et al. author list.
2. Replaced arXiv DOI aliases with formal publication DOIs for ADBench, Vaska et al., Hansen et al., and Fourure et al.; arXiv identifiers remain recorded in provenance.
3. Replaced the non-resolving `10.2307/4615733` DOI-like value with the stable JSTOR URL for Holm (1979).
4. Recorded that Li et al. was online in 2023 and assigned to a 2024 journal issue; the bibliography intentionally uses the issue year.
5. Recorded the stale local artifact id `pei2024_dense_blocking`; it refers to the correctly identified Wang et al. paper and was not renamed because research artifacts are preserved write-once.
6. Corrected a historical checksum-authority mismatch. The existing artifact manifest correctly hashes the stored text files, while all 16 per-paper `text_sha256` fields were calculated before Windows newline translation. The write-once artifact was not modified. The limitation is machine-readable in the provenance registry, the strict verifier reports all 16 mismatches, and future artifacts hash the bytes after writing.

## Evidence Gaps Preserved

- `lit-holm-procedure`: the paper identity is verified, but inspected full text is not preserved. The methodological claim remains unverified.
- `lit-reliability-method`: the Krippendorff paper identity and DOI are verified, but inspected full text is not preserved. The detailed annotation-reliability recommendation remains unverified.
- The use of context-dependent anomaly research to motivate MyHR policy residuals is recorded as an inference, not a direct result of Vaska et al.
- The locked-evaluation recommendation is recorded as an inference from the benchmark critique, not a direct prescription from Rochner et al.
- Sign-flip exchangeability and scenario-bootstrap assumptions still need dedicated methodological sources before they support final inferential claims.

## Reproducibility

Run:

```powershell
python scripts/verify_tdk_citations.py --require-local-artifact
python -m unittest tests.test_literature_workflow tests.test_citation_governance
```

The verifier checks bibliography/provenance parity, canonical identifier uniqueness, DOI agreement, source provenance, claim keys, evidence types, support labels, and full-text review status. It reports unresolved claims rather than deleting or disguising them.
