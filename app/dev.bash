set -a
[ -f ../.env ] && . ../.env
set +a

export PYTHONPATH=$(pwd)

uvicorn main:app --host 0.0.0.0 --port 3000 --reload