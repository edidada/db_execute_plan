CREATE INDEX orders_customer_date ON orders(o_custkey,o_orderdate);
CREATE INDEX orders_date ON orders(o_orderdate);
ANALYZE TABLE customer;
ANALYZE TABLE orders;
