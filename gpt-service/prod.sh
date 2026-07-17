#!/usr/bin/env sh
set -eu

exec poetry run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-33336}"
