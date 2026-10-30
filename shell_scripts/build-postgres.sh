#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
lab_init postgres "$@"
prefix="$LAB_WORK/pg"
mkdir -p "$LAB_WORK/pg-build"
cd "$LAB_WORK/pg-build"
"$LAB_REPO/upstream/postgres/configure" --prefix="$prefix" --without-icu --without-readline
make -j"$LAB_JOBS"
make install
cd "$LAB_WORK"
"$prefix/bin/initdb" -D "$LAB_WORK/pgdata" -U runner -A trust
"$prefix/bin/pg_ctl" -D "$LAB_WORK/pgdata" -l "$LAB_OUT/postgres-server.log" -o "-h '' -k $LAB_WORK" -w start
"$prefix/bin/createdb" -h "$LAB_WORK" -U runner planlab
"$prefix/bin/postgres" --version | tee artifacts/server-version.txt
export PLANLAB_PG_HOST="$LAB_WORK"
trap '"$prefix/bin/pg_ctl" -D "$LAB_WORK/pgdata" -m fast -w stop' EXIT
python tools/relational_demo.py postgres
