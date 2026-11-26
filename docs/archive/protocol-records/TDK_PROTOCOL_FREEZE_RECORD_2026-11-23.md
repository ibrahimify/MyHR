# TDK Protocol Freeze Record

Status: **FROZEN - ONE AUTHORIZED HOLDOUT ATTEMPT**

## Reported authorization

On 24 November 2026, the author reported that the supervisor approved protocol
freeze and that two independent academic experts completed a qualitative realism
review and authorized the protected holdout stage. Their identities remain
private. The repository records no names, case-level ratings, agreement statistic,
or adjudication outcome that was not supplied.

## Frozen candidate

The candidate is defined by `config/tdk_holdout_matrix_v1.json`:

- 36 deterministic pairwise-covering conditions;
- 30 independent seeds per condition;
- 120 fictional employee histories per scenario;
- a holdout seed family disjoint from development and validation;
- identical 10% additional review capacity for raw and policy-aware methods;
- recall at fixed capacity as the primary endpoint;
- AP and legitimate-case flag rates as the Holm-adjusted secondary family;
- Isolation Forest as the primary scorer;
- five predeclared scorers retained only as exploratory comparisons;
- fixed environment, dependency, and condition-matrix checksums.

The condition matrix SHA-256 is
`ca6bdc2a3977485e8e7d48deb4d64666b15a1f572663882c3d58bdb026ada139`.

## Fail-closed execution gate

The runner cannot consume the holdout unless an untracked authorization record:

1. binds the exact clean Git revision and matrix checksum;
2. records dated supervisor approval and its evidence locator;
3. records two distinct anonymous reviewer IDs and their qualifications;
4. links completed expert-review evidence and SHA-256 checksums;
5. explicitly authorizes one execution.

The runner derives one canonical ledger location outside the repository; callers
cannot select an alternate ledger path. Failed attempts are finalized as failed,
and success is recorded only after the checksummed staging directory is published
atomically. The independent auditor requires that external ledger, revalidates
the authorization evidence, and checks the attempt, matrix, and frozen revision.
This is a fail-closed safeguard against accidental or routine replay within the
supported workflow, not a claim that software can prevent an authorized operator
from editing source, using another clone, or deliberately deleting external state.

## Private evidence boundary

The private authorization and evidence files remain outside the repository;
their checksums bind them to the run. Anonymous reviewer IDs and qualifications
are sufficient for the tracked provenance. The review establishes qualitative
face validity only; it does not provide quantitative agreement evidence.

No holdout was generated, inspected, scored, or unlocked while preparing this
record.
