"""Register official release gitlinks without downloading large source trees.

GitHub Actions performs the actual pinned checkout. Run from repository root.
Existing populated submodules should be updated by normal Git commands instead.
"""
import json
import subprocess
from pathlib import Path

repos = [
    ('postgres', 'postgres/postgres', 'REL_17_6'),
    ('mysql', 'mysql/mysql-server', 'mysql-8.4.6'),
    ('duckdb', 'duckdb/duckdb', 'v1.3.2'),
    ('datafusion', 'apache/datafusion', '49.0.2'),
    ('iceberg', 'apache/iceberg', 'apache-iceberg-1.9.2'),
]
records = []
for name, repo, tag in repos:
    commit = subprocess.check_output(['gh', 'api', f'repos/{repo}/commits/{tag}', '--jq', '.sha'], text=True).strip()
    path = 'upstream/' + name
    url = f'https://github.com/{repo}.git'
    for key, value in [('path', path), ('url', url), ('shallow', 'true')]:
        subprocess.run(['git', 'config', '-f', '.gitmodules', f'submodule.{path}.{key}', value], check=True)
    subprocess.run(['git', 'update-index', '--add', '--cacheinfo', '160000', commit, path], check=True)
    records.append({'name': name, 'repository': url, 'tag': tag, 'commit': commit, 'path': path})
    print(name, tag, commit, flush=True)
Path('versions.lock.json').write_text(json.dumps({'upstreams': records, 'java': '17', 'gradle': '8.14.3', 'spark': '3.5.6', 'scala': '2.12', 'rust': '1.88.0', 'python': '3.11'}, indent=2) + '\n', encoding='utf-8')
