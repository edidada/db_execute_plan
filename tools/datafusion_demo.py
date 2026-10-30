import csv
import os
import json
import subprocess
from pathlib import Path

out = Path('artifacts')
out.mkdir(exist_ok=True)
sql = """
CREATE EXTERNAL TABLE customer(c_custkey BIGINT,c_mktsegment VARCHAR) STORED AS CSV LOCATION 'data/generated/customer.csv' OPTIONS (format.has_header true);
CREATE EXTERNAL TABLE orders(o_orderkey BIGINT,o_custkey BIGINT,o_orderdate DATE,o_totalprice DOUBLE,o_orderstatus VARCHAR) STORED AS CSV LOCATION 'data/generated/orders.csv' OPTIONS (format.has_header true);
"""
query = "SELECT c_mktsegment,COUNT(*) AS n FROM customer JOIN orders ON c_custkey=o_custkey WHERE o_orderdate >= DATE '1995-07-01' GROUP BY c_mktsegment ORDER BY c_mktsegment"
(out / 'datafusion.sql').write_text(sql + 'EXPLAIN ANALYZE ' + query + ';\n' + query + ';\n')
(out / 'datafusion-result.sql').write_text(sql + query + ';\n')
binary = os.environ.get('PLANLAB_DATAFUSION_CLI', 'upstream/datafusion/target/release/datafusion-cli')
plan = subprocess.run([binary, '--file', str(out / 'datafusion.sql')], text=True, capture_output=True, check=True)
(out / 'datafusion-plan.txt').write_text(plan.stdout + plan.stderr)
result = subprocess.run([binary, '--quiet', '--format', 'csv', '--file', str(out / 'datafusion-result.sql')], text=True, capture_output=True, check=True)
(out / 'datafusion-result.csv').write_text(result.stdout)
(out / 'datafusion-result-stderr.txt').write_text(result.stderr)
rows = list(csv.reader(result.stdout.splitlines()))
segments = {'AUTOMOBILE', 'BUILDING', 'FURNITURE', 'MACHINERY', 'HOUSEHOLD'}
actual = [[r[0], int(r[1])] for r in rows if len(r) == 2 and r[0] in segments]
assert actual == json.loads(Path('data/generated/expected.json').read_text()), result.stdout + result.stderr
print('DataFusion result assertions passed')
