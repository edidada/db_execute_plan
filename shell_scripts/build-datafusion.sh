#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
lab_init datafusion "$@"
export CARGO_TARGET_DIR="$LAB_WORK/cargo-target"
export PLANLAB_DATAFUSION_CLI="$CARGO_TARGET_DIR/release/datafusion-cli"
command -v rustup >/dev/null || { echo 'Install rustup first: https://rustup.rs' >&2; exit 2; }
rustup toolchain install 1.88.0 --profile minimal
export RUSTUP_TOOLCHAIN=1.88.0
export CARGO_PROFILE_RELEASE_DEBUG=0
export CARGO_PROFILE_RELEASE_LTO=false
cd upstream/datafusion
cargo build --release --locked -p datafusion-cli -j "$LAB_JOBS"
cd ../..
"$PLANLAB_DATAFUSION_CLI" --version | tee artifacts/server-version.txt
python tools/datafusion_demo.py
