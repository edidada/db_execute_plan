"""Deterministic TPC-H-shaped subset, NOT a TPC-H benchmark."""
import csv
import json
from datetime import date, timedelta
from pathlib import Path

out = Path('data/generated')
out.mkdir(parents=True, exist_ok=True)
segments = ['AUTOMOBILE', 'BUILDING', 'FURNITURE', 'MACHINERY', 'HOUSEHOLD']
with (out / 'customer.csv').open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['c_custkey', 'c_mktsegment'])
    w.writerows((k, segments[k % 5]) for k in range(1, 1002))
counts = {s: 0 for s in segments}
with (out / 'orders.csv').open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['o_orderkey', 'o_custkey', 'o_orderdate', 'o_totalprice', 'o_orderstatus'])
    for k in range(1, 100001):
        customer = 1 if k <= 90000 else 2 + (k - 90001) % 1000
        day = date(1995, 1, 1) + timedelta(days=k % 365)
        cents = 10000 + k % 100000
        w.writerow([k, customer, day.isoformat(), f'{cents // 100}.{cents % 100:02d}', 'F' if k % 3 else 'O'])
        if day >= date(1995, 7, 1):
            counts[segments[customer % 5]] += 1
(out / 'expected.json').write_text(json.dumps(sorted(counts.items()), indent=2))
print(json.dumps({'customers': 1001, 'orders': 100000, 'expected': counts}))
