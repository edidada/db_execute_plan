"""Verify completed GitHub runs and their artifacts; never compiles locally.

Requires gh authentication. Writes a durable JSON report and selected raw evidence.
Exit 0 only when all six latest workflows have successful, verified artifacts.
"""
import csv
import io
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

def gh(*args):
    return subprocess.check_output(['gh', *args], text=True, encoding='utf-8')

names = ['postgres', 'mysql', 'duckdb', 'datafusion', 'iceberg', 'java']
workflow_names = {n: n + '-source-lab' for n in names[:-1]}
workflow_names['java'] = 'java17-plan-audit'
runs = json.loads(gh('run', 'list', '--branch', 'main', '--limit', '100', '--json', 'databaseId,workflowName,status,conclusion,headSha,url'))
lock = {r['name']: r for r in json.loads(Path('versions.lock.json').read_text())['upstreams']}
report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
          'branch': 'main',
          'reviewed_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
          'local_compilation': False, 'workflows': {}}

def verify(name):
    run = next(r for r in runs if r['workflowName'] == workflow_names[name])
    result = {'run': run, 'accepted': False}
    if run['status'] != 'completed' or run['conclusion'] != 'success':
        result['reason'] = 'Latest run has not completed successfully'
        return name, result
    subprocess.run(['git', 'merge-base', '--is-ancestor', run['headSha'], 'HEAD'], check=True)
    details = json.loads(gh('run', 'view', str(run['databaseId']), '--json', 'jobs'))
    assert details['jobs'] and all(j['conclusion'] == 'success' for j in details['jobs']), details
    dest = Path('artifacts/acceptance') / name / str(run['databaseId'])
    dest.mkdir(parents=True, exist_ok=True)
    if not (dest / '.downloaded').exists():
        gh('run', 'download', str(run['databaseId']), '--dir', str(dest))
        (dest / '.downloaded').touch()
    evidence = Path('docs/evidence') / f"{name}-{run['databaseId']}"
    evidence.mkdir(parents=True, exist_ok=True)
    if name == 'java':
        xmls = list(dest.rglob('TEST-*.xml'))
        assert xmls, 'Maven test report missing'
        suites = [ET.parse(p).getroot() for p in xmls]
        assert sum(int(s.attrib['tests']) for s in suites) == 2
        assert all(int(s.attrib.get(k, 0)) == 0 for s in suites for k in ['failures', 'errors', 'skipped'])
        html = next(dest.rglob('index.html')).read_text(encoding='utf-8')
        for field, number in [('tests', '2'), ('failures', '0'), ('ignored', '0')]:
            assert re.search(r'id="' + field + r'">\s*<div class="counter">' + number + r'</div>', html)
        jar = next(p for p in dest.rglob('plan-audit-1.0.0.jar') if 'original-' not in p.name)
        with zipfile.ZipFile(jar) as archive:
            assert 'io/github/edidada/plan/PlanAudit.class' in archive.namelist()
        assert list(dest.rglob('*.zip')), 'Gradle application distribution missing'
        for p in xmls:
            shutil.copyfile(p, evidence / p.name)
        (evidence / 'gradle-test-summary.html').write_text(html, encoding='utf-8')
        result['checks'] = {'maven_tests': 2, 'gradle_tests': 2, 'test_failures': 0, 'shaded_jar': True, 'gradle_distribution': True}
    else:
        root = next(p for p in dest.iterdir() if p.is_dir())
        assert (root / 'repository-sha.txt').read_text().strip() == run['headSha']
        assert (root / 'upstream-sha.txt').read_text().strip() == lock[name]['commit']
        manifest = json.loads((root / 'data-manifest.json').read_text())
        assert manifest['customers'] == 1001 and manifest['orders'] == 100000
        expected = [[k, v] for k, v in sorted(manifest['expected'].items())]
        log = (root / 'build-and-demo.log').read_text(encoding='utf-8')
        checks = {'upstream_sha_matches_lock': True, 'dataset_orders': 100000, 'dataset_customers': 1001}
        checks['source_tag'] = lock[name]['tag']
        if (root / 'server-version.txt').exists():
            checks['reported_version'] = (root / 'server-version.txt').read_text().strip()
        if name in {'postgres', 'mysql', 'duckdb'}:
            assert f'{name} result assertions passed' in log
            plans = json.loads((root / f'{name}-plans.json').read_text())
            assert len(plans) == 10
            assert {(p['phase'], p['experiment']) for p in plans} == {(s, i) for s in ['before-index', 'after-index'] for i in range(1, 6)}
            assert all(p['plan'] for p in plans)
            checks['actual_plans'] = 10
            if name == 'postgres':
                assert len(json.loads((root / 'pg-cardinality-audit.json').read_text())) == 10
                assert len(list(root.glob('pg-before-index-*.json'))) == 5
                assert len(list(root.glob('pg-after-index-*.json'))) == 5
                checks['java_actual_plan_audit'] = True
            if name == 'duckdb':
                assert (root / 'orders.parquet').stat().st_size > 0
                assert (root / 'duckdb-source-cli.txt').read_text().strip().splitlines()[-1] == '100000'
                assert (root / 'duckdb-parquet-plan.txt').stat().st_size > 0
                checks['parquet_and_source_cli'] = True
                # A shallow checkout may lack Git tags: do not invent a clean
                # release label. Source identity is verified by the gitlink SHA.
                checks['release_label_matches_tag'] = 'v1.3.2' in checks['reported_version']
        elif name == 'datafusion':
            assert 'DataFusion result assertions passed' in log
            rows = list(csv.reader(io.StringIO((root / 'datafusion-result.csv').read_text())))
            assert [[r[0], int(r[1])] for r in rows[1:]] == expected
            plan = (root / 'datafusion-plan.txt').read_text()
            assert 'Error during' not in plan and 'SQL error' not in plan
            assert 'output_rows' in plan
            checks['aggregate_groups'] = 5
        elif name == 'iceberg':
            assert 'Iceberg snapshot and aggregate assertions passed' in log
            validation = json.loads((root / 'iceberg-validation.json').read_text())
            assert validation['old_count'] == 90000 and validation['current_count'] == 100000
            assert validation['aggregate'] == expected
            assert 'isFinalPlan=true' in (root / 'iceberg-executed-plan.txt').read_text()
            snapshots = [json.loads(line) for p in (root / 'iceberg-snapshots').glob('part-*.json') for line in p.read_text().splitlines()]
            assert len(snapshots) == 2
            checks.update({'snapshots': 2, 'old_count': 90000, 'current_count': 100000, 'final_aqe_plan': True})
        # Keep compact raw evidence, not binaries, data files or very large build logs.
        for p in root.rglob('*'):
            if p.is_file() and p.name != 'build-and-demo.log' and p.suffix in {'.json', '.csv', '.txt', '.sql'}:
                target = evidence / p.relative_to(root)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, target)
        markers = [line for line in log.splitlines() if 'assertions passed' in line or 'BUILD SUCCESS' in line or 'Finished `release`' in line]
        (evidence / 'validation-markers.txt').write_text('\n'.join(markers) + '\n', encoding='utf-8')
        result['checks'] = checks
    result['accepted'] = True
    result['evidence'] = evidence.as_posix()
    return name, result

def safe_verify(name):
    try:
        return verify(name)
    except Exception as error:
        return name, {'accepted': False, 'reason': str(error), 'error_type': type(error).__name__}

with ThreadPoolExecutor(max_workers=3) as pool:
    for name, result in pool.map(safe_verify, names):
        report['workflows'][name] = result
        print(name, 'PASS' if result['accepted'] else 'NOT ACCEPTED', result.get('reason', result.get('checks')))
report['all_accepted'] = all(r['accepted'] for r in report['workflows'].values())
Path('docs/acceptance.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
raise SystemExit(0 if report['all_accepted'] else 1)
