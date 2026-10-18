# MyHR TDK Blinded Scenario Realism Review Packet

Status: **DRAFT - PENDING HUMAN APPROVAL**

This packet contains no model scores, predictions, thresholds, aggregate results, or generated truth labels. It does not approve a scenario or alter the experiment protocol. Cases must not be distributed until a human approves the policy assumptions, reviewer roles, and sampling plan.

## Purpose

The review asks whether fictional workforce-progression histories are understandable, administratively plausible, and classifiable from the evidence shown. It does not ask reviewers to judge model quality.

## Proposed Review Design

- Two reviewers with HR administration, public-sector personnel, employment-policy, or closely related experience.
- A blinded set of 48 fictional histories, sampled before model evaluation from approved scenario families.
- Independent first-pass ratings. Reviewers must not discuss cases before submitting them.
- A recorded adjudication meeting only for disagreements or missing-policy findings.
- No case may be edited, removed, or relabelled because a detector performs poorly on it.
- Reviewer identity, experience category, review date, case order, and packet checksum must be recorded.

The sample size, reviewer eligibility, agreement statistic, and adjudication rule are proposals only.

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

Report response counts with denominators, reviewer-specific distributions, raw agreement, and a human-approved chance-corrected agreement statistic. Preserve original ratings, disagreement reasons, and adjudicated outcomes separately. Do not treat adjudication as proof of real-world prevalence.

## Distribution Checklist

- [ ] Human approval of policy cards and scenario families
- [ ] Human approval of reviewer eligibility and invitations
- [ ] Frozen case-sampling script and random seed
- [ ] No model results or truth labels in distributed files
- [ ] Packet checksum recorded
- [ ] Reviewer instructions piloted for clarity without changing case outcomes
- [ ] Data-protection statement confirmed: fictional data only
