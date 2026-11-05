# Strand: Mobile (Flutter)

## Scope

- Flutter app modules: **browse** public dependency data (API client), **local vault** for user-owned files/metadata, **reminders** (local notifications MVP; optional FCM for metadata-only sync).
- **Localization:** mirror web — fetch translation bundle, keep current locale in app state, send **`Accept-Language`** on HTTP calls; prefer localized strings from API over hardcoding. Spec: [../i18n-localization/README.md](../i18n-localization/README.md).
- **Storage modes:** strictly on-device; optional **BYO cloud** behind a narrow `CloudSyncProvider` interface (WebDAV, Dropbox, Google Drive, etc.) with user OAuth—no Redtape server storage of blobs in that mode.
- Organization by canonical **category** (folders/tags) using the same language-neutral `code`s the API serves
  from `GET /api/v1/categories` (no Flutter work yet, syncing the taxonomy is a later chapter); encryption
  at rest using platform secure storage for keys.
- Platform-specific packaging (iOS/Android), store policies, and deep links (optional).

## Dependencies on other strands

- **backend-api:** read-only graph and social endpoints as exposed to mobile.
- **security-privacy-gdpr:** privacy disclosures and data minimization for any server-side account features.
- **devops-ci-cd:** build pipelines, signing, env files.

## Child plans (expand next)

| File | Topic |
|------|--------|
| `01-app-modules-and-navigation.md` | (TBD) Tabs/shell, browse vs vault. |
| `02-local-vault-and-encryption.md` | (TBD) On-device DB/files, key handling. |
| `03-cloud-adapters.md` | (TBD) Provider interface, OAuth, sync semantics. |
| `04-reminders-and-deadlines.md` | (TBD) Local vs push, modeling time-sensitive rules. |

## Links

- Master: [../../00-master-summary.md](../../00-master-summary.md)
- Stack: [../../01-stack-and-free-tier.md](../../01-stack-and-free-tier.md)
