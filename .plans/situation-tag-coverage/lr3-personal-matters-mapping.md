---
name: "LR3 — PVOG personalMatters leaf-code mapping"
overview: "The full hand-mapping artifact for LR3: every leaf code the live PVOG v7 bootstrap tree returned, against the 18 life_situation codes in apps/api/scripts/seed_data/taxonomy.py."
isProject: false
---

# LR3 — PVOG personalMatters leaf-code mapping

**Live run:** [02-live-runs.md](02-live-runs.md) (LR3) · **Decision:** [gaps-and-decisions.md](gaps-and-decisions.md) (T-PENDING, S3 row)

**Provenance.** Fetched 2026-11-01 from the live, public v7 bootstrap endpoint (`https://pvog.fitko.net/suchdienst/api/v7/servicedescriptions/000000000000?personalMatters=Geburt&facades=true&size=100`, the same request `PvogClient.fetch_personal_matter_vocabulary()` from chapter 3 issues) — no credentials required, read-only GET. 118 leaf codes returned (`facades.personalMatters`, deduplicated and sorted by `_personal_matter_codes_from_facades`), 56 under the citizen-facing top node (`Lebenslagen für Bürgerinnen und Bürger`, codes `1xxxxxx`) and 62 under the business-facing top node (`Geschäftslagen für Unternehmen`, codes `2xxxxxx`).

**Who did this mapping.** This is a first-pass, AI-assisted hand-mapping (done by the chief of staff in this run), not a human domain expert's. `02-live-runs.md`'s own LR3 text calls for "a human" to do this judgment call. **Treat the percentages below as a starting point for a human spot-check, not a settled number** — several calls (marked below) are genuinely debatable.

## Why the business branch is out of scope

The 18 `life_situation` codes are all individual/personal life events (birth, marriage, moving, retirement, ...). PVOG's tree splits citizens from businesses at the top level, and the business branch (`2xxxxxx`, 62 leaves — business registration, payroll, procurement, R&D, environmental permits, etc.) has no citizen-facing counterpart among the 18. Even `going-self-employed` ("Gewerbe anmelden und Selbstständigkeit starten") — the one situation code about an individual's own economic choice — is modelled by PVOG as a transaction the resulting *business* performs (`2010100`–`2010600`, under `Unternehmensstart und Gewerbezulassung`), not as a citizen life-situation leaf. All 62 business leaves are counted as **unmapped** below, not ambiguous: this isn't a close call, it's a scope mismatch baked into PVOG's own taxonomy design.

## Citizen-branch mapping (56 leaves)

| Code | Name (de) | Parent category | Verdict | Target situation code(s) |
| --- | --- | --- | --- | --- |
| 1010100 | Vor der Geburt | Geburt | clean | birth-of-child |
| 1010200 | Nach der Geburt | Geburt | clean | birth-of-child |
| 1020100 | Adoption und Pflegekinder | Partnerschaft und Familie | ambiguous | birth-of-child (closest, not exact — adoption isn't a birth) |
| 1020200 | Kinderbetreuung | Partnerschaft und Familie | unmapped | — (ongoing childcare logistics, not a triggering event) |
| 1020300 | Eheschließung | Partnerschaft und Familie | clean | marriage |
| 1020400 | Scheidung | Partnerschaft und Familie | clean | separation-divorce |
| 1020500 | Trennung mit Kind | Partnerschaft und Familie | clean | separation-divorce |
| 1030100 | Schule | Schule, Ausbildung und Studium | ambiguous | starting-school (broader than just "starting") |
| 1030200 | Berufsausbildung | Schule, Ausbildung und Studium | ambiguous | studying / new-job (vocational training straddles both, no dedicated code) |
| 1030300 | Studium | Schule, Ausbildung und Studium | clean | studying |
| 1040100 | Weiterbildung | Arbeit | unmapped | — (continuing education, not a listed situation) |
| 1040300 | Jobsuche und Arbeitslosigkeit | Arbeit | ambiguous | job-loss **and** new-job (one PVOG leaf bundles both — the textbook many-to-many case) |
| 1040400 | Anerkennung ausländischer Berufsqualifikationen | Arbeit | ambiguous | immigration / new-job |
| 1040500 | Berufszulassungen und Berechtigungen | Arbeit | ambiguous | getting-licence (taxonomy's description is driving/boating-specific, not professional licensing) |
| 1050100 | Hausbau und Immobilienerwerb | Bauen und Wohnen | clean | buying-property |
| 1050200 | Wohnen und Umzug | Bauen und Wohnen | ambiguous | moving-house **and** renting-home (one leaf bundles both) |
| 1060100 | Steuererklärung | Steuern und Abgaben | unmapped | — |
| 1060200 | Einkommensteuer und Kirchensteuer | Steuern und Abgaben | unmapped | — |
| 1060300 | Sozialabgaben | Steuern und Abgaben | unmapped | — |
| 1060400 | Grundsteuer und Grunderwerbsteuer | Steuern und Abgaben | ambiguous | buying-property (ongoing tax, not the purchase event itself) |
| 1060600 | Fahrzeugsteuern | Steuern und Abgaben | ambiguous | buying-vehicle (ongoing tax, not the purchase event) |
| 1060700 | Erbschaftsteuer und Schenkungsteuer | Steuern und Abgaben | ambiguous | death-of-relative (also covers lifetime gifts, unrelated to a death) |
| 1060800 | Sonstige Steuern | Steuern und Abgaben | unmapped | — |
| 1070100 | Ausweise | Ausweise und Dokumente | unmapped | — (domain-shaped, cuts across many situations) |
| 1070200 | Urkunden und Bescheinigungen | Ausweise und Dokumente | unmapped | — (domain-shaped; birth/marriage/death certs all live here) |
| 1080100 | Einwanderung | Migration und Integration | clean | immigration |
| 1080200 | Asyl | Migration und Integration | ambiguous | immigration (a distinct legal track, not named separately in the 18) |
| 1080300 | Einbürgerung | Migration und Integration | clean | naturalisation |
| 1080400 | Integration | Migration und Integration | ambiguous | immigration (broad) |
| 1090100 | Führerscheine | Mobilität und Fahrzeuge | clean | getting-licence |
| 1090200 | Fahrzeugbesitz | Mobilität und Fahrzeuge | clean | buying-vehicle |
| 1100100 | Engagement und Beteiligung | Wahlen, Engagement und Beteiligung | unmapped | — |
| 1100200 | Wahlen | Wahlen, Engagement und Beteiligung | unmapped | — |
| 1110100 | Veranstaltungen und Feste | Hobby und Freizeit | unmapped | — |
| 1110200 | Fischen und Jagen | Hobby und Freizeit | unmapped | — (hunting/fishing licences outside getting-licence's described scope) |
| 1110300 | Tierhaltung | Hobby und Freizeit | unmapped | — |
| 1120100 | Reisen | Reisen und Auslandsaufenthalt | unmapped | — |
| 1120200 | Auslandsaufenthalt | Reisen und Auslandsaufenthalt | unmapped | — |
| 1120300 | Auswanderung | Reisen und Auslandsaufenthalt | unmapped | — (emigration; immigration's own description is one-directional, "moving to Germany") |
| 1130100 | Gesundheitsvorsorge | Gesundheit und Vorsorge | ambiguous | illness-care (preventive care, not illness itself) |
| 1130200 | Krankheit | Gesundheit und Vorsorge | clean | illness-care |
| 1130300 | Behinderung | Gesundheit und Vorsorge | clean | illness-care |
| 1130400 | Pflege | Gesundheit und Vorsorge | clean | illness-care |
| 1140100 | Existenzsicherung und staatliche Unterstützung | Sozialleistungen | ambiguous | job-loss (welfare broadly, not exclusively job-loss-triggered) |
| 1150100 | Außergerichtliche Verfahren und Streitschlichtung | Recht und Verbraucherschutz | unmapped | — |
| 1150200 | Gerichtliche Verfahren, Anzeige und Klage | Recht und Verbraucherschutz | unmapped | — |
| 1150300 | Verbraucherschutz | Recht und Verbraucherschutz | unmapped | — |
| 1150400 | Datenschutz, Auskünfte und Akteneinsicht | Recht und Verbraucherschutz | unmapped | — |
| 1160100 | Katastrophenhilfe | Notlagen und Opferhilfen | unmapped | — |
| 1160200 | Hilfen für Geschädigte | Notlagen und Opferhilfen | unmapped | — |
| 1170100 | Klima, Natur und Arten | Umwelt und Klima | unmapped | — |
| 1170200 | Wasser, Gewässer und Boden | Umwelt und Klima | unmapped | — |
| 1180100 | Altersvorsorge | Altersvorsorge und Ruhestand | clean | retirement |
| 1180200 | Rente | Altersvorsorge und Ruhestand | clean | retirement |
| 1190100 | Todesfall | Sterbefall und Nachlass | clean | death-of-relative |
| 1190200 | Erbschaft, Nachlass und Testament | Sterbefall und Nachlass | clean | death-of-relative |

**Tally (citizen branch, 56 leaves):** 18 clean (32%), 14 ambiguous (25%), 24 unmapped (43%).

## Business-branch leaves (62, codes `2xxxxxx`)

All 62 counted **unmapped** — out of scope per the scope-mismatch note above, not individually tabulated. (`going-self-employed`'s closest PVOG analogue, `2010100`–`2010600` under `Unternehmensstart und Gewerbezulassung`, lives here.)

## Overall tally (118 leaves)

| Verdict | Count | Share |
| --- | --- | --- |
| Clean | 18 | 15.3% |
| Ambiguous | 14 | 11.9% |
| Unmapped | 86 (24 citizen + 62 business) | 72.9% |

## What this means for T-PENDING's S3 row

- Where PVOG does map cleanly, it's a genuine independent second signal: 12 of the 18 situation codes get at least one clean PVOG leaf (`birth-of-child`, `marriage`, `separation-divorce`, `studying`, `buying-property`, `immigration`, `naturalisation`, `getting-licence`, `buying-vehicle`, `illness-care`, `retirement`, `death-of-relative`). The remaining 6 (`moving-house`, `job-loss`, `new-job`, `going-self-employed`, `starting-school`, `renting-home`) get none — either bundled ambiguously with another situation or absent from PVOG's tree entirely.
- `job-loss` and `new-job` share one ambiguous PVOG leaf (`1040300`) rather than each getting their own — PVOG's own granularity doesn't distinguish them, so S3 cannot disambiguate those two situations from the PVOG signal alone.
- `moving-house` and `renting-home` share one ambiguous leaf (`1050200`) likewise.
- `starting-school` and `going-self-employed` have **no PVOG leaf of their own** — `starting-school`'s closest leaf (`1030100`, "Schule") is broader than enrollment alone, and `going-self-employed` has no citizen-branch analogue at all.
- The 43% citizen-branch unmapped share (domain-shaped buckets like taxes, IDs/certificates, legal process, consumer protection, civic engagement) confirms PVOG's `personalMatters` vocabulary is not a 1:1 substitute for the 18 situation codes — it is a differently-grained classification that happens to overlap on roughly a third of its citizen-facing leaves.

**Recommendation for the human spot-check:** review the 14 "ambiguous" rows first (listed above) — that's where the mapping choice actually matters for S3's eventual precision, far more than confirming the 18 "clean" rows.
