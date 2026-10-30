"""Render the five independent software workflows; no compilation here."""
from pathlib import Path

for name in ['postgres', 'mysql', 'duckdb', 'datafusion', 'iceberg']:
    paths = [f'upstream/{name}', '.gitmodules', 'shell_scripts/common.sh', f'shell_scripts/build-{name}.sh', 'tools/generate_data.py', 'sql/workload.sql', 'data/**', f'.github/workflows/{name}.yml']
    paths.append('tools/relational_demo.py' if name in {'postgres', 'mysql', 'duckdb'} else f'tools/{name}_demo.py')
    if name == 'postgres':
        paths.extend(['plan-audit/**', 'pom.xml', 'shell_scripts/audit-postgres.sh'])
    if name == 'iceberg':
        paths.append('shell_scripts/iceberg-submodule.init.gradle')
    extra = ''
    if name in {'iceberg', 'postgres'}:
        extra = '''      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
'''
    audit = ''
    if name == 'postgres':
        audit = """      - name: Audit PostgreSQL plans
        run: bash shell_scripts/audit-postgres.sh --output-dir artifacts
"""
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
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
{extra}      - name: Build and run standalone Ubuntu lab
        run: bash shell_scripts/build-{name}.sh --install-deps --jobs 2 --output-dir artifacts
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
