"""Render the five independent software workflows; no compilation here."""
from pathlib import Path

software = {
    'postgres': ('sudo apt-get update && sudo apt-get install -y build-essential bison flex zlib1g-dev libssl-dev', 'python -m pip install "psycopg[binary]==3.2.9"'),
    'mysql': ('sudo apt-get update && sudo apt-get install -y build-essential cmake ninja-build bison pkg-config libssl-dev libncurses-dev libtirpc-dev libudev-dev libaio-dev', 'python -m pip install PyMySQL==1.1.1'),
    'duckdb': ('sudo apt-get update && sudo apt-get install -y build-essential cmake ninja-build lld', ''),
    'datafusion': ('sudo apt-get update && sudo apt-get install -y build-essential pkg-config libssl-dev clang cmake', ''),
    'iceberg': ('sudo apt-get update && sudo apt-get install -y build-essential', 'python -m pip install pyspark==3.5.6'),
}
for name, (deps, pip) in software.items():
    paths = [f'upstream/{name}', '.gitmodules', f'ci/build-{name}.sh', 'tools/generate_data.py', 'sql/**', 'data/**', f'.github/workflows/{name}.yml']
    if name in {'postgres', 'mysql', 'duckdb'}:
        paths.append('tools/relational_demo.py')
    else:
        paths.append(f'tools/{name}_demo.py')
    if name == 'postgres':
        paths.extend(['plan-audit/**', 'pom.xml'])
    if name == 'iceberg':
        paths.append('ci/iceberg-submodule.init.gradle')
    extra = ''
    if name == 'datafusion':
        extra = '''      - name: Rust 1.88.0
        run: rustup toolchain install 1.88.0 --profile minimal && rustup default 1.88.0
        env:
          RUSTUP_MAX_RETRIES: '5'
'''
    if name in {'iceberg', 'postgres'}:
        extra = '''      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
'''
    audit = ''
    if name == 'postgres':
        audit = '''      - name: Audit actual PostgreSQL JSON with Java 17
        run: |
          mvn -B -ntp verify
          java -jar plan-audit/target/plan-audit-1.0.0.jar artifacts/pg-*.json > artifacts/pg-cardinality-audit.json
'''
    workflow = f'''name: {name}-source-lab
on:
  push:
    branches: [main]
    paths: {paths!r}
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: {name}-${{{{ github.ref }}}}
  cancel-in-progress: true
jobs:
  source-and-plan:
    runs-on: ubuntu-24.04
    timeout-minutes: 180
    env:
      CARGO_PROFILE_RELEASE_DEBUG: '0'
      CARGO_PROFILE_RELEASE_LTO: 'false'
    steps:
      - uses: actions/checkout@v4
      - name: Initialize only this pinned submodule
        run: git submodule update --init --depth 1 upstream/{name}
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
{extra}      - name: Dependencies
        run: |
          {deps}
          {pip or 'python --version'}
      - name: Record environment and generate public-schema data
        run: |
          mkdir -p artifacts
          git rev-parse HEAD > artifacts/repository-sha.txt
          git -C upstream/{name} rev-parse HEAD > artifacts/upstream-sha.txt
          uname -a > artifacts/runner.txt
          python tools/generate_data.py | tee artifacts/data-manifest.json
      - name: Build source and run plan experiments
        shell: bash
        run: |
          set -o pipefail
          bash ci/build-{name}.sh 2>&1 | tee artifacts/build-and-demo.log
{audit}      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: {name}-plans-${{{{ github.run_id }}}}
          path: artifacts/
          retention-days: 14
          if-no-files-found: error
'''
    path = Path(f'.github/workflows/{name}.yml')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(workflow, encoding='utf-8', newline='\n')
