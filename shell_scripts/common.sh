#!/usr/bin/env bash
# Shared Ubuntu CLI; source from an entry script, then call lab_init NAME "$@".
lab_init() {
  LAB_NAME="$1"; shift
  LAB_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  LAB_JOBS=2
  LAB_WORK="${RUNNER_TEMP:-$LAB_REPO/.local-runs}/planlab-$LAB_NAME"
  LAB_OUT="$LAB_REPO/artifacts/$LAB_NAME"
  local install=0 prepare=0
  while (($#)); do
    case "$1" in
      --work-dir|--output-dir|--jobs)
        if (($# < 2)); then echo "Missing value: $1" >&2; return 2; fi
        case "$1" in
          --work-dir) LAB_WORK="$2";;
          --output-dir) LAB_OUT="$2";;
          --jobs) LAB_JOBS="$2";;
        esac
        shift 2;;
      --install-deps) install=1; shift;;
      --prepare-only) prepare=1; shift;;
      --help|-h)
        printf 'Usage: bash %s [--work-dir DIR] [--output-dir DIR] [--jobs N] [--install-deps] [--prepare-only]\n' "$0"
        echo 'Ubuntu: installs Python packages in an isolated venv; apt installation is opt-in.'
        echo 'Use a fresh work directory per run. No GitHub environment variables are required.'
        exit 0;;
      *) echo "Unknown option: $1" >&2; return 2;;
    esac
  done
  [[ "$LAB_JOBS" =~ ^[1-9][0-9]*$ ]] || { echo 'jobs must be positive' >&2; return 2; }
  if [[ "$LAB_NAME" == mysql* || "$LAB_NAME" == postgres ]]; then
    if ((EUID == 0)); then echo 'Run database labs as a normal user; --install-deps uses sudo for apt only.' >&2; return 2; fi
  fi
  LAB_WORK="$(realpath -m "$LAB_WORK")"
  LAB_OUT="$(realpath -m "$LAB_OUT")"
  [[ "$LAB_WORK" != "$LAB_REPO" && "$LAB_OUT" != "$LAB_WORK" ]] || { echo 'Use separate work/output directories' >&2; return 2; }
  if [[ -e "$LAB_WORK/.planlab-started" ]]; then
    echo "Work directory already used: $LAB_WORK. Choose a new --work-dir; no data will be deleted." >&2
    return 2
  fi
  mkdir -p "$LAB_WORK" "$LAB_OUT"
  if [[ -n "$(ls -A "$LAB_WORK")" ]]; then echo "Work directory must be empty: $LAB_WORK" >&2; return 2; fi
  chmod 700 "$LAB_WORK"
  if [[ -n "$(ls -A "$LAB_OUT")" ]]; then echo "Output directory must be empty: $LAB_OUT" >&2; return 2; fi
  exec > >(tee "$LAB_OUT/build-and-demo.log") 2>&1
  if ((install)); then
    local sudo_cmd=()
    if ((EUID != 0)); then sudo_cmd=(sudo); fi
    "${sudo_cmd[@]}" apt-get update
    "${sudo_cmd[@]}" apt-get install -y build-essential cmake ninja-build bison flex pkg-config libssl-dev libncurses-dev libtirpc-dev libudev-dev libaio-dev zlib1g-dev lld clang python3-venv python3-pip
    if [[ "$LAB_NAME" == iceberg ]]; then
      "${sudo_cmd[@]}" apt-get install -y openjdk-17-jdk
    fi
  fi
  local engine="$LAB_NAME"
  [[ "$engine" != mysql-source-trace ]] || engine=mysql
  git -C "$LAB_REPO" submodule update --init --depth 1 "upstream/$engine"
  mkdir -p "$LAB_WORK/upstream" "$LAB_WORK/data"
  ln -s "$LAB_REPO/upstream/$engine" "$LAB_WORK/upstream/$engine"
  ln -s "$LAB_REPO/tools" "$LAB_WORK/tools"
  ln -s "$LAB_REPO/sql" "$LAB_WORK/sql"
  ln -s "$LAB_REPO/shell_scripts" "$LAB_WORK/shell_scripts"
  ln -s "$LAB_OUT" "$LAB_WORK/artifacts"
  git -C "$LAB_REPO" rev-parse HEAD > "$LAB_OUT/repository-sha.txt"
  git -C "$LAB_REPO/upstream/$engine" rev-parse HEAD > "$LAB_OUT/upstream-sha.txt"
  uname -a > "$LAB_OUT/runner.txt"
  export LAB_REPO LAB_WORK LAB_OUT LAB_JOBS
  cd "$LAB_WORK"
  touch .planlab-started
  if ((prepare)); then echo 'Prepared paths and pinned source; compilation not started.'; exit 0; fi
  python3 -m venv "$LAB_WORK/venv"
  source "$LAB_WORK/venv/bin/activate"
  case "$engine" in
    mysql) python -m pip install PyMySQL==1.1.1;;
    postgres) python -m pip install 'psycopg[binary]==3.2.9';;
    iceberg) python -m pip install pyspark==3.5.6;;
  esac
  python tools/generate_data.py | tee "$LAB_OUT/data-manifest.json"
}
