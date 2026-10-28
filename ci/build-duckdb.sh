#!/usr/bin/env bash
set -euxo pipefail
cmake -S upstream/duckdb -B "$RUNNER_TEMP/duckdb-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_UNITTESTS=OFF -DDISABLE_UNITY=ON
cmake --build "$RUNNER_TEMP/duckdb-build" --target shell --parallel 2
export DUCKDB_CLI="$RUNNER_TEMP/duckdb-build/duckdb"
"$DUCKDB_CLI" --version | tee artifacts/server-version.txt
python tools/relational_demo.py duckdb
