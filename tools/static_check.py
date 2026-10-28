"""Read-only structural checks. Does not compile or run database/Java code."""
import ast
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]
for p in (root / 'tools').glob('*.py'):
    ast.parse(p.read_text(encoding='utf-8-sig'), filename=str(p))
for p in [root / 'pom.xml', root / 'plan-audit/pom.xml']:
    ET.parse(p)
for p in (root / '.github/workflows').glob('*.yml'):
    doc = yaml.load(p.read_text(), Loader=yaml.BaseLoader)
    assert 'on' in doc and 'jobs' in doc, p
    assert 'workflow_dispatch' in doc['on'], p
for p in [root / 'README.md', *(root / 'docs').glob('*.md'), root / 'data/README.md']:
    for link in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
        if '://' in link or link.startswith('#'):
            continue
        target = (p.parent / link.split('#')[0]).resolve()
        assert target.exists(), (p, link)
if (root / 'versions.lock.json').exists():
    lock = json.loads((root / 'versions.lock.json').read_text())
    assert len(lock['upstreams']) == 5
    assert all(re.fullmatch('[0-9a-f]{40}', r['commit']) for r in lock['upstreams'])
    for record in lock['upstreams']:
        entry = subprocess.check_output(['git', 'ls-files', '--stage', '--', record['path']], cwd=root, text=True).split()
        assert entry[:2] == ['160000', record['commit']], (record['path'], entry)
print('PASS: Python AST, Maven XML, workflow YAML, Markdown local links and version lock structure; no compilation')
