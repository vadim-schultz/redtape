# Strand: Security, privacy, and GDPR

## Scope

- Distinguish **public/crowdsourced bureaucracy data** from **personal vault data** (device-only or user-chosen cloud).
- Lawful basis, transparency (privacy policy), **subprocessors** list aligned with chosen hosts (see [../../01-stack-and-free-tier.md](../../01-stack-and-free-tier.md)).
- Retention for logs, proposals, and deleted accounts; data export and erasure where applicable.
- AppSec: auth hardening, upload validation, SSRF protections for server-side URL fetchers used by crawlers, rate limiting.

## Dependencies on other strands

- **backend-api** and **social-moderation:** what PII exists on server.
- **mobile-flutter:** local encryption, OAuth to third-party clouds, consent flows.

## Child plans (expand next)

| File | Topic |
|------|--------|
| `01-data-inventory-and-roles.md` | (TBD) Categories of data and controllers/processors. |
| `02-lawful-basis-and-user-rights.md` | (TBD) GDPR articles mapping, DSR process. |
| `03-appsec-checklist.md` | (TBD) Threats and mitigations for API and crawlers. |

## Links

- Master: [../../00-master-summary.md](../../00-master-summary.md)
- Stack: [../../01-stack-and-free-tier.md](../../01-stack-and-free-tier.md)
