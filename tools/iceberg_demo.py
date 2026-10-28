"""Spark 3.5.6 + source-built Iceberg 1.9.2 runtime, Java 17."""
from pathlib import Path
import json
from pyspark.sql import SparkSession

spark = (SparkSession.builder.master('local[2]').appName('planlab')
    .config('spark.sql.extensions', 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions')
    .config('spark.sql.catalog.lab', 'org.apache.iceberg.spark.SparkCatalog')
    .config('spark.sql.catalog.lab.type', 'hadoop')
    .config('spark.sql.catalog.lab.warehouse', str(Path('warehouse').resolve()))
    .config('spark.sql.shuffle.partitions', '2').getOrCreate())
out = Path('artifacts')
out.mkdir(exist_ok=True)
try:
    orders = spark.read.option('header', True).schema('o_orderkey LONG,o_custkey LONG,o_orderdate DATE,o_totalprice DECIMAL(12,2),o_orderstatus STRING').csv('data/generated/orders.csv')
    customers = spark.read.option('header', True).schema('c_custkey LONG,c_mktsegment STRING').csv('data/generated/customer.csv')
    orders.createOrReplaceTempView('src_orders')
    customers.createOrReplaceTempView('customer')
    spark.sql('CREATE NAMESPACE IF NOT EXISTS lab.demo')
    spark.sql('CREATE TABLE lab.demo.orders USING iceberg PARTITIONED BY (months(o_orderdate)) AS SELECT * FROM src_orders WHERE o_orderkey <= 90000')
    snapshot = spark.sql('SELECT snapshot_id FROM lab.demo.orders.snapshots ORDER BY committed_at DESC').first()[0]
    spark.sql('INSERT INTO lab.demo.orders SELECT * FROM src_orders WHERE o_orderkey > 90000')
    assert spark.sql(f'SELECT count(*) FROM lab.demo.orders VERSION AS OF {snapshot}').first()[0] == 90000
    assert spark.table('lab.demo.orders').count() == 100000
    query = "SELECT c_mktsegment,COUNT(*) n FROM customer JOIN lab.demo.orders ON c_custkey=o_custkey WHERE o_orderdate >= DATE '1995-07-01' GROUP BY c_mktsegment ORDER BY c_mktsegment"
    df = spark.sql(query)
    actual = [[r[0], r[1]] for r in df.collect()]
    assert actual == json.loads(Path('data/generated/expected.json').read_text())
    (out / 'iceberg-executed-plan.txt').write_text(df._jdf.queryExecution().executedPlan().toString())
    for name in ['files', 'snapshots', 'history', 'manifests']:
        spark.table(f'lab.demo.orders.{name}').coalesce(1).write.mode('overwrite').json(str(out / f'iceberg-{name}'))
    plan = spark.sql("EXPLAIN FORMATTED SELECT * FROM lab.demo.orders WHERE o_orderdate >= DATE '1995-12-01'")
    (out / 'iceberg-pruning-plan.txt').write_text('\n'.join(r[0] for r in plan.collect()))
    (out / 'iceberg-validation.json').write_text(json.dumps({'old_snapshot': snapshot, 'old_count': 90000, 'current_count': 100000, 'aggregate': actual}, indent=2))
    print('Iceberg snapshot and aggregate assertions passed', spark.version)
finally:
    spark.stop()
