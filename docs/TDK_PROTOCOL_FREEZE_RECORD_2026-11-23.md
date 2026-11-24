# TDK Protocol Freeze Record

Status: **FREEZE CANDIDATE - HOLDOUT NOT EXECUTABLE**

## Reported authorization

On 23 November 2026, the author reported that the supervisor and two experts
gave permission to continue the research through protocol finalization and the
protected holdout stage. This record preserves that report without inventing
names, qualifications, review responses, signatures, or evidence that was not
provided to the repository.

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
4. links completed blinded-review evidence and SHA-256 checksums;
5. explicitly authorizes one execution.

The runner derives one canonical ledger location outside the repository; callers
cannot select an alternate ledger path. Failed attempts are finalized as failed,
and success is recorded only after the checksummed staging directory is published
atomically. The independent auditor requires that external ledger, revalidates
the authorization evidence, and checks the attempt, matrix, and frozen revision.
This is a fail-closed safeguard against accidental or routine replay within the
supported workflow, not a claim that software can prevent an authorized operator
from editing source, using another clone, or deliberately deleting external state.

## Evidence still required

Before changing this record to `FROZEN`, the execution gate needs the two reviewers'
completed blinded-review evidence. Their identities remain private and are not
recorded in the repository. The private
authorization and evidence files must remain outside the repository; their
checksums bind them to the run. Until those fields are supplied and verified,
no holdout history may be generated, inspected, or scored.

No holdout was generated, inspected, scored, or unlocked while preparing this
record.
