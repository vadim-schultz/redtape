#!/bin/sh
# Production start: migrate, seed, serve. Run from `apps/api`.
#
# Render's free plan has no pre-deploy hook and no shell, so schema and reference
# data are brought up to date here on every boot. Every step is idempotent
# (alembic no-ops at head; seeds upsert by stable key and never delete), and `set -e`
# keeps the API from starting against a schema or seed that failed to apply.
set -e

alembic upgrade head
python -m scripts.seed_i18n
python -m scripts.seed_documents
python -m scripts.seed_taxonomy

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
