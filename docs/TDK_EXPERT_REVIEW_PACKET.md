# MyHR TDK Blinded Scenario Realism Review Packet

Status: **METHOD AND PROCEDURE AUTHOR-APPROVED - REVIEWER NOMINATION AND EXECUTION PENDING**

This packet contains no model scores, predictions, thresholds, aggregate results,
or generated truth labels. The project author approved two independent blinded
reviewers with complementary HR-policy and information-systems expertise,
preserved initial judgments, predeclared agreement reporting, evidence-based
adjudication, and retained ambiguity. This is not represented as an independent
supervisor signature. Cases must not be distributed until both reviewers are
nominated and qualified, the sampling output and seed are frozen, and the packet
checksum is recorded.

## Purpose

The review asks whether fictional workforce-progression histories are understandable, administratively plausible, and classifiable from the evidence shown. It does not ask reviewers to judge model quality.

## Reviewer Nomination - Required Before Distribution

| Role | Required expertise | Human name | Qualification evidence | Confirmed/date |
| --- | --- | --- | --- | --- |
| Reviewer A | HR policy, workforce progression, or public-sector personnel administration | ____________________ | ____________________ | ____________________ |
| Reviewer B | Information systems, administrative data quality, or audit systems | ____________________ | ____________________ | ____________________ |

The same person may not fill both roles. Neither reviewer may have generated the
sample labels or inspected model scores for the selected cases.

## Approved Review Method

- Two independent reviewers: one with HR-policy expertise and one with information-systems expertise.
- Independent first-pass ratings. Reviewers must not discuss cases before submitting them.
- A recorded adjudication meeting only for disagreements or missing-policy findings, using documented policy evidence.
- Preserve genuinely ambiguous cases instead of forcing agreement.
- No case may be edited, removed, or relabelled because a detector performs poorly on it.
- Reviewer identity, experience category, review date, case order, and packet checksum must be recorded.

The two-role reviewer method, 48-case sampling plan, agreement measures, and
adjudication principles are approved for protocol preparation. Execution remains
blocked on the two human nominations and the frozen sampling output.

## Predeclared Sampling Protocol

1. Construct the candidate pool from development and validation scenarios only;
   never sample from or inspect a holdout.
2. Include only histories whose scenario combination passes the approved
   population-pattern and record-level eligibility checks.
3. Select 48 histories: 12 ordinary legitimate, 12 rare legitimate, 12
   administrative error, and 12 ambiguous or evidence-insufficient histories.
4. Within those four strata, balance population, policy version, and mechanism
   coverage as far as the frozen candidate pool permits. Record any unavailable
   cell instead of substituting after inspecting model behavior.
5. Use one recorded sampling seed. Selection must not use anomaly scores,
   predictions, alert membership, or method performance.
6. Give both reviewers the same 48 cases in independently randomized order.
   Record both order seeds, the sampling script revision, case IDs, policy-card
   revision, and packet SHA-256 checksum before distribution.

The 48-case review is a realism and evidence-sufficiency check. It does not
estimate organizational prevalence or replace the protocol-scale experiment.

## Reviewer Instructions

For each case, use only the supplied history and policy card. Do not assume facts that are absent. Select `Insufficient evidence` when the record cannot support a reliable decision. Explain the decisive evidence in one or two sentences.

Do not attempt to infer which cases are intended to be unusual. All people, organizations, identifiers, and events are synthetic.

## Policy Card Template

| Field | Value shown to reviewer |
| --- | --- |
| Policy identifier and version | Fictional approved identifier |
| Jurisdiction or organization | Fictional scope |
| Effective period | Start date and end date, if any |
| Required service by level | Months |
| Commendation treatment | Credit rule and limits |
| Sanction treatment | Delay rule and resolution behavior |
| Recognized prior service | Eligibility and evidence rule |
| Recording rule | Effective date versus recorded date |
| Annual increment rule | Explicitly separate from promotion |

## Case History Template

| Evidence group | Information shown |
| --- | --- |
| Employee context | Synthetic identifier, track, level, organization type |
| Employment timeline | Hire, transfer, promotion, and service dates |
| Administrative events | Commendations, sanctions, increments, corrections |
| Policy context | Version, jurisdiction, effective period, exceptions |
| Provenance | Synthetic source references and recorded dates |

Model-derived values are prohibited from the reviewer packet.

## Questionnaire Per Case

1. **Administrative plausibility:** `Plausible` / `Implausible` / `Uncertain`
2. **Record status:** `Ordinary legitimate` / `Rare but legitimate` / `Probable administrative error` / `Insufficient evidence`
3. **Applicable policy clear:** `Yes` / `No`
4. **Timeline internally consistent:** `Yes` / `No` / `Uncertain`
5. **Evidence complete enough for HR review:** `Yes` / `No`
6. **Confidence:** `1` very low through `5` very high
7. **Decisive evidence:** short free-text reason
8. **Missing or ambiguous evidence:** short free-text note
9. **Would you escalate for human review?** `Yes` / `No`

## End-Of-Packet Questions

1. Which policy rules or terms were ambiguous?
2. Which histories seemed unrealistic for the stated organization?
3. Which important administrative mechanisms were missing?
4. Did any case reveal its likely intended label from artificial wording or structure?
5. What evidence would an HR reviewer normally require but was absent?

## Planned Analysis

Report response counts with denominators and reviewer-specific distributions.
For the four-category `Record status` item, report raw agreement and unweighted
Cohen's kappa with a 95% bootstrap interval resampled by case. Report raw
agreement for the other categorical items; confidence is summarized by reviewer
and category and is not converted into a correctness score.

After both first-pass forms are locked, send every record-status disagreement
and every case receiving `Insufficient evidence` from either reviewer to a joint
evidence meeting. Reviewers must cite the policy-card clause and record evidence
supporting any adjudicated result. Preserve each initial rating, the cited
evidence, final disposition, and reason in separate fields. If the evidence does
not resolve the disagreement, retain `Ambiguous`; do not force a binary label or
count adjudication as proof of real-world prevalence.

## Distribution Checklist

- [ ] Policy cards and compatible scenario families match the approved contract
- [ ] Reviewer A named and qualification recorded
- [ ] Reviewer B named and qualification recorded
- [ ] Frozen 48-case sampling output, script revision, and sampling seed
- [ ] No model results or truth labels in distributed files
- [ ] Packet checksum recorded
- [ ] Reviewer instructions piloted for clarity without changing case outcomes
- [ ] Data-protection statement confirmed: fictional data only
