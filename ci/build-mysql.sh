#!/usr/bin/env bash
set -euxo pipefail
prefix="$RUNNER_TEMP/mysql"
cmake -S upstream/mysql -B "$RUNNER_TEMP/mysql-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
  -DWITH_UNIT_TESTS=OFF -DWITH_ROUTER=OFF -DWITH_NDB=OFF \
  -DWITH_MYSQLX=OFF -DWITH_SSL=system -DWITH_DEBUG=OFF
cmake --build "$RUNNER_TEMP/mysql-build" --target mysqld mysql mysqladmin --parallel 2
binary="$RUNNER_TEMP/mysql-build/runtime_output_directory"
"$binary/mysqld" --no-defaults --initialize-insecure --basedir="$RUNNER_TEMP/mysql-build" --datadir="$RUNNER_TEMP/mysql-data"
"$binary/mysqld" --no-defaults --basedir="$RUNNER_TEMP/mysql-build" --datadir="$RUNNER_TEMP/mysql-data" \
  --bind-address=127.0.0.1 --port=3306 --socket="$RUNNER_TEMP/mysql.sock" \
  --pid-file="$RUNNER_TEMP/mysql.pid" --log-error="$GITHUB_WORKSPACE/artifacts/mysql-server.log" &
ready=0
for attempt in {1..90}; do
  if "$binary/mysqladmin" --no-defaults --socket="$RUNNER_TEMP/mysql.sock" -uroot ping; then ready=1; break; fi
  sleep 2
done
test "$ready" = 1
"$binary/mysql" --no-defaults --socket="$RUNNER_TEMP/mysql.sock" -uroot -e 'CREATE DATABASE planlab;'
"$binary/mysqld" --version | tee artifacts/server-version.txt
python tools/relational_demo.py mysql
