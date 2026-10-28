-- E1: Same query shape, hot versus cold key.
SELECT COUNT(*) FROM orders WHERE o_custkey = 1;
SELECT COUNT(*) FROM orders WHERE o_custkey = 1001;
-- E2: SARGability; compare actual plan, do not assume the rewrite wins.
SELECT COUNT(*) FROM orders WHERE EXTRACT(YEAR FROM o_orderdate) = 1995;
SELECT COUNT(*) FROM orders WHERE o_orderdate >= DATE '1995-01-01' AND o_orderdate < DATE '1996-01-01';
-- E3: Join, predicate pushdown, aggregation and ordering.
SELECT c.c_mktsegment, COUNT(*) AS n
FROM customer c JOIN orders o ON c.c_custkey = o.o_custkey
WHERE o.o_orderdate >= DATE '1995-07-01'
GROUP BY c.c_mktsegment ORDER BY c.c_mktsegment;
