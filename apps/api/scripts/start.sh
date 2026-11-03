#!/bin/sh
# Production start: migrate, seed, serve. Run from `apps/api`.
#
# Render's free plan has no pre-deploy hook and no shell, so schema and reference
# data are brought up to date here on every boot. Every step is idempotent
# (alembic no-ops at head; seeds upsert by stable key and never delete), and
# `set -e` keeps the API from starting against a schema or seed that failed to apply.
#
# The one-time Saxony jurisdiction repair (scripts/fix_saxony_jurisdiction_leak.py)
# ran its repair and was removed from here on 2026-11-02 once the operator
# confirmed production no longer has the fake Dresden row; the script and its
# test are left in the repo (see chapter B6 in .plans/codebase-audit).
set -e

alembic upgrade head
python -m scripts.seed_i18n
python -m scripts.seed_jurisdictions
python -m scripts.seed_taxonomy

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
