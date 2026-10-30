# MyHR TDK Supervisor Decision Sheet

**Nothing below is approved until a human records a decision. The final holdout remains locked.**

The high-level choices recorded on 29 October remain the implementation direction. This sheet concerns concrete definitions exposed by the second audit and is required before protocol freeze.

| Decision | Evidence and recommendation | Human response |
| --- | --- | --- |
| Scenario Proposals 1 and 3-6 | Repaired late-correction and transition cases now satisfy invariant checks, but their semantics and matrix frequency are not approved. Review the examples and approve, reject, or modify them. | [ ] Approve [ ] Reject [ ] Modify |
| Employee-specific grandfathering | Policy identity alone cannot prove an employee's entitlement. Require an explicit entitlement/evidence record rather than infer grandfathering from a generated label. | [ ] Approve [ ] Reject [ ] Modify |
| Knowledge-time and review-time views | Effective and recorded dates exist, but the exact view for "what was knowable then" versus "what is reviewable now" is not frozen. Define both before protocol-scale generation. | [ ] Approve [ ] Reject [ ] Modify |
| Expert realism review | Use two blinded reviewers with HR-policy and information-systems expertise. Fix sample size, questionnaire, agreement statistic, adjudication, and ambiguity handling before showing cases. | [ ] Approve [ ] Reject [ ] Modify |
| Protocol-scale matrix | Keep scenario seeds as units; predeclare populations, mechanisms, repeated seeds, and zero-positive handling. Do not select cells after inspecting results. | [ ] Approve [ ] Reject [ ] Modify |
| Multiplicity | Keep fixed-capacity recall primary; treat AP as secondary; predeclare the full secondary family and Holm adjustment. | [ ] Approve [ ] Reject [ ] Modify |
| Freeze and holdout | Authorize one holdout run only after all above decisions, expert review, clean development/validation artifacts, dependency lock, source revision, and independent audit are dated and frozen. | [ ] Approve [ ] Reject [ ] Modify |

Reviewer: ____________________  Date: ____________________  Signature: ____________________
