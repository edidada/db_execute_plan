关系型db 执行计划 知识点，mysql pg oracle sqlserver db2总结

执行计划是关系型数据库性能调优的核心。不同数据库在生成、查看和解读执行计划上既有共通逻辑，也存在显著差异。以下按 MySQL、PostgreSQL、Oracle、SQL Server、DB2 分别总结其关键知识点。

### MySQL：EXPLAIN 为核心，关注访问类型与 Extra

MySQL 主要通过 `EXPLAIN` 语句查看执行计划，支持传统表格、JSON 格式，MySQL Workbench 还提供可视化视图。

解读时重点看这几列：**type**（访问类型，从好到坏依次为 `system` > `const` > `eq_ref` > `ref` > `range` > `index` > `ALL`，出现 `ALL` 通常意味着全表扫描，需关注索引优化）；**key**（实际使用的索引）；**rows**（预估扫描行数）；**Extra**（额外信息，如 `Using index` 表示覆盖索引，`Using temporary` / `Using filesort` 通常暗示需要优化排序或分组）。MySQL 8.0 起支持哈希联接，可视化图中菱形可能代表哈希联接而非嵌套循环。

### PostgreSQL：EXPLAIN 与 EXPLAIN ANALYZE 区分明确

PG 的 `EXPLAIN` 只显示预估计划，加上 `ANALYZE` 才会实际执行并返回真实运行时间与行数。这是与 MySQL 较大的不同：`EXPLAIN ANALYZE` 会执行语句，对 `INSERT/UPDATE/DELETE` 需放在事务中回滚以避免数据变更。

输出格式为树状节点，每个节点显示 `cost=启动成本..总成本`、`rows=预估行数`、`width=行宽`。关键节点类型包括 `Seq Scan`（全表扫描）、`Index Scan`、`Hash Join`、`Nested Loop`、`Merge Join`。通过对比预估 `rows` 与实际 `rows`（`ANALYZE` 输出中的 `actual` 值），可以判断统计信息是否准确。若偏差过大，应更新统计信息或排查数据倾斜。

### Oracle：EXPLAIN PLAN + DBMS_XPLAN，关注自适应计划

Oracle 使用 `EXPLAIN PLAN FOR` 将计划写入 `PLAN_TABLE`，再用 `DBMS_XPLAN.DISPLAY` 格式化输出。查看已执行语句的真实计划则用 `DBMS_XPLAN.DISPLAY_CURSOR`，可获取游标缓存中的实际执行统计。

核心关注点包括：**Operation**（操作类型，如 `TABLE ACCESS FULL`、`INDEX RANGE SCAN`、`HASH JOIN`）、**Rows**（CBO 预估行数）、**Cost**（优化器估算成本）、**Predicate Information**（谓词过滤条件）。Oracle 的**自适应执行计划**（Adaptive Plan）会在运行时根据实际数据分布调整计划，`DBMS_XPLAN` 的 `ADAPTIVE` 格式可显示最终计划与动态调整痕迹。绑定变量窥探可能导致计划不稳定，需留意 `EXPLAIN PLAN` 输出可能不代表真实执行计划（尤其涉及绑定变量类型转换时）。

### SQL Server：图形化与 DMV 结合，区分估计/实际计划

SQL Server 提供两种计划：**估计的执行计划**（不运行查询，基于统计信息）和**实际的执行计划**（运行查询，包含实际行数与耗时）。SSMS 中可图形化查看，也可用 `SET SHOWPLAN_XML ON`（估计）或 `SET STATISTICS XML ON`（实际）获取。

执行计划从右到左、从上到下阅读。重点排查：**表扫描/索引扫描**在大型表上是否必要；**键查找**（Key Lookup）是否频繁出现（可通过覆盖索引消除）；**估计行数与实际行数**的巨大差异（通常指向统计信息过时）；**粗箭头**（表示大量数据流经该操作符）。SQL Server 还会在图形计划中直接给出缺失索引建议（Missing Index），但需权衡写入开销，不可盲目采纳。

### DB2：通过 Explain 表与监控函数获取计划

DB2 获取执行计划的常见方式包括：使用 `EXPLAIN` 命令将计划写入 Explain 表，或通过 `db2exfmt` 格式化输出；对于动态 SQL，可使用 `MON_GET_PKG_CACHE_STMT` 等监控函数获取包缓存中的实际访问计划。`EXPLAIN_FROM_SECTION` 可从可执行 ID 提取计划。

调优时关注操作符的**总成本**与**I/O 成本**占比。若某表的 I/O 成本贡献比例异常高，往往是索引缺失或统计信息不准的信号。DB2 优化器对统计信息敏感，应确保 `RUNSTATS` 定期执行。此外，DB2 的访问计划缓存（Package Cache）可能因统计信息更新或配置变更而失效，需结合监控数据判断计划是否发生了非预期的变更。

### 跨库共性要点

无论哪种数据库，执行计划调优的通用思路是：**先看访问路径**（是否走了低效的全表扫描/全索引扫描，能否通过索引改为 Seek/Range Scan），**再看联接方式与顺序**（嵌套循环适合小结果集驱动大表并走索引，哈希联接适合大表间等值联接且无有效索引，合并联接适合已排序的大表），**最后对比预估与实际**（偏差大则更新统计信息或检查参数嗅探/绑定变量窥探）。各库的“成本”模型不同，同一查询在不同库上的最优计划也可能不同，跨库迁移时执行计划需重新验证。
