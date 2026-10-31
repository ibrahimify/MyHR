"""Atomically append one literature-supported claim to the TDK evidence ledger."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.verify_tdk_citations import verify_citation_governance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim-id", required=True)
    parser.add_argument("--claim", required=True)
    parser.add_argument("--document", required=True)
    parser.add_argument("--status", choices=("verified", "inference", "unverified", "contradicted"), required=True)
    parser.add_argument("--citation-key", required=True)
    parser.add_argument("--evidence-type", choices=("full_text", "metadata", "repository_artifact", "expert_judgment"), required=True)
    parser.add_argument("--locator", required=True)
    parser.add_argument("--artifact-id")
    parser.add_argument("--supports", required=True)
    parser.add_argument("--support-type", choices=("direct", "inference", "contradiction", "identity_only"), required=True)
    parser.add_argument("--ledger", type=Path, default=Path("docs/TDK_CLAIM_EVIDENCE_LEDGER.json"))
    args = parser.parse_args()
    if args.evidence_type == "full_text" and not args.artifact_id:
        parser.error("--artifact-id is required for full_text evidence")

    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    if any(item.get("claim_id") == args.claim_id for item in ledger["claims"]):
        raise ValueError(f"claim_id already exists: {args.claim_id}")
    ledger["claims"].append({
        "claim_id": args.claim_id,
        "claim": args.claim,
        "document": args.document,
        "status": args.status,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "evidence": [{
            "citation_key": args.citation_key,
            "evidence_type": args.evidence_type,
            "locator": args.locator,
            "supports": args.supports,
            "support_type": args.support_type,
            **({"artifact_id": args.artifact_id} if args.artifact_id else {}),
        }],
    })
    ledger["audit_state"] = {
        "status": "pending_independent_audit",
        "note": "A new claim invalidates the prior citation audit until an Independent Auditor rechecks it.",
    }
    payload = json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=args.ledger.parent, delete=False
    ) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    try:
        verify_citation_governance(
            Path("docs/TDK_REFERENCES.bib"),
            Path("docs/TDK_CITATION_PROVENANCE.json"),
            temporary,
        )
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    temporary.replace(args.ledger)


if __name__ == "__main__":
    main()
