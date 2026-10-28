#!/usr/bin/env bash
set -euxo pipefail
cd upstream/datafusion
cargo build --release --locked -p datafusion-cli -j 2
cd ../..
upstream/datafusion/target/release/datafusion-cli --version | tee artifacts/server-version.txt
python tools/datafusion_demo.py
