#!/usr/bin/env bash
# Check whether the local dev database is empty or has an initialized CloudStack schema.
# A partially initialized schema must never trigger an automatic deploydb run.
set -euo pipefail

: "${MYSQL_PWD:?The development DB root password must be supplied via MYSQL_PWD}"

schema_state="$(mysql -hskymoon-db -uroot -N -B -e "
SELECT CONCAT(
  (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'cloud'),
  ':',
  (SELECT COUNT(*) FROM information_schema.tables
   WHERE table_schema = 'cloud' AND table_name IN ('configuration', 'user', 'data_center'))
);
")"

if [[ ! "$schema_state" =~ ^([0-9]+):([0-9]+)$ ]]; then
  echo 'SkyMoon: unexpected database schema inventory response; refusing initialization.' >&2
  exit 2
fi

table_count="${BASH_REMATCH[1]}"
essential_count="${BASH_REMATCH[2]}"

if (( table_count == 0 && essential_count == 0 )); then
  printf 'initialize\n'
elif (( table_count >= 3 && essential_count == 3 )); then
  printf 'reuse\n'
else
  echo "SkyMoon: found an incomplete development schema (${table_count} tables, ${essential_count}/3 required tables)." >&2
  echo 'Refusing automatic deploydb. Inspect or restore the database; do not reset a populated volume.' >&2
  exit 2
fi
