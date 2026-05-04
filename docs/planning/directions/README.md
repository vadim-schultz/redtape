# Planning strands

Each subdirectory is a **development strand**: overview in `README.md`, with numbered or named child files for implementation chapters.

| Strand | Focus |
|--------|--------|
| [backend-api](backend-api/) | Litestar, Pydantic, SQLAlchemy, public API, OpenAPI |
| [data-model-migrations](data-model-migrations/) | Postgres schema, jurisdiction fallback, graph storage |
| [i18n-localization](i18n-localization/) | DB-based translations, locale negotiation, fallback chain |
| [web-frontend](web-frontend/) | Vite, React, TypeScript, Chakra, graph UI, social flows |
| [mobile-flutter](mobile-flutter/) | Vault, BYO cloud, reminders, API client |
| [crawlers-jobs](crawlers-jobs/) | Freshness vs discovery, scheduling, ethics |
| [social-moderation](social-moderation/) | Proposals, votes, evidence, audit log, roles |
| [security-privacy-gdpr](security-privacy-gdpr/) | Lawful basis, retention, local-first posture |
| [devops-ci-cd](devops-ci-cd/) | Monorepo layout, CI, migrations, secrets, observability |

Return to [../README.md](../README.md) for reading order and conventions.
