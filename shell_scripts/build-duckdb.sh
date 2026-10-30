#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
lab_init duckdb "$@"
# DuckDB 1.3.2's static shell link contains a back-reference from mbedtls to
# duckdb_static. LLD resolves previously visited archives (GNU ld does not).
ld.lld --version | tee artifacts/linker-version.txt
cmake -S upstream/duckdb -B "$LAB_WORK/duckdb-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_UNITTESTS=OFF -DDISABLE_UNITY=ON \
  -DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld
cmake --build "$LAB_WORK/duckdb-build" --target shell --parallel "$LAB_JOBS"
export DUCKDB_CLI="$LAB_WORK/duckdb-build/duckdb"
"$DUCKDB_CLI" --version | tee artifacts/server-version.txt
python tools/relational_demo.py duckdb
