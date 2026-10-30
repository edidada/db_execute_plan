SELECT /* planlab_source_trace_e3 */ c.c_mktsegment, SUM(per_customer.order_count) AS n
FROM customer AS c
JOIN (
    SELECT filtered.o_custkey, COUNT(*) AS order_count
    FROM (
        SELECT o.o_custkey
        FROM orders AS o
        WHERE o.o_orderdate >= DATE '1995-07-01'
    ) AS filtered
    GROUP BY filtered.o_custkey
) AS per_customer ON per_customer.o_custkey = c.c_custkey
GROUP BY c.c_mktsegment
ORDER BY c.c_mktsegment;
