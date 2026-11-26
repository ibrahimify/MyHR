"""Rebuild the checksum manifest for preserved documentation."""

from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path


ARCHIVE_ROOT = Path("docs/archive")
MANIFEST_PATH = ARCHIVE_ROOT / "MANIFEST.md"


def normalized_bytes(path: Path) -> bytes:
    body = path.read_bytes()
    if path.suffix.lower() in {".md", ".html"}:
        body = body.replace(b"\r\n", b"\n")
    return body


def main() -> int:
    files = sorted(
        path
        for path in ARCHIVE_ROOT.rglob("*")
        if path.is_file() and path != MANIFEST_PATH
    )
    lines = [
        "# Archive Manifest",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "This manifest records the files preserved under `docs/archive/`, excluding this self-referential manifest.",
        "Checksums are SHA-256. Markdown and HTML use Git-normalized LF line endings.",
        "",
        "| Archived path | Bytes | SHA-256 |",
        "| --- | ---: | --- |",
    ]
    for path in files:
        body = normalized_bytes(path)
        relative = path.relative_to(ARCHIVE_ROOT).as_posix()
        lines.append(f"| `{relative}` | {len(body):,} | `{sha256(body).hexdigest()}` |")
    lines.extend(
        [
            "",
            "Archived files preserve project history and are not current scientific authority.",
            "See `docs/README.md` for the active documentation set.",
            "",
        ]
    )
    MANIFEST_PATH.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
