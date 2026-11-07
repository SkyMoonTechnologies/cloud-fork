#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/mysql" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
case "${MOCK_DB_SCENARIO:-}" in
  empty) printf '0:0\n' ;;
  ready) printf '235:3\n' ;;
  missing_config) printf '28:2\n' ;;
  partial) printf '2:1\n' ;;
  malformed) printf 'not-an-inventory\n' ;;
  mysql_error) exit 1 ;;
  *) exit 3 ;;
esac
MOCK
chmod +x "$TMP/mysql"
export PATH="$TMP:$PATH" MYSQL_PWD='mock-only'
check() {
  local scenario="$1" expected_status="$2" expected_output="$3" status=0 output
  export MOCK_DB_SCENARIO="$scenario"
  output="$(bash "$SCRIPT_DIR/db-init-guard.sh" 2>&1)" || status=$?
  if [[ "$status" -ne "$expected_status" ]]; then
    printf 'FAIL: %s returned %s not %s: %s\n' "$scenario" "$status" "$expected_status" "$output" >&2
    exit 1
  fi
  if [[ "$output" != *"$expected_output"* ]]; then
    printf 'FAIL: %s missing expected output %q: %s\n' "$scenario" "$expected_output" "$output" >&2
    exit 1
  fi
}
check empty 0 initialize
check ready 0 reuse
check missing_config 2 incomplete
check partial 2 incomplete
check malformed 2 unexpected
check mysql_error 1 ''
printf 'PASS: DB initialization guard scenarios (6)\n'
