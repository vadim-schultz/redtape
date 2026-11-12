# Snapshot golden pages

Four stored HTML snapshots copied unchanged from the gold set in `../gold/`, for the snapshot translation golden tests
(`tests/test_snapshot_gold.py`).

| Page | What it pins |
| --- | --- |
| `aa-probebeschaeftigung` | a translated procedure page: headings, paragraphs, list items, link tokens |
| `bzkj-antrag-indizierung` | a translated form page |
| `fragebogen-bundeskartellamt-registrierung` | a page in English, skipped as `not_german` |
| `verwaltung-js-shell` | an empty JavaScript shell, skipped as `too_short` |

`manifest.json` maps each page to the source URL its label file records (the base the cleaner resolves links against).
`<name>.expected.json` is the expected result: the canonical payload of an identity translation for a translated page,
or `{"skipped": reason, "source_hash": hash}` for a skipped one.
