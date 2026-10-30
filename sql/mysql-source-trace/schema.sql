CREATE DATABASE planlab;
USE planlab;
CREATE TABLE customer (
  c_custkey INTEGER PRIMARY KEY,
  c_mktsegment VARCHAR(20) NOT NULL
) ENGINE=InnoDB;
CREATE TABLE orders (
  o_orderkey INTEGER PRIMARY KEY,
  o_custkey INTEGER NOT NULL,
  o_orderdate DATE NOT NULL,
  o_totalprice DECIMAL(12,2) NOT NULL,
  o_orderstatus CHAR(1) NOT NULL
) ENGINE=InnoDB;
