"""PVOG ``personalMatters`` leaf code to situation code mapping.

Built from the human sign-off in ``.plans/situation-tag-coverage/lr3-personal-matters-mapping.md``'s
"Human sign-off" section (recorded as decision T4 in that suite's ``gaps-and-decisions.md``): widen the
LR3 first-pass mapping to include the 14 "ambiguous" leaves alongside the 18 "clean" ones, emitting every
plausible situation code for a bundled leaf instead of excluding it.

32 citizen-branch leaves map to 17 of the 18 situation codes; ``going-self-employed`` has no citizen-branch
PVOG leaf at all (its only analogue is the out-of-scope business branch) and stays unmapped.
"""

from __future__ import annotations

PERSONAL_MATTER_CLARITY: dict[str, float] = {
    "1010100": 0.95,  # clean: Vor der Geburt
    "1010200": 0.95,  # clean: Nach der Geburt
    "1020100": 0.65,  # ambiguous: Adoption und Pflegekinder
    "1020300": 0.95,  # clean: Eheschließung
    "1020400": 0.95,  # clean: Scheidung
    "1020500": 0.95,  # clean: Trennung mit Kind
    "1030100": 0.65,  # ambiguous: Schule
    "1030200": 0.65,  # ambiguous: Berufsausbildung
    "1030300": 0.95,  # clean: Studium
    "1040300": 0.65,  # ambiguous: Jobsuche und Arbeitslosigkeit
    "1040400": 0.65,  # ambiguous: Anerkennung ausländischer Berufsqualifikationen
    "1040500": 0.65,  # ambiguous: Berufszulassungen und Berechtigungen
    "1050100": 0.95,  # clean: Hausbau und Immobilienerwerb
    "1050200": 0.65,  # ambiguous: Wohnen und Umzug
    "1060400": 0.65,  # ambiguous: Grundsteuer und Grunderwerbsteuer
    "1060600": 0.65,  # ambiguous: Fahrzeugsteuern
    "1060700": 0.65,  # ambiguous: Erbschaftsteuer und Schenkungsteuer
    "1080100": 0.95,  # clean: Einwanderung
    "1080200": 0.65,  # ambiguous: Asyl
    "1080300": 0.95,  # clean: Einbürgerung
    "1080400": 0.65,  # ambiguous: Integration
    "1090100": 0.95,  # clean: Führerscheine
    "1090200": 0.95,  # clean: Fahrzeugbesitz
    "1130100": 0.65,  # ambiguous: Gesundheitsvorsorge
    "1130200": 0.95,  # clean: Krankheit
    "1130300": 0.95,  # clean: Behinderung
    "1130400": 0.95,  # clean: Pflege
    "1140100": 0.65,  # ambiguous: Existenzsicherung und staatliche Unterstützung
    "1180100": 0.95,  # clean: Altersvorsorge
    "1180200": 0.95,  # clean: Rente
    "1190100": 0.95,  # clean: Todesfall
    "1190200": 0.95,  # clean: Erbschaft, Nachlass und Testament
}
"""Mapping-clarity weight per leaf, citing ``lr3-personal-matters-mapping.md``'s verdict column directly:
``0.95`` for the 18 leaves marked "clean" (one leaf maps to one code), ``0.65`` for the 14 marked
"ambiguous" (a many-to-many bundle). Same 32 keys as :data:`PERSONAL_MATTER_TO_SITUATION` — kept in sync
by a key-parity test, not re-derived from the verdict column at runtime.
"""

PERSONAL_MATTER_TO_SITUATION: dict[str, list[str]] = {
    "1010100": ["birth-of-child"],
    "1010200": ["birth-of-child"],
    "1020100": ["birth-of-child"],
    "1020300": ["marriage"],
    "1020400": ["separation-divorce"],
    "1020500": ["separation-divorce"],
    "1030100": ["starting-school"],
    "1030200": ["studying", "new-job"],
    "1030300": ["studying"],
    "1040300": ["job-loss", "new-job"],
    "1040400": ["immigration", "new-job"],
    "1040500": ["getting-licence"],
    "1050100": ["buying-property"],
    "1050200": ["moving-house", "renting-home"],
    "1060400": ["buying-property"],
    "1060600": ["buying-vehicle"],
    "1060700": ["death-of-relative"],
    "1080100": ["immigration"],
    "1080200": ["immigration"],
    "1080300": ["naturalisation"],
    "1080400": ["immigration"],
    "1090100": ["getting-licence"],
    "1090200": ["buying-vehicle"],
    "1130100": ["illness-care"],
    "1130200": ["illness-care"],
    "1130300": ["illness-care"],
    "1130400": ["illness-care"],
    "1140100": ["job-loss"],
    "1180100": ["retirement"],
    "1180200": ["retirement"],
    "1190100": ["death-of-relative"],
    "1190200": ["death-of-relative"],
}
