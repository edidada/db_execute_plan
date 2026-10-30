"""CI lab SQL only. PostgreSQL/MySQL use the source-built server."""
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

engine = sys.argv[1]
out = Path('artifacts')
out.mkdir(exist_ok=True)
text = '\n'.join(l for l in Path('sql/workload.sql').read_text().splitlines() if not l.startswith('--'))
statements = [s.strip() for s in text.split(';') if s.strip()]
if engine == 'duckdb':
    class SourceDuckDB:
        def execute(self, sql):
            proc = subprocess.run([os.environ['DUCKDB_CLI'], 'artifacts/duckdb.db', '-json', '-c', sql], capture_output=True, text=True, check=True)
            # DuckDB 1.3.2 shell renders EXPLAIN specially, even with -json.
            # Preserve that raw plan; parse JSON only for ordinary result sets.
            if sql.lstrip().upper().startswith('EXPLAIN'):
                self.rows = [(proc.stdout,)]
            else:
                self.rows = [tuple(r.values()) for r in json.loads(proc.stdout or '[]')]
            return self
        def fetchall(self):
            return self.rows
        def close(self):
            pass
    con = SourceDuckDB()
    con.execute("CREATE TABLE customer AS SELECT * FROM read_csv_auto('data/generated/customer.csv')")
    con.execute("CREATE TABLE orders AS SELECT * FROM read_csv_auto('data/generated/orders.csv')")
else:
    if engine == 'postgres':
        import psycopg
        con = psycopg.connect(host=os.environ.get('PLANLAB_PG_HOST', 'localhost'), port=5432, dbname='planlab', user='runner', autocommit=True)
    else:
        import pymysql
        connection = {'unix_socket': os.environ['PLANLAB_SOCKET']} if os.environ.get('PLANLAB_SOCKET') else {'host': '127.0.0.1'}
        con = pymysql.connect(**connection, user='root', database='planlab', autocommit=True)
    cur = con.cursor()
    cur.execute('CREATE TABLE customer(c_custkey INTEGER PRIMARY KEY,c_mktsegment VARCHAR(20))')
    cur.execute('CREATE TABLE orders(o_orderkey INTEGER PRIMARY KEY,o_custkey INTEGER,o_orderdate DATE,o_totalprice DECIMAL(12,2),o_orderstatus CHAR(1))')
    for table in ['customer', 'orders']:
        with Path(f'data/generated/{table}.csv').open() as f:
            rows = list(csv.reader(f))[1:]
        for start in range(0, len(rows), 5000):
            cur.executemany(f"INSERT INTO {table} VALUES ({','.join(['%s'] * len(rows[0]))})", rows[start:start+5000])
    cur.close()

def execute(sql):
    if engine == 'duckdb':
        return con.execute(sql).fetchall()
    with con.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall() if cur.description else []

def analyze():
    if engine == 'mysql':
        for table in ['customer', 'orders']:
            execute('ANALYZE TABLE ' + table)
    else:
        execute('ANALYZE')

analyze()
log = []
for phase in ['before-index', 'after-index']:
    if phase == 'after-index':
        execute('CREATE INDEX orders_customer_date ON orders(o_custkey,o_orderdate)')
        execute('CREATE INDEX orders_date ON orders(o_orderdate)')
        analyze()
    for i, sql in enumerate(statements):
        prefix = 'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' if engine == 'postgres' else 'EXPLAIN ANALYZE '
        plan = execute(prefix + sql)
        log.append({'phase': phase, 'experiment': i+1, 'sql': sql, 'plan': plan})
        if engine == 'postgres':
            (out / f'pg-{phase}-{i+1}.json').write_text(json.dumps(plan[0][0], indent=2))
        rows = execute(sql)
        if i < 4:
            assert int(rows[0][0]) == [90000, 10, 100000, 100000][i], (sql, rows)
        else:
            actual = [[str(s), int(n)] for s, n in rows]
            expected = json.loads(Path('data/generated/expected.json').read_text())
            assert actual == expected, (actual, expected)
(out / f'{engine}-plans.json').write_text(json.dumps(log, default=str, indent=2))
if engine == 'duckdb':
    execute("COPY (SELECT * FROM orders ORDER BY o_orderdate) TO 'artifacts/orders.parquet' (FORMAT PARQUET, ROW_GROUP_SIZE 10000)")
    rows = execute("EXPLAIN ANALYZE SELECT COUNT(*) FROM read_parquet('artifacts/orders.parquet') WHERE o_orderdate >= DATE '1995-12-01'")
    (out / 'duckdb-parquet-plan.txt').write_text(str(rows))
    cli = subprocess.run([os.environ['DUCKDB_CLI'], '-csv', '-c', "SELECT COUNT(*) AS n FROM read_csv_auto('data/generated/orders.csv');"], capture_output=True, text=True, check=True)
    assert cli.stdout.strip().splitlines()[-1] == '100000', cli.stdout
    (out / 'duckdb-source-cli.txt').write_text(cli.stdout)
con.close()
print(engine, 'result assertions passed; inspect artifacts for plan choices')
