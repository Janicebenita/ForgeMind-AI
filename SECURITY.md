# Security — ForgeMind AI

## Authentication & RBAC

ForgeMind AI uses signed JWT tokens for authentication. Backend-authoritative
role-based access control (RBAC) determines which evidence a user can access.

Role filtering is applied **before** retrieval and generation. The frontend
cannot override backend access controls.

## Authorization Before Evidence Retrieval

All retrieval and generation requests are subject to backend authorization.
Evidence is filtered by the authenticated user's role before any AI model
receives context. Unauthorized evidence is never passed to generation.

## Evidence & Data Handling

- Ingested documents are recorded with SHA-256 hashes for lineage and
  integrity verification.
- Duplicate documents are rejected at ingestion.
- Generated outputs include citations referencing source evidence.
- Confidence metadata accompanies AI-generated responses.
- The system abstains when evidence is insufficient.

## Environment Variables & Secrets

- Credentials and secrets must be stored in environment variables or
  Azure Key Vault references — never in source code.
- The `.env.example` file documents required variables without including
  real values.
- Demo credentials included in the repository are intended for local
  evaluation only and must be replaced in any shared or production
  environment.

## Source Lineage

Every ingested document is associated with a SHA-256 hash, original filename,
and ingestion timestamp. This lineage chain supports auditability and
evidence integrity verification.

## Human Authorization Boundary

ForgeMind AI is a decision-support platform. It does not execute industrial
actions, control equipment, approve maintenance, or override human authority.

All operational decisions remain under authorized human control.

## Synthetic Rail Dataset Disclaimer

The `demo-data/rail/` directory contains entirely synthetic data created
for the Omnikon National Hackathon 2026. It does not represent any real
railway operator, real assets, or real incidents.

## Vulnerability Reporting

If you discover a security vulnerability in this repository, please report
it responsibly by contacting the repository maintainers directly through
GitHub rather than opening a public issue.

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt and work to address confirmed vulnerabilities
promptly.
