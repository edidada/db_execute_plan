#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
lab_init mysql "$@"
prefix="$LAB_WORK/mysql"
cmake -S upstream/mysql -B "$LAB_WORK/mysql-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
  -DWITH_UNIT_TESTS=OFF -DWITH_ROUTER=OFF -DWITH_NDB=OFF \
  -DWITH_MYSQLX=OFF -DWITH_SSL=system -DWITH_DEBUG=OFF
cmake --build "$LAB_WORK/mysql-build" --target mysqld mysql mysqladmin --parallel "$LAB_JOBS"
binary="$LAB_WORK/mysql-build/runtime_output_directory"
"$binary/mysqld" --no-defaults --initialize-insecure --basedir="$LAB_WORK/mysql-build" --datadir="$LAB_WORK/mysql-data"
"$binary/mysqld" --no-defaults --basedir="$LAB_WORK/mysql-build" --datadir="$LAB_WORK/mysql-data" \
  --skip-networking --socket="$LAB_WORK/mysql.sock" \
  --pid-file="$LAB_WORK/mysql.pid" --log-error="$LAB_OUT/mysql-server.log" &
export PLANLAB_SOCKET="$LAB_WORK/mysql.sock"
trap '"$binary/mysqladmin" --no-defaults --socket="$PLANLAB_SOCKET" -uroot shutdown || true' EXIT
ready=0
for attempt in {1..90}; do
  if "$binary/mysqladmin" --no-defaults --socket="$LAB_WORK/mysql.sock" -uroot ping; then ready=1; break; fi
  sleep 2
done
test "$ready" = 1
"$binary/mysql" --no-defaults --socket="$LAB_WORK/mysql.sock" -uroot -e 'CREATE DATABASE planlab;'
"$binary/mysqld" --version | tee artifacts/server-version.txt
python tools/relational_demo.py mysql
