SELECT /* planlab_source_trace_e3 */ c.c_mktsegment, COUNT(*) AS n
FROM customer c JOIN orders o ON c.c_custkey=o.o_custkey
WHERE o.o_orderdate >= DATE '1995-07-01'
GROUP BY c.c_mktsegment ORDER BY c.c_mktsegment;
