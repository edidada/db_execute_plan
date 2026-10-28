# 参考文献、版本与知识点索引

文内 [K] 是知识点、[E] 是实验、[B] 是书籍、[P] 是论文、[D] 是官方技术文档。
文献用于支持机制与研究方法，不表示本项目复现了论文全部结果。无逐字大段转载。

## 书籍

| 编号 | 书籍 | 对应内容 |
|---|---|---|
| B1 | Silberschatz, Korth, Sudarshan, *Database System Concepts*, 7th ed., McGraw-Hill, 2019；中译《数据库系统概念》 | Query Processing、Query Optimization、Indexing 主题；K1–K5，E1–E3。不同译本页码不同，按章节主题定位 |
| B2 | Ramakrishnan, Gehrke, *Database Management Systems*, 3rd ed., McGraw-Hill, 2003 | Evaluation of Relational Operators、A Typical Relational Query Optimizer；K1/K4/K5 |
| B3 | Hellerstein, Stonebraker, Hamilton, *Architecture of a Database System*, Foundations and Trends in Databases 1(2), 2007, DOI [10.1561/1900000002](https://doi.org/10.1561/1900000002) | 查询处理器、存储与执行架构；K1/K3/K6 |
| B4 | Martin Kleppmann, *Designing Data-Intensive Applications*, 1st ed., O'Reilly, 2017，《设计数据密集型应用》 | Storage and Retrieval、Batch Processing；K6/K7。架构视角不替代具体版本执行计划手册 |

## 论文

| 编号 | 原始来源 | 本仓库使用的思想 |
|---|---|---|
| P1 | Selinger et al., *Access Path Selection in a Relational Database Management System*, SIGMOD 1979, [DOI](https://doi.org/10.1145/582095.582099) | 成本优化、动态规划、有用顺序；K1/K3 |
| P2 | Goetz Graefe, *Query Evaluation Techniques for Large Databases*, ACM Computing Surveys 25(2), 1993, [作者论文](https://web.stanford.edu/class/cs346/2014/graefe.pdf) | 迭代执行、联接、排序、聚合；K1/K5/K6 |
| P3 | Graefe, McKenna, *The Volcano Optimizer Generator: Extensibility and Efficient Search*, ICDE 1993, [DOI](https://doi.org/10.1109/ICDE.1993.344061) | 搜索空间、物理属性及可扩展优化；K1 |
| P4 | Leis et al., *How Good Are Query Optimizers, Really?*, PVLDB 9(3), 2015, pp.204–215, [原文](https://vldb.org/pvldb/vol9/p204-leis.pdf) | 基数估计误差、联接顺序与实验方法；K2/K8，E1/E3 |
| P5 | Boncz, Zukowski, Nes, *MonetDB/X100: Hyper-Pipelining Query Execution*, CIDR 2005, [作者原文](https://www.cidrdb.org/cidr2005/papers/P19.pdf) | 批量/向量化执行动机；K6，E3/E4。不声称 DuckDB/DataFusion 实现与 X100 完全一致 |
| P6 | Armbrust et al., *Lakehouse: A New Generation of Open Platforms that Unify Data Warehousing and Advanced Analytics*, CIDR 2021, [作者原文](https://cs.stanford.edu/~matei/papers/2021/cidr_lakehouse.pdf) | 开放格式与湖仓架构主张；K7。是架构论证，不是所有湖表系统同等性能的证明 |
| P7 | Armbrust et al., *Delta Lake: High-Performance ACID Table Storage over Cloud Object Stores*, PVLDB 13(12), 2020, [原文](https://www.vldb.org/pvldb/vol13/p3411-armbrust.pdf) | 表级事务日志、元数据与历史读取的另一设计；K7/K8。Iceberg 与 Delta 的元数据机制不同，不把 Delta 实现套到 Iceberg |

## 官方文档

| 编号 | 来源 | 使用范围 |
|---|---|---|
| D1 | [PostgreSQL 17 Using EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html)、[Planner Statistics](https://www.postgresql.org/docs/17/planner-stats.html) | 实际/估计、loops、统计与缓冲解释 |
| D2 | [MySQL 8.4 EXPLAIN](https://dev.mysql.com/doc/refman/8.4/en/explain.html)、[Hash Join](https://dev.mysql.com/doc/refman/8.4/en/hash-joins.html)、[EXPLAIN Output](https://dev.mysql.com/doc/refman/8.4/en/explain-output.html) | TREE、ANALYZE、访问方式与 Extra |
| D3 | [DuckDB EXPLAIN ANALYZE](https://duckdb.org/docs/stable/guides/meta/explain_analyze)、[DataFusion CLI](https://datafusion.apache.org/user-guide/cli/usage.html) | CLI 与指标；在线 stable 可能更新，实际语法以锁定源码及 CI 日志为准 |
| D4 | [Iceberg 1.9.2 Queries](https://iceberg.apache.org/docs/1.9.2/spark-queries/)、[Partitioning](https://iceberg.apache.org/docs/1.9.2/partitioning/)、[Specification](https://iceberg.apache.org/spec/) | 元数据表、时间旅行、隐式分区与表结构；spec 是演进文档，实验只使用 1.9.2 能力 |
| D5 | [Spark 3.5.6 Performance Tuning](https://spark.apache.org/docs/3.5.6/sql-performance-tuning.html) | AQE、分布与广播机制 |
| D6 | [Oracle 19c DBMS_XPLAN](https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_XPLAN.html) | DISPLAY、DISPLAY_CURSOR、权限与统计 |
| D7 | [SQL Server SHOWPLAN_XML](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-showplan-xml-transact-sql?view=sql-server-ver16)、[STATISTICS XML](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-statistics-xml-transact-sql?view=sql-server-ver16) | 批次限制与估计/实际计划 |
| D8 | [Db2 11.5 documentation](https://www.ibm.com/docs/en/db2/11.5.x) | 按 EXPLAIN_FROM_SECTION、MON_GET_PKG_CACHE_STMT、Section actuals、db2exfmt 条目检索；服务端配置按产品文档核实 |
| D9 | [TPC Current Specifications](https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp) | TPC-H 公开表定义来源，实验并非官方基准 |

## 中英文术语速查

| 中文 | English | 避免混淆 |
|---|---|---|
| 在线事务处理 | Online Transaction Processing, OLTP | 用户原请求 oatp 按 OLTP 解读 |
| 在线分析处理 | Online Analytical Processing, OLAP | 分析执行器不等于完整数据仓库 |
| 执行计划 | Execution Plan | 估计计划与实际计划均可存在 |
| 基数 / 选择率 | Cardinality / Selectivity | 行数与比例 |
| 成本优化器 | Cost-Based Optimizer, CBO | cost 不是可跨库比较的毫秒 |
| 谓词下推 / 投影裁剪 | Predicate Pushdown / Projection Pruning | 减少行 / 减少列 |
| 可搜索性 | SARGability | 与访问路径、表达式索引和版本相关 |
| 覆盖索引 / 回表 | Covering Index / Base-table Lookup | 覆盖不意味着所有引擎永不访问基表 |
| 数据倾斜 / 相关性 | Data Skew / Correlation | 单列非均匀 / 多列联合非独立 |
| 内存溢写 | Spill | 需观测批次、临时文件和内存 |
| 重分布 / 广播 | Shuffle or Repartition / Broadcast | 网络、复制与数据倾斜代价 |
| 表格式 / 文件格式 | Table Format / File Format | Iceberg / Parquet |
| 快照 / 时间旅行 | Snapshot / Time Travel | 元数据版本 / 指定历史版本读取 |
| 隐式分区 | Hidden Partitioning | 查询使用原始字段，规划器投影到分区转换 |
