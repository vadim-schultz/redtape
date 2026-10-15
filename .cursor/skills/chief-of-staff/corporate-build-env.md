# Corporate build environment (optional)

Repos behind a corporate proxy may ship this file beside the chief-of-staff skill. When present, the chief of staff includes it in every implementer prompt.

Pass this block to every `chapter-implementer` assignment. Implementers cannot see the user’s `.env`; they must export these before package installs, **manual calls to GovData/PVOG/FIM APIs**, and local CI when the assignment includes this block:

- `NPM_CONFIG_REGISTRY`: `https://npm.packages.rsint.net/artifactory/api/npm/rs_npm_virtual/`
- `HTTP_PROXY` / `HTTPS_PROXY`: `http://185.46.212.88:9480/` (or `http://proxy.rohde-schwarz.com:9480/` per R&S Cloud networking docs)
- `NO_PROXY`: `localhost,127.0.0.1,.rsint.net,.rsext.net`
- `DOCKER_REGISTRY`: `docker.packages.rsint.net/docker.io`
- `RS_DOCKER_REGISTRY`: `docker.packages.rsint.net`
- `PYPI_INDEX_URL`: `https://pypi.packages.rsint.net/api/pypi/rs_pypi_virtual/simple`
- `PYPI_EXTRA_INDEX_URL`: `https://pypi.packages.rsint.net/api/pypi/rs_common_components/simple`

The implementer may mirror the same values as shell `export` lines or read equivalents from repo-root `.env` if present — never commit `.env`.

**Discovery ingest:** `*.fitko.de`, `*.govdata.de`, and `fimportal.de` are **not** on `NO_PROXY`; `curl`, browsers, and `httpx` (with default `trust_env=True`) use the proxy for chapter 7a research and manual CLI runs. CI tests use fixtures only and do not call these hosts.

See also [docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) § Corporate network.
