#!/usr/bin/env bash
set -euo pipefail
mkdir -p artifacts/mysql-source-trace
out="$GITHUB_WORKSPACE/artifacts/mysql-source-trace"
exec > >(tee "$out/build-and-demo.log") 2>&1
set -x
sudo apt-get update
sudo apt-get install -y build-essential cmake ninja-build bison pkg-config libssl-dev libncurses-dev libtirpc-dev libudev-dev libaio-dev
python -m pip install PyMySQL==1.1.1
git submodule update --init --depth 1 upstream/mysql
git rev-parse HEAD > "$out/repository-sha.txt"
git -C upstream/mysql rev-parse HEAD > "$out/upstream-sha.txt"
cp -r sql/mysql-source-trace "$out/sql"
python tools/generate_data.py | tee "$out/data-manifest.json"
build="$RUNNER_TEMP/mysql-trace-build"
data="$RUNNER_TEMP/mysql-trace-data"
export PLANLAB_SOCKET="$RUNNER_TEMP/mysql-trace.sock"
cmake -S upstream/mysql -B "$build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DWITH_DEBUG=ON -DWITH_UNIT_TESTS=OFF \
  -DWITH_ROUTER=OFF -DWITH_NDB=OFF -DWITH_MYSQLX=OFF -DWITH_SSL=system
cp "$build/CMakeCache.txt" "$out/CMakeCache.txt"
cmake --build "$build" --target mysqld mysql mysqladmin --parallel 2
binary="$build/runtime_output_directory"
"$binary/mysqld" --version | tee "$out/server-version.txt"
"$binary/mysqld" --no-defaults --initialize-insecure --basedir="$build" --datadir="$data"
"$binary/mysqld" --no-defaults --basedir="$build" --datadir="$data" \
  --skip-networking --socket="$PLANLAB_SOCKET" --pid-file="$RUNNER_TEMP/mysql-trace.pid" \
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
