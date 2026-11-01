# TDK Citation Audit, 1 November 2026

Role: Research & Citation Specialist (sixth research role). This audit verifies identifiers, metadata, and claim support. It does not approve protocol decisions, scientific conclusions, or the paper. The final holdout was not touched.

Earlier audits: [TDK_CITATION_AUDIT_2026-10-29.md](TDK_CITATION_AUDIT_2026-10-29.md) and [TDK_CITATION_INDEPENDENT_AUDIT_2026-10-29.md](TDK_CITATION_INDEPENDENT_AUDIT_2026-10-29.md). Both are preserved unchanged.

## Scope and method

- Paper audited: `docs/TDK_PAPER_DRAFT.md` (read-only), first snapshot SHA-256 `D22B42D9F566AB224B86011BADD1337849589970155D373541518753BFE6FA18`, re-checked against snapshot `387CA10B74135465F0AC33DC63FE4B7FF69B049E8D36A07EC788AFF7040D4BA2`. Another agent is rewriting the prose, so the old-text strings below are quoted from the second snapshot and must be re-matched before applying changes. Between the snapshots some sentences were merged, but all 15 citation uses and their claims were kept.
- Entries checked: the 16 entries of `## References` and all 18 entries of `docs/TDK_REFERENCES.bib` (the two extra bib entries are Holm 1979 and Krippendorff 2004).
- Metadata sources: Crossref `https://api.crossref.org/works/<DOI>`; DataCite `https://api.datacite.org/dois/<DOI>` for arXiv DOIs (Crossref returns 404 for `10.48550/*` because arXiv registers with DataCite); arXiv API; JMLR landing page; the paper's own title page in the preserved full text. OpenAlex was used only for discovery (checking for later peer-reviewed versions of arXiv-only items); none was found.
- Claim support: every in-text marker was extracted programmatically (15 citation uses). Each was checked against the preserved full text in `research_outputs/literature_fulltext/20261017T215119Z_4b354b03c1af` (manifest checksums verified by the repository verifier). Locators are PDF page numbers of the preserved file.
- Retrieval date for all checks: 2026-11-01.

## Reference metadata

Status meanings: **verified** = bib entry matches the registry with no change; **corrected** = bib entry changed in this audit; **unresolved** = a field could not be verified.

| # | Key | Bib status | DOI / identifier | Verification source | Notes, including paper reference-list mismatches |
|---|---|---|---|---|---|
| 1 | liu2008isolation | verified | 10.1109/ICDM.2008.17 | [Crossref](https://api.crossref.org/works/10.1109/ICDM.2008.17) | Paper venue reads "Proceedings of the 2008 IEEE International Conference on Data Mining"; registered title is "2008 Eighth IEEE International Conference on Data Mining", pp. 413-422. Paper omits pages. |
| 2 | liu2012isolation | corrected | 10.1145/2133360.2133363 | [Crossref](https://api.crossref.org/works/10.1145/2133360.2133363) | Bib: pages 1-39 added. Paper omits vol. 6, no. 1, pp. 1-39. |
| 3 | han2022adbench | corrected | 10.52202/068431-2329; arXiv 2206.09426 | [Crossref](https://api.crossref.org/works/10.52202/068431-2329); paper title page (local full text, PDF page 1) | Bib author "Mingqi Jiang" corrected to "Minqi Jiang" (Crossref and the paper's author line; the arXiv metadata record carries the misspelling). Volume 35 and pp. 32142-32159 added. The paper's initial "M. Jiang" is unaffected. Paper omits volume and pages. |
| 4 | li2024survey | verified | 10.1145/3609333 | [Crossref](https://api.crossref.org/works/10.1145/3609333) | Online 2023-09-06; issue 2024-01 (vol. 18, no. 1, pp. 1-54). 2024 issue year retained. Paper omits volume, issue, pages. |
| 5 | carletti2023diffi | verified | 10.1016/j.engappai.2022.105730 | [Crossref](https://api.crossref.org/works/10.1016/j.engappai.2022.105730) | Vol. 119, article 105730. The arXiv title differs ("...Depth-based Isolation Forest Feature Importance"); the bib correctly uses the journal title. Paper omits volume and article number. |
| 6 | vaska2022context | corrected | 10.1109/CASE49997.2022.9926631; arXiv 2203.09354 | [Crossref](https://api.crossref.org/works/10.1109/CASE49997.2022.9926631) | Bib type changed misc to inproceedings; booktitle "2022 IEEE 18th International Conference on Automation Science and Engineering (CASE)" and pp. 2020-2027 added. Paper reference has no venue. |
| 7 | steinbuss2021benchmarking | corrected | 10.1145/3441453 | [Crossref](https://api.crossref.org/works/10.1145/3441453) | Bib: pages 1-20 added. Paper omits vol. 15, no. 4, pp. 1-20. In-text name "Bohm" lacks the umlaut. |
| 8 | hansen2023synthetic | corrected | 10.52202/075280-1466; arXiv 2310.16981 | [Crossref](https://api.crossref.org/works/10.52202/075280-1466) | Bib type changed misc to inproceedings; NeurIPS vol. 36, pp. 33781-33823 added. Paper reference has no venue. |
| 9 | fourure2021biased | corrected | 10.1007/978-3-030-86514-6_1; arXiv 2106.16020 | [Crossref](https://api.crossref.org/works/10.1007/978-3-030-86514-6_1) | Bib booktitle completed ("... Applied Data Science Track"), LNCS series and pp. 3-18 added. **Unresolved field:** the LNCS volume number is not in the Crossref record and the Springer page redirected to a login; it is omitted rather than guessed. |
| 10 | saito2015precision | verified | 10.1371/journal.pone.0118432 | [Crossref](https://api.crossref.org/works/10.1371/journal.pone.0118432) | Paper omits vol. 10, no. 3, e0118432. |
| 11 | demsar2006statistical | corrected | no DOI; JMLR stable URL | [JMLR landing page](https://www.jmlr.org/papers/v7/demsar06a.html) | Page states 7(1):1-30, 2006; bib issue number 1 added. Paper omits volume and pages. **Not cited anywhere in the paper text.** |
| 12 | wang2024universal | verified | 10.48550/arXiv.2404.14831 | [DataCite](https://api.datacite.org/dois/10.48550/arxiv.2404.14831); arXiv API | Six authors confirmed. arXiv preprint only; paper should say so. Provenance keeps the stale artifact id `pei2024_dense_blocking` (immutable artifact, already documented). |
| 13 | sorbo2024metricmaze | verified | 10.1007/s10618-023-00988-8 | [Crossref](https://api.crossref.org/works/10.1007/s10618-023-00988-8) | Online 2023-11-18; issue 2024-05 (vol. 38, no. 3, pp. 1027-1068). **Not cited anywhere in the paper text.** |
| 14 | rochner2025rethink | verified | 10.48550/arXiv.2507.15584 | [DataCite](https://api.datacite.org/dois/10.48550/arxiv.2507.15584); arXiv API | Six authors confirmed. arXiv preprint only. |
| 15 | neelamegam2026bitemporal | verified | 10.1007/s42488-026-00162-x | [Crossref](https://api.crossref.org/works/10.1007/s42488-026-00162-x) | J. Data, Inf. Manag. 8(2):71-96. Crossref drops diacritics ("Ozturkoglu"); bib keeps publisher-PDF spelling. Paper reference has no venue. |
| 16 | deng2026hilad | verified | 10.1145/3778167; arXiv 2405.03234 | [Crossref](https://api.crossref.org/works/10.1145/3778167) | ACM TiiS 16(2):1-23; online 2026-03-13. Paper reference has no venue. |
| bib only | holm1979multiple | verified (metadata) | no DOI; [JSTOR 4615733](https://www.jstor.org/stable/4615733) | Prior JSTOR check (2026-10-29); [Crossref search](https://api.crossref.org/works?query.bibliographic=Holm%20A%20Simple%20Sequentially%20Rejective%20Multiple%20Test%20Procedure%201979&rows=5) returns no DOI; reference list of Demšar 2006 (local full text, PDF page 29) | JSTOR returned a client challenge today, so the stable page was not re-read. Journal, volume 6, pages 65-70, year 1979 corroborated by Demšar's bibliography. Named in paper Sections 3 and 5.3 but absent from the reference list. |
| bib only | krippendorff2004reliability | verified (metadata) | 10.1111/j.1468-2958.2004.tb00738.x | [Crossref](https://api.crossref.org/works/10.1111/j.1468-2958.2004.tb00738.x) | Crossref splits title and subtitle; bib title is correct. Named in paper Section 5.3 but absent from the reference list. Author copy listed at `repository.upenn.edu/asc_papers/242`; automated download returned an HTML bot challenge, so full text is still uninspected. |

No duplicate keys, DOIs, or arXiv identifiers were found.

## Citation uses

Locators are PDF pages of the preserved full text. Paraphrases are short and not quotations.

| # | Paper section | Claim (paraphrase) | Ref | Support | Locator and what the source says |
|---|---|---|---|---|---|
| 1 | 1.2 Problem Statement | Isolation Forest scores observations by how quickly random recursive partitions isolate them (earlier wording: shorter paths give higher scores). | [1,2] | supported | [1] PDF pages 2-4: random partitioning gives anomalies shorter paths; score s derived from expected path length. [2] PDF pages 2-3: anomalies have short average path lengths on iTrees. |
| 2 | 2.1 | Trees choose a random feature and split value; expected path length across trees becomes the anomaly score. | [1] | supported | PDF pages 2-4 and 6: random attribute and split value selection; anomaly score from E(h(x)) over the forest. |
| 3 | 2.1 | The later formulation analyses the method more broadly and explains its computational behavior. | [2] | supported | PDF pages 1-3 and 10-11: subsampling, linear time complexity, training and evaluation complexity, swamping and masking. |
| 4 | 2.1 | ADBench: performance varies with dataset, supervision assumptions, and method family. | [3] | supported | PDF page 1: no unsupervised method statistically better than others; supervision levels studied. PDF pages 7-8: critical-difference results; suitability depends on anomaly type; no universal winner. |
| 5 | 2.2 | Context-dependent anomalies are unusual only in a situation; knowledge-based context changes interpretation. | [6] | supported | PDF page 1: framework uses a semantic knowledge base for context; example of an object normal in one room type and odd in another. PDF pages 2-4: method. |
| 6 | 2.3 | XAD separates global understanding of a detector from local evidence for an alert. | [4] | supported | PDF page 8: global explanations describe whole-model logic; local explanations explain individual decisions. |
| 7 | 2.3 | DIFFI derives Isolation Forest feature importance from tree depth and feature use. | [5] | supported | PDF page 5: global and local DIFFI importances. PDF pages 10-14: importance built from leaf depth and the induced imbalance at nodes split on each feature. "Feature use" is a fair simplification. |
| 8 | 2.4 | Under severe imbalance, ROC can look favorable while queue precision is poor; PR analysis is often more informative. | [10] | supported | PDF page 1: ROC interpretability can deceive on imbalanced data. PDF page 12 onward: simulations show PRC more informative than ROC on imbalanced data. Source is about binary classifiers, consistent with the claim. |
| 9 | 2.4 | Biased partitioning, thresholds chosen on test labels, favorable seed selection, and contamination from known test prevalence can make a detector look stronger. | [9] | **partially supported** | PDF pages 1-2: train-test split and contamination-rate choices change test contamination, threshold, F1 and AVPR. PDF page 11, Table 1: thresholds optimized on the test set and smaller test splits raise F1/AVPR. **Favorable seed selection is not discussed in the paper** (no occurrence in the full text). |
| 10 | 2.4 | Conclusions may depend on a narrow evaluation pipeline. | [14] | supported | PDF page 6: unclear whether gains come from the algorithm or from other pipeline choices. PDF page 9: designing on a single pipeline with ground-truth labels risks overfitting. |
| 11 | 2.5 | Steinbuss and Böhm show the importance of varying synthetic outlier characteristics and data domains. | [7] | supported | PDF pages 1-2: synthetic outliers with insightful characteristics; benchmark must cover many data domains. |
| 12 | 2.5 | Data-centric synthetic tabular work emphasizes downstream behavior and multiple profiles over a single similarity score. | [8] | supported | PDF pages 1-2 (Figure 1): data-centric profiles track downstream performance better than statistical-fidelity measures; divergence metrics alone tell only part of the story. |
| 13 | 2.6 | Bitemporal research calls these valid time and transaction time. | [15] | supported | PDF pages 1-2: valid time (true in the real world) and transaction time (recorded in the database); history preserved through controlled updates. |
| 14 | 2.7 | HITL anomaly detection treats expert validation as part of the workflow, not model output as truth. | [16] | supported | PDF page 2: users validate model decisions and give corrective feedback in a loop; explanation alone judged insufficient. |
| 15 | 2.7 | Dense-blocking research stresses candidate workload and blocking recall. | [12] | supported | PDF page 2: blocking generates candidate pairs under a recall or comparison budget. PDF page 5: pair completeness (recall) and pair quality. |

Totals: 15 citation uses; 14 supported, 1 partially supported, 0 abstract-only, 0 unverified, 0 not supported.

Uncited or unlisted works:

- [11] Demšar and [13] Sørbø and Ruocco appear in the reference list but have no in-text marker.
- Holm (Section 4.11 "Holm's step-down adjustment", Section 5.3, Section 7.10, Appendix B) and Krippendorff (Section 5.3) are named in the text but are not in the reference list.

## Ledger and provenance changes made

`docs/TDK_REFERENCES.bib` (keys unchanged; no entries merged or removed):

1. `liu2012isolation`: added `pages = {1--39}`.
2. `han2022adbench`: `Jiang, Mingqi` changed to `Jiang, Minqi`; added `volume = {35}`, `pages = {32142--32159}`.
3. `vaska2022context`: `@misc` changed to `@inproceedings`; added CASE 2022 `booktitle` and `pages = {2020--2027}`.
4. `steinbuss2021benchmarking`: added `pages = {1--20}`.
5. `hansen2023synthetic`: `@misc` changed to `@inproceedings`; added NeurIPS `booktitle`, `volume = {36}`, `pages = {33781--33823}`.
6. `fourure2021biased`: booktitle extended with "Applied Data Science Track"; added `series`, `publisher`, `pages = {3--18}`.
7. `demsar2006statistical`: added `number = {1}`.

`docs/TDK_CITATION_PROVENANCE.json`:

- Every record gained a dated 2026-11-01 source (`crossref`, `datacite`, `publisher`, or `crossref_search` for Holm), plus `metadata_rechecked_at` and `metadata_recheck_report`. Records with findings carry a `metadata_recheck_note`. A top-level `metadata_recheck` block was added. No existing source, DOI, status or artifact reference was removed.

`docs/TDK_CLAIM_EVIDENCE_LEDGER.json`:

- `lit-holm-procedure`: status changed from `unverified` to `verified`. The new evidence is a secondary full-text account in Demšar 2006 (artifact `demsar2006_statistical_comparisons`, PDF pages 12-13), which describes Holm's step-down procedure as a family-wise error control method. The Holm metadata item is kept and explicitly says Holm's own full text was not inspected.
- `lit-reliability-method`: still `unverified`. The note records the inaccessible author copy.
- `audit_state`: changed from `independent_audit_passed` to `pending_independent_audit`. Any edit to these files invalidates the 2026-10-29 fingerprint, and this role cannot sign the independent audit. The previous audit status, date, report, and fingerprint are kept under `previous_audit`.

## Verifier result

Command: `python scripts/verify_tdk_citations.py --require-local-artifact`.

| | Before | After |
|---|---|---|
| valid | true | true |
| bibliography entries / provenance records / claims | 18 / 18 / 15 | 18 / 18 / 15 |
| local artifact verified | true | true |
| legacy text-hash mismatches | 16 | 16 |
| unverified claims | `lit-holm-procedure`, `lit-reliability-method` | `lit-reliability-method` |
| audit state | independent_audit_passed (2026-10-29) | pending_independent_audit |

`tests/test_citation_governance.py`: 12 passed after the changes.

The 16 legacy text-hash mismatches are not fixable here. The stored `text_sha256` values in the immutable `papers.json` were computed before newline translation. The manifest hashes, which the verifier checks, match every stored file. The limitation is already documented under `known_artifact_limitations`. Fixing it would mean rewriting `research_outputs/`, which is prohibited.

Remaining open items for a human or the Independent Auditor:

1. Re-run the Independent Auditor check and, if it passes, record a new fingerprint.
2. Obtain and preserve, in a new literature artifact, legal full text for Krippendorff 2004 (UPenn ScholarlyCommons author copy) and ideally Holm 1979 (JSTOR). Until then `lit-reliability-method` stays unverified.
3. Verify the LNCS volume number for Fourure et al. from the Springer book page if the paper's style requires it.

## Required paper changes (for the coordinator)

Apply after re-matching the text, because the prose is being rewritten. The reference-list items assume the current numbering is kept.

### Reference list

R1. `[1] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation Forest,” in Proceedings of the 2008 IEEE International Conference on Data Mining, 2008. DOI: 10.1109/ICDM.2008.17.`
-> `[1] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation Forest,” in 2008 Eighth IEEE International Conference on Data Mining, 2008, pp. 413–422. DOI: 10.1109/ICDM.2008.17.`

R2. `[2] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation-Based Anomaly Detection,” ACM Transactions on Knowledge Discovery from Data, 2012. DOI: 10.1145/2133360.2133363.`
-> `[2] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation-Based Anomaly Detection,” ACM Transactions on Knowledge Discovery from Data, vol. 6, no. 1, pp. 1–39, 2012. DOI: 10.1145/2133360.2133363.`

R3. `[3] S. Han, X. Hu, H. Huang, M. Jiang, and Y. Zhao, “ADBench: Anomaly Detection Benchmark,” Advances in Neural Information Processing Systems, 2022. DOI: 10.52202/068431-2329.`
-> `[3] S. Han, X. Hu, H. Huang, M. Jiang, and Y. Zhao, “ADBench: Anomaly Detection Benchmark,” in Advances in Neural Information Processing Systems 35, 2022, pp. 32142–32159. DOI: 10.52202/068431-2329.`

R4. `[4] Z. Li, Y. Zhu, and M. van Leeuwen, “A Survey on Explainable Anomaly Detection,” ACM Transactions on Knowledge Discovery from Data, 2024. DOI: 10.1145/3609333.`
-> `[4] Z. Li, Y. Zhu, and M. van Leeuwen, “A Survey on Explainable Anomaly Detection,” ACM Transactions on Knowledge Discovery from Data, vol. 18, no. 1, pp. 1–54, 2024. DOI: 10.1145/3609333.`

R5. `[5] M. Carletti, M. Terzi, and G. A. Susto, “Interpretable Anomaly Detection with DIFFI: Depth-Based Feature Importance of Isolation Forest,” Engineering Applications of Artificial Intelligence, 2023. DOI: 10.1016/j.engappai.2022.105730.`
-> `[5] M. Carletti, M. Terzi, and G. A. Susto, “Interpretable Anomaly Detection with DIFFI: Depth-Based Feature Importance of Isolation Forest,” Engineering Applications of Artificial Intelligence, vol. 119, art. 105730, 2023. DOI: 10.1016/j.engappai.2022.105730.`

R6. `[6] N. Vaska, K. Leahy, and V. Helus, “Context-Dependent Anomaly Detection with Knowledge Graph Embedding Models,” 2022. DOI: 10.1109/CASE49997.2022.9926631.`
-> `[6] N. Vaska, K. Leahy, and V. Helus, “Context-Dependent Anomaly Detection with Knowledge Graph Embedding Models,” in 2022 IEEE 18th International Conference on Automation Science and Engineering (CASE), 2022, pp. 2020–2027. DOI: 10.1109/CASE49997.2022.9926631.`

R7. `[7] G. Steinbuss and K. Böhm, “Benchmarking Unsupervised Outlier Detection with Realistic Synthetic Data,” ACM Transactions on Knowledge Discovery from Data, 2021. DOI: 10.1145/3441453.`
-> `[7] G. Steinbuss and K. Böhm, “Benchmarking Unsupervised Outlier Detection with Realistic Synthetic Data,” ACM Transactions on Knowledge Discovery from Data, vol. 15, no. 4, pp. 1–20, 2021. DOI: 10.1145/3441453.`

R8. `[8] L. Hansen, N. Seedat, M. van der Schaar, and A. Petrovic, “Reimagining Synthetic Tabular Data Generation through Data-Centric AI: A Comprehensive Benchmark,” 2023. DOI: 10.52202/075280-1466.`
-> `[8] L. Hansen, N. Seedat, M. van der Schaar, and A. Petrovic, “Reimagining Synthetic Tabular Data Generation through Data-Centric AI: A Comprehensive Benchmark,” in Advances in Neural Information Processing Systems 36, 2023, pp. 33781–33823. DOI: 10.52202/075280-1466.`

R9. `[9] D. Fourure, M. U. Javaid, N. Posocco, and S. Tihon, “Anomaly Detection: How to Artificially Increase Your F1-Score with a Biased Evaluation Protocol,” in Machine Learning and Knowledge Discovery in Databases, 2021. DOI: 10.1007/978-3-030-86514-6_1.`
-> `[9] D. Fourure, M. U. Javaid, N. Posocco, and S. Tihon, “Anomaly Detection: How to Artificially Increase Your F1-Score with a Biased Evaluation Protocol,” in Machine Learning and Knowledge Discovery in Databases. Applied Data Science Track, Lecture Notes in Computer Science, Springer, 2021, pp. 3–18. DOI: 10.1007/978-3-030-86514-6_1.`

R10. `[10] T. Saito and M. Rehmsmeier, “The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets,” PLOS ONE, 2015. DOI: 10.1371/journal.pone.0118432.`
-> `[10] T. Saito and M. Rehmsmeier, “The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets,” PLOS ONE, vol. 10, no. 3, e0118432, 2015. DOI: 10.1371/journal.pone.0118432.`

R11. `[11] J. Demšar, “Statistical Comparisons of Classifiers over Multiple Data Sets,” Journal of Machine Learning Research, 2006.`
-> `[11] J. Demšar, “Statistical Comparisons of Classifiers over Multiple Data Sets,” Journal of Machine Learning Research, vol. 7, pp. 1–30, 2006. Available: https://www.jmlr.org/papers/v7/demsar06a.html.`
(Keep only if T3 is applied; otherwise [11] is an uncited reference and should be removed.)

R12. `[12] T. Wang et al., “Towards Universal Dense Blocking for Entity Resolution,” 2024. DOI: 10.48550/arXiv.2404.14831.`
-> `[12] T. Wang, H. Lin, X. Han, X. Chen, B. Cao, and L. Sun, “Towards Universal Dense Blocking for Entity Resolution,” arXiv preprint arXiv:2404.14831, 2024. DOI: 10.48550/arXiv.2404.14831.`

R13. `[13] S. Sørbø and M. Ruocco, “Navigating the Metric Maze: A Taxonomy of Evaluation Metrics for Anomaly Detection in Time Series,” Data Mining and Knowledge Discovery, 2024. DOI: 10.1007/s10618-023-00988-8.`
-> `[13] S. Sørbø and M. Ruocco, “Navigating the Metric Maze: A Taxonomy of Evaluation Metrics for Anomaly Detection in Time Series,” Data Mining and Knowledge Discovery, vol. 38, no. 3, pp. 1027–1068, 2024. DOI: 10.1007/s10618-023-00988-8.`
(Keep only if T4 is applied; otherwise remove as uncited.)

R14. `[14] P. Röchner et al., “We Need to Rethink Benchmarking in Anomaly Detection,” 2025. DOI: 10.48550/arXiv.2507.15584.`
-> `[14] P. Röchner, S. Klüttermann, K. Kammler, F. Rothlauf, E. Müller, and D. Schlör, “We Need to Rethink Benchmarking in Anomaly Detection,” arXiv preprint arXiv:2507.15584, 2025. DOI: 10.48550/arXiv.2507.15584.`

R15. `[15] G. Neelamegam, J. Bhogal, P. Samimi, and Ö. Öztürkoğlu, “Comprehensive Insights into Bitemporal Databases: A PRISMA-Guided Systematic Literature Review,” 2026. DOI: 10.1007/s42488-026-00162-x.`
-> `[15] G. Neelamegam, J. Bhogal, P. Samimi, and Ö. Öztürkoğlu, “Comprehensive Insights into Bitemporal Databases: A PRISMA-Guided Systematic Literature Review,” Journal of Data, Information and Management, vol. 8, no. 2, pp. 71–96, 2026. DOI: 10.1007/s42488-026-00162-x.`

R16. `[16] Z. Deng, X. Xuan, K.-L. Ma, and Z. Kong, “A Reliable Framework for Human-in-the-Loop Anomaly Detection in Time Series,” 2026. DOI: 10.1145/3778167.`
-> `[16] Z. Deng, X. Xuan, K.-L. Ma, and Z. Kong, “A Reliable Framework for Human-in-the-Loop Anomaly Detection in Time Series,” ACM Transactions on Interactive Intelligent Systems, vol. 16, no. 2, pp. 1–23, 2026. DOI: 10.1145/3778167.`

R17 (add, required by T3 and T5). `[17] S. Holm, “A Simple Sequentially Rejective Multiple Test Procedure,” Scandinavian Journal of Statistics, vol. 6, no. 2, pp. 65–70, 1979. Available: https://www.jstor.org/stable/4615733.`

R18 (add, required by T5). `[18] K. Krippendorff, “Reliability in Content Analysis: Some Common Misconceptions and Recommendations,” Human Communication Research, vol. 30, no. 3, pp. 411–433, 2004. DOI: 10.1111/j.1468-2958.2004.tb00738.x.`

### In-text claims

T1 (Section 2.4, partially supported claim).
`Biased partitioning, thresholds chosen on test labels, favorable seed selection, and contamination settings derived from known test prevalence can all make a detector look stronger than it is [9], and conclusions may depend on a narrow evaluation pipeline [14].`
-> `Train-test partitioning choices, thresholds tuned on the test set, and contamination rates taken from the test data can all inflate F1 and average precision [9], and conclusions may depend on a narrow evaluation pipeline [14]. Selecting favorable seeds is a related risk, which MyHR addresses by fixing and reporting all seeds.`

T2 (Section 2.5, name spelling).
`Steinbuss and Bohm show` -> `Steinbuss and Böhm show`

T3 (Section 4.11, uncited method and uncited [11]).
`with Holm's step-down adjustment across these three two-sided tests.` -> `with Holm's step-down adjustment [11,17] across these three two-sided tests.`
(Demšar [11], PDF pages 12-13, describes the procedure in full text; Holm [17] is the metadata-verified original.)

T4 (Section 2.4, uncited [13]).
`Threshold metrics are still needed because HR teams review a finite number of cases; Sections 4.9 and 4.10 define the operating points and measures used here.`
-> `Threshold metrics are still needed because HR teams review a finite number of cases; Sections 4.9 and 4.10 define the operating points and measures used here. Metric choice follows the review task because anomaly-detection metrics encode different assumptions, a point made for time-series detection in [13].`
(Sørbø and Ruocco, PDF pages 1-2, argue that metric choice must reflect task requirements; their scope is time-series detection, hence the qualifier.) If the coordinator prefers not to add this sentence, remove [13] from the reference list instead.

T5 (Section 5.3, stale audit status and missing references).
`The citation audit currently validates 18 references and 15 claim records, and sixteen legally accessible full texts are preserved locally.`
-> `An independent citation audit on 29 October 2026 validated 18 references and 15 claim records; metadata corrections recorded on 1 November 2026 await independent re-audit. Sixteen legally accessible full texts are preserved locally.`

`Two references remain metadata-only: Holm's multiple-comparison paper and Krippendorff's reliability paper. Claims that depend on their full text remain explicitly unverified.`
-> `Two references remain metadata-only: Holm's multiple-comparison paper [17] and Krippendorff's reliability paper [18]. The Holm procedure claim is supported through Demšar's full-text description [11]; the reliability claim attributed to Krippendorff remains explicitly unverified.`

### Optional style note

The reference list is not numbered in order of first citation (first appearances run 1, 2, 3, 6, 4, 5, 10, 9, 14, 7, 8, 15, 16, 12). If the target style is IEEE, renumber after the prose is final. This audit does not renumber, so the R and T items above use the current numbers.
