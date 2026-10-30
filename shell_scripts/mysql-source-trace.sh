#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
lab_init mysql-source-trace "$@"
out="$LAB_OUT"
export PLANLAB_TRACE_OUT="$LAB_OUT"
cp -r sql/mysql-source-trace "$out/sql"
build="$LAB_WORK/mysql-trace-build"
data="$LAB_WORK/mysql-trace-data"
export PLANLAB_SOCKET="$LAB_WORK/mysql-trace.sock"
cmake -S upstream/mysql -B "$build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DWITH_DEBUG=ON -DWITH_UNIT_TESTS=OFF \
  -DWITH_ROUTER=OFF -DWITH_NDB=OFF -DWITH_MYSQLX=OFF -DWITH_SSL=system
cp "$build/CMakeCache.txt" "$out/CMakeCache.txt"
cmake --build "$build" --target mysqld mysql mysqladmin --parallel "$LAB_JOBS"
binary="$build/runtime_output_directory"
"$binary/mysqld" --version | tee "$out/server-version.txt"
"$binary/mysqld" --no-defaults --initialize-insecure --basedir="$build" --datadir="$data"
"$binary/mysqld" --no-defaults --basedir="$build" --datadir="$data" \
  --skip-networking --socket="$PLANLAB_SOCKET" --pid-file="$LAB_WORK/mysql-trace.pid" \
  --log-error="$out/mysql-error.log" &
server_pid=$!
cleanup() {
  "$binary/mysqladmin" --no-defaults --socket="$PLANLAB_SOCKET" -uroot shutdown || true
  wait "$server_pid" || true
}
trap cleanup EXIT
ready=0
for attempt in {1..90}; do
  if "$binary/mysqladmin" --no-defaults --socket="$PLANLAB_SOCKET" -uroot ping; then ready=1; break; fi
  sleep 2
done
test "$ready" = 1
python tools/mysql_source_trace.py
# Print selected native source logs in Actions; upload complete files separately.
grep -E 'JOIN::optimize|choose_table_order|Query plan:|create_access_paths' "$out/after-index.dbug" | head -80 || true
