"""PVOG ``personalMatters`` leaf code to situation code mapping.

Built from the human sign-off in ``.plans/situation-tag-coverage/lr3-personal-matters-mapping.md``'s
"Human sign-off" section (recorded as decision T4 in that suite's ``gaps-and-decisions.md``): widen the
LR3 first-pass mapping to include the 14 "ambiguous" leaves alongside the 18 "clean" ones, emitting every
plausible situation code for a bundled leaf instead of excluding it.

32 citizen-branch leaves map to 17 of the 18 situation codes; ``going-self-employed`` has no citizen-branch
PVOG leaf at all (its only analogue is the out-of-scope business branch) and stays unmapped.
"""

from __future__ import annotations

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
