# Page cleaner fixtures

Rendered-snapshot stand-ins for `clean_page` (chapter E2). Each `<name>.html` has a `<name>.facts.json` with the
sentences and document names that must survive cleaning.

These pages are **synthetic**: hand-built after the layouts of German portals (a Bootstrap accordion service page, an
A to Z list, a client-rendered shell with its raw response in `js_shell.raw.html`, a page with a cookie banner and a
large footer, a table of required documents, an ASP.NET page wrapped in one form), with realistic boilerplate (mega
menu, mobile menu, search form, inline styles and scripts, view state) and no personal data. They are smaller than real
snapshots, so the character ratio they give is optimistic. Replace them with snapshots captured by
`discovery-fixture-capture.yml` and re-run the gate (chapter E5 does this on real pages).
