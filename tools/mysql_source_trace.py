"""Only run against the isolated source-built Debug server in CI."""
import csv
import json
import os
from pathlib import Path
import pymysql

out = Path('artifacts/mysql-source-trace')
sql_dir = Path('sql/mysql-source-trace')
con = pymysql.connect(unix_socket=os.environ['PLANLAB_SOCKET'], user='root', autocommit=True)

def file_sql(name):
    return (sql_dir / name).read_text(encoding='utf-8').strip()

def batch(name):
    with con.cursor() as cur:
        for statement in file_sql(name).split(';'):
            if statement.strip():
                cur.execute(statement)

def run(statement):
    with con.cursor() as cur:
        cur.execute(statement)
        return cur.fetchall() if cur.description else []

try:
    batch('schema.sql')
    for table in ['customer', 'orders']:
        with Path(f'data/generated/{table}.csv').open() as stream:
            rows = list(csv.reader(stream))[1:]
        with con.cursor() as cur:
            for start in range(0, len(rows), 5000):
                cur.executemany(f"INSERT INTO {table} VALUES ({','.join(['%s'] * len(rows[0]))})", rows[start:start+5000])
    expected = json.loads(Path('data/generated/expected.json').read_text())
    context = run('SELECT VERSION(), CONNECTION_ID(), @@optimizer_switch')
    (out / 'session.json').write_text(json.dumps(context, indent=2))
    results = []
    query = file_sql('query.sql').rstrip(';')
    for phase in ['before-index', 'after-index']:
        if phase == 'after-index':
            batch('indexes.sql')
        else:
            run('ANALYZE TABLE customer')
            run('ANALYZE TABLE orders')
        # Native ast keyword prints query tree and PrintQueryPlan; t traces
        # existing DBUG_TRACE entries. Enable only after loading the dataset.
        debug_path = str((out / f'{phase}.dbug').resolve())
        functions = ','.join(['dispatch_sql_command', 'parse_sql', 'mysql_execute_command',
                              'Sql_cmd_dml::prepare', 'Sql_cmd_dml::execute',
                              'Query_expression::prepare', 'Query_block::prepare',
                              'Query_expression::optimize', 'JOIN::optimize',
                              'JOIN::make_join_plan', 'Optimize_table_order::choose_table_order',
                              'Query_expression::execute'])
        debug = f'd,ast:t:i:F:L:f,{functions}:O,{debug_path}'
        (out / f'{phase}-debug-on.sql').write_text("SET SESSION debug='" + debug + "';\n")
        run('SET SESSION debug=%s' % ("'" + debug + "'"))
        batch('trace-on.sql')
        rows = run(query)
        trace_rows = run(file_sql('trace-read.sql'))
        batch('trace-off.sql')
        run("SET SESSION debug=''")
        actual = [[str(segment), int(count)] for segment, count in rows]
        assert actual == expected, actual
        assert len(trace_rows) == 1, trace_rows
        statement, trace, missing, denied = trace_rows[0]
        assert 'planlab_source_trace_e3' in statement
        assert missing == 0 and denied == 0, (missing, denied)
        parsed = json.loads(trace)
        assert 'join_optimization' in trace and 'considered_execution_plans' in trace
        (out / f'{phase}-optimizer-trace.json').write_text(json.dumps(parsed, indent=2))
        (out / f'{phase}-trace-metadata.json').write_text(json.dumps({'query': statement, 'missing_bytes': missing, 'insufficient_privileges': denied}, indent=2))
        plan = run('EXPLAIN ANALYZE ' + query)
        (out / f'{phase}-explain-analyze.txt').write_text('\n'.join(str(r[0]) for r in plan) + '\n')
        results.append({'phase': phase, 'aggregate': actual, 'trace_complete': True})
        print(phase, 'EXPLAIN ANALYZE:', *[r[0] for r in plan], sep='\n', flush=True)
        for keyword in ['JOIN::optimize', 'choose_table_order', 'Query plan:']:
            assert keyword in Path(debug_path).read_text(errors='replace'), keyword
    (out / 'validation.json').write_text(json.dumps({'passed': True, 'results': results}, indent=2))
    print('PASS: query results, complete optimizer traces, actual plans and native DBUG markers', flush=True)
finally:
    con.close()
