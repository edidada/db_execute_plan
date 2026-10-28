"""Query gh for the latest run of each lab and save an explicit status snapshot."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

runs = json.loads(subprocess.check_output([
    'gh', 'run', 'list', '--limit', '100', '--json',
    'databaseId,workflowName,status,conclusion,headSha,url,createdAt,updatedAt'
], text=True))
names = [f'{name}-source-lab' for name in ['postgres', 'mysql', 'duckdb', 'datafusion', 'iceberg']] + ['java17-plan-audit']
latest = {}
for run in runs:
    if run['workflowName'] in names:
        latest.setdefault(run['workflowName'], run)
snapshot = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'latest_runs': latest}
Path('docs/ci-status.json').write_text(json.dumps(snapshot, indent=2) + '\n', encoding='utf-8')
lines = [
    '## 实时检查快照', '',
    f"检查时间 UTC：`{snapshot['checked_at_utc']}`。这是该时刻的状态，不承诺之后不变。", '',
    '| 工作流 | 最新 run | 源码提交 | 状态 |',
    '|---|---|---|---|',
]
for name in names:
    run = latest.get(name)
    if run is None:
        lines.append(f'| {name} | 无记录 | — | 未验证 |')
        continue
    status = run['conclusion'] if run['status'] == 'completed' else run['status']
    lines.append(f"| {name} | [{run['databaseId']}]({run['url']}) | `{run['headSha'][:7]}` | {status} |")
lines += ['', 'success 才表示该 run 完成验收；in_progress/queued 未完成。failure 需看实际失败日志；cancelled 表示取消，不能当作通过。', '',
          '复查：`python tools/ci_status.py`；排错：`gh run view <RUN_ID> --log-failed`。原始状态保存在 [ci-status.json](ci-status.json)。', '']
path = Path('docs/06-delivery.md')
intro = path.read_text(encoding='utf-8').split('## 实时检查快照')[0]
path.write_text(intro.rstrip() + '\n\n' + '\n'.join(lines), encoding='utf-8')
for name in names:
    r = latest.get(name, {})
    print(name, r.get('databaseId'), r.get('status'), r.get('conclusion'))
