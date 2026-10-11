# Security Policy

MyHR is an academic HR management project that handles sensitive employee-style data in local SQLite databases. Please treat security and privacy issues seriously.

## Supported Versions

Security fixes are handled on the active development branches:

- `master`: stable public branch
- `thesis-final-polish`: thesis/stable app branch
- `research/policy-aware-anomaly`: TDK research branch

## Reporting A Vulnerability

Please do not open a public issue for security vulnerabilities.

Preferred process:

1. Use GitHub private vulnerability reporting if it is available for this repository.
2. If private reporting is not available, contact the maintainer through the GitHub profile and share only a minimal description until a private channel is agreed.

Include:

- affected version or commit;
- steps to reproduce;
- expected impact;
- whether employee data, authentication, export files, or local database files are affected.

## Security Expectations

- Do not commit real employee data, credentials, database files, exported reports, or generated research outputs.
- Keep local `.db`, `.sqlite`, `.env`, and `research_outputs/` files out of Git.
- Treat generated demo data as synthetic unless explicitly documented otherwise.
- Do not use AI-generated research results in the paper unless the exact seed, config, run ID, and output artifacts are saved and reviewed.

## Scope

In scope:

- authentication or authorization bypass;
- sensitive data exposure through exports, logs, reports, or imports;
- unsafe file handling;
- audit-log tampering;
- dependency vulnerabilities;
- reproducibility issues that could falsify research results.

Out of scope:

- attacks requiring already compromised local machines;
- denial-of-service against intentionally local-only demo workflows;
- reports based only on synthetic demo data being visible in screenshots.
