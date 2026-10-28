
CREATE EXTERNAL TABLE customer(c_custkey BIGINT,c_mktsegment VARCHAR) STORED AS CSV LOCATION 'data/generated/customer.csv' OPTIONS (format.has_header true);
CREATE EXTERNAL TABLE orders(o_orderkey BIGINT,o_custkey BIGINT,o_orderdate DATE,o_totalprice DOUBLE,o_orderstatus VARCHAR) STORED AS CSV LOCATION 'data/generated/orders.csv' OPTIONS (format.has_header true);
SELECT c_mktsegment,COUNT(*) AS n FROM customer JOIN orders ON c_custkey=o_custkey WHERE o_orderdate >= DATE '1995-07-01' GROUP BY c_mktsegment ORDER BY c_mktsegment;
