# Gold set for the extraction eval

Twenty real pages with labelled documents, used by `python -m discovery_ingest
llm eval` and by `tests/test_llm_eval_gold_set.py`. Each page is a
`<name>.html` snapshot and a `<name>.gold.json` label file.

**The labels are provisional.** Claude drafted them from the cleaned page text.
A human must review every `.gold.json` file before anyone trusts the
thresholds of decision X14. Review means: open the page at its source URL,
read it, and correct the names, roles and conditions.

## Where the pages come from

Each page is a stored `html_snapshot` that the crawler rendered and kept in
production. The owner approved a read-only download of 189 snapshots on
2026-10-28 for testing. These 20 were chosen by reading their cleaned text.
No page was written by hand and none is synthetic.

- `verwaltung-js-shell` is one of 111 `verwaltung.bund.de` snapshots that are
  empty client-side shells. It stays as the "nothing to read" case.
- The set covers 14 hosts. No host has more than four pages.

## What the labels mean

The rule is the one in the extraction prompt. The labels were drafted against `ext-1`; the prompt is now `ext-5`
(`PROMPT_VERSION` in `extract/llm/prompt.py`), and the labels still wait for a human review.

- A name is copied verbatim from the page, atomic ("A oder B" is two names).
- `required` is a document the applicant brings, `form` is a form to fill in,
  `issued` is what the procedure results in.
- Identifiers and data items are not documents (Kundennummer, Betriebsnummer,
  "Information, ob ...").
- Leaflets, guides and checklists in a download list are not documents.
- `condition` and `is_optional` explain the label. Scoring ignores them.
- `dependencies` hold only what the page states ("dem Antrag beizufügen").
  Edges derived from a single issued document are not labelled here.
- `domain_codes` and `situation_codes` come from `taxonomy.json`, a copy of
  `apps/api/scripts/seed_data/taxonomy.py` in the shape of
  `GET /machine/taxonomy`. Pages that are not procedures carry no codes.
- `source_url` in each label file is the final URL, the base the cleaner
  resolves links against.

## The pages

Counts are characters of the decoded HTML (raw), of the cleaned text with the
default 30,000 character cap (cleaned) and without a cap (full). "Docs" and
"Edges" count gold labels: 47 documents and 2 edges in total.

| Page | Page kind | Docs | Edges | Raw | Cleaned | Full | Kinds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `aa-probebeschaeftigung` | service | 4 | 0 | 77,134 | 4,465 | 4,465 | service, conditional |
| `aa-ferienbeschaeftigung` | service | 8 | 0 | 110,684 | 6,924 | 6,924 | service, conditional |
| `aa-transferkurzarbeitergeld` | service | 9 | 0 | 95,332 | 3,709 | 3,709 | service, conditional |
| `aa-arbeitslos-schritte` | list | 0 | 0 | 61,110 | 1,388 | 1,388 | list, no-documents |
| `ble-fleisch-intervention` | service | 8 | 0 | 52,994 | 21,238 | 21,238 | service, conditional, truncated |
| `ble-wein-neuanpflanzung` | service | 3 | 0 | 56,338 | 20,249 | 20,249 | service, truncated |
| `ble-kaese-lagerhaltung` | other | 0 | 0 | 36,674 | 11,677 | 11,677 | no-documents |
| `bundesarchiv-akteneinsicht` | service | 5 | 2 | 144,830 | 17,716 | 17,716 | service, accordion, conditional, truncated |
| `bfj-gewerbezentralregister` | list | 0 | 0 | 106,506 | 5,949 | 5,949 | list, no-documents |
| `bzkj-antrag-indizierung` | form | 1 | 0 | 41,520 | 1,940 | 1,940 | form |
| `kba-zfer-login` | login_or_error | 0 | 0 | 28,353 | 1,368 | 1,368 | login-wall, no-documents |
| `goaml-start` | login_or_error | 0 | 0 | 11,514 | 4,082 | 4,082 | login-wall, no-documents |
| `vorsorgeregister-registrierung` | service | 3 | 0 | 29,482 | 1,872 | 1,872 | service, conditional |
| `nebenwirkungen-melden` | service | 4 | 0 | 32,441 | 4,728 | 4,728 | service, accordion, conditional |
| `bvl-tierarzneimittel-meldung` | service | 2 | 0 | 25,822 | 5,149 | 5,149 | service |
| `verwaltung-js-shell` | other | 0 | 0 | 6,158 | 0 | 0 | js-shell, no-documents |
| `verwaltung-fluggastrechte-anzeige` | form | 0 | 0 | 10,324 | 1,963 | 1,963 | form, no-documents |
| `auswaertiges-amt-start` | other | 0 | 0 | 113,167 | 1,076 | 1,076 | no-documents |
| `netzausbau-start` | other | 0 | 0 | 74,189 | 5,695 | 5,695 | no-documents |
| `fragebogen-bundeskartellamt-registrierung` | form | 0 | 0 | 17,074 | 2,390 | 2,390 | form, no-documents |

Kinds: `accordion` pages hide their sections behind collapsed toggles (14
toggles on the Bundesarchiv page, an FAQ accordion on `nebenwirkungen.bund.de`);
`list` pages only link to procedures; `truncated` pages hit the 12,000-character cap of `clean-1` and `clean-2`; none hits the 30,000-character cap of `clean-3`, and the manifest keeps the kind as a record.

## Source URL and fetch date

| Page | Fetched | Source URL |
| --- | --- | --- |
| `aa-probebeschaeftigung` | 2026-10-28 | <https://www.arbeitsagentur.de/unternehmen/finanziell/foerderung-menschen-mit-behinderungen/probebeschaeftigung> |
| `aa-ferienbeschaeftigung` | 2026-10-28 | <https://www.arbeitsagentur.de/unternehmen/fachkraefte-ausland/ferienbeschaeftigung> |
| `aa-transferkurzarbeitergeld` | 2026-10-28 | <https://www.arbeitsagentur.de/unternehmen/finanziell/kurzarbeitergeldformen/transfermassnahmen-transferkurzarbeitergeld/transferkurzarbeitergeld-anzeige-antrag-abschlusspruefung> |
| `aa-arbeitslos-schritte` | 2026-10-28 | <https://www.arbeitsagentur.de/arbeitslos-arbeit-finden/arbeitslosengeld/ihre-schritte-wenn-sie-arbeitslos-werden> |
| `ble-fleisch-intervention` | 2026-10-28 | <https://www.ble.de/DE/Themen/Marktorganisation/Intervention/Fleisch/fleisch_node.html> |
| `ble-wein-neuanpflanzung` | 2026-10-28 | <https://www.ble.de/DE/Themen/Landwirtschaft/Wein/wein_node.html> |
| `ble-kaese-lagerhaltung` | 2026-10-28 | <https://www.ble.de/DE/Themen/Marktorganisation/Private-Lagerhaltung/Kaese/kaese_node.html> |
| `bundesarchiv-akteneinsicht` | 2026-10-28 | <https://www.bundesarchiv.de/im-archiv-recherchieren/stasi-unterlagen-einsehen/akteneinsicht-fuer-privatpersonen/> |
| `bfj-gewerbezentralregister` | 2026-10-28 | <https://www.bundesjustizamt.de/DE/Themen/ZentraleRegister/Gewerbezentralregister/Gewerbezentralregister_node.html> |
| `bzkj-antrag-indizierung` | 2026-10-28 | <https://www.bzkj.de/bzkj/service/formulare/antrag> |
| `kba-zfer-login` | 2026-10-28 | <https://www.kba-online.de/registerauskunft/app/> |
| `goaml-start` | 2026-10-28 | <https://goaml.fiu.bund.de/Home> |
| `vorsorgeregister-registrierung` | 2026-10-28 | <https://www.vorsorgeregister.de/privatpersonen/registrierung/> |
| `nebenwirkungen-melden` | 2026-10-28 | <https://nebenwirkungen.bund.de/nw/DE/home/home_node.html> |
| `bvl-tierarzneimittel-meldung` | 2026-10-28 | <https://www.bvl.bund.de/VETUAW/DE/Home/home_node.html> |
| `verwaltung-js-shell` | 2026-10-28 | <https://verwaltung.bund.de/leistungsbeantragung/DE/leistung/99080089011000/herausgeber/LeiKa-103778568/region/00> |
| `verwaltung-fluggastrechte-anzeige` | 2026-10-28 | <https://verwaltung.bund.de/leistungsbeantragung/DE/leistung/99080054261000/herausgeber/LeiKa-103751218/region/00> |
| `auswaertiges-amt-start` | 2026-10-28 | <https://www.auswaertiges-amt.de/de/reiseundsicherheit/reise-und-sicherheitshinweise> |
| `netzausbau-start` | 2026-10-28 | <https://www.netzausbau.de/home/de.html> |
| `fragebogen-bundeskartellamt-registrierung` | 2026-10-28 | <https://www.fragebogen-bundeskartellamt.de/lip/form/display.do?%24context=6A639A6DBD1181B6CD72> |

The snapshot id, byte size and SHA-256 of every original page are in
`manifest.json`.

## Personal data and trimming

Before trimming, these were replaced on every page: email addresses by
`kontakt@example.invalid`, phone and fax numbers by `0000 0000000`, and the
linked names of BLE contact persons by `Ansprechperson`.

To keep each file under 80 KB, the committed HTML has no `script`, `style`,
`svg`, `noscript` or `template` elements, no `style` attributes, no `data:`
URIs and its whitespace runs are collapsed. None of these change what the
cleaner reads, and the test proves it: at trim time the SHA-256 of
`clean_page(...).text` of the redacted, untrimmed page was recorded as
`cleaned_sha256` in `manifest.json`. `test_trimming_did_not_change_what_the_cleaner_reads`
compares it with the cleaned text of every committed page (and the link set,
language and title were compared at trim time).

## Offline measurement: cleaner recall

`cleaner_recall` is the share of gold document names whose slug appears, as
whole words, in the cleaned text. Measured over the 47 gold names: **44 of 47
(0.936)** on 2026-10-28 with `clean-1` and its 12,000-character cap, 46 of 47
(0.979) with `clean-2`, and **47 of 47 (1.000)** with `clean-3` and the default
30,000-character cap (chapter E14), which equals the uncapped result because no
gold page is longer than 21,238 characters.

The two names that the 12,000-character cap cut (`Bestandsliste` on
`ble-fleisch-intervention`, `Nachweis des Verwandtschaftsverhältnisses` on
`bundesarchiv-akteneinsicht`) are inside the text now. The third miss, a link
title joined to a block description without a space on
`aa-ferienbeschaeftigung`, was fixed in `clean-2`. Under the new cap the
`cleaned_sha256` of `ble-fleisch-intervention`, `ble-wein-neuanpflanzung` and
`bundesarchiv-akteneinsicht` changed in `manifest.json`; their `cleaned_chars`
and `truncated` fields there still describe the 12,000-character cap.

## Adding a page

1. Take a stored snapshot and remove personal data as above.
2. Trim it as above and record `cleaned_sha256` from the untrimmed page.
3. Write the label file and add the page to `manifest.json` with its kinds.
4. Run `python -m pytest tests/test_llm_eval_gold_set.py`.
