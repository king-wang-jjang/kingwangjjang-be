set -a
[ -f ../.env ] && . ../.env
set +a

export PYTHONPATH=$(pwd)

poetry run python main.py