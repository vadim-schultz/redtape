# redtape: repo rules for Claude Code

## Package registries

Corporate package registries are set in the environment, usually in `.env` or the shell: `UV_INDEX_URL`, `UV_DEFAULT_INDEX`, `PIP_INDEX_URL` or `NPM_CONFIG_REGISTRY`. Check them before the first install or `uv`/`npm` run in a session.

1. For each registry URL set in `.env` or the environment, probe it: `curl -sS -o /dev/null -m 10 -w '%{http_code}' <url>`. With no npm override, use `npm config get registry`.
2. If a corporate registry is set and does not answer, install from the public registries for that step: `https://pypi.org/simple` for Python and `https://registry.npmjs.org/` for npm. Do not edit `.env`. If no corporate registry is set, use the public one.
3. Python fallback that leaves the lock file alone: `uv export --frozen --no-hashes --no-emit-project --format requirements-txt > <file>`, then `uv pip install --python .venv/bin/python --index-url https://pypi.org/simple -r <file>`. Run tools with `.venv/bin/python`. `uv run` fails while a lock points at an unreachable mirror.
4. Never commit a lock file that points at a registry. The committed `apps/api/uv.lock` and `apps/discovery-ingest/uv.lock` currently reference `pypi.packages.rsint.net`; leave them unless the user asks for a re-lock. Revert any `uv.lock` or `package-lock.json` change that a fallback made before committing.
5. Name every fallback in the final message, so the user knows which packages came from the public index.
