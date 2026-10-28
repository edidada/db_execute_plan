#!/usr/bin/env bash
set -euxo pipefail
prefix="$RUNNER_TEMP/pg"
cd upstream/postgres
./configure --prefix="$prefix" --without-icu --without-readline
make -j2
make install
cd ../..
"$prefix/bin/initdb" -D "$RUNNER_TEMP/pgdata" -U runner -A trust
"$prefix/bin/pg_ctl" -D "$RUNNER_TEMP/pgdata" -l "$GITHUB_WORKSPACE/artifacts/postgres-server.log" -o '-h 127.0.0.1 -p 5432' -w start
"$prefix/bin/createdb" -h 127.0.0.1 -U runner planlab
"$prefix/bin/postgres" --version | tee artifacts/server-version.txt
python tools/relational_demo.py postgres
