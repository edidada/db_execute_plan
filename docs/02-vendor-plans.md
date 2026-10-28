# 五种传统 RDBMS：版本、入口、陷阱

源码实验锁定 PostgreSQL 17.6 与 MySQL 8.4.6。以下商业产品语法讨论以 Oracle Database 19c、SQL Server 2022（16.x）、Db2 LUW 11.5 为范围；没有运行这些产品，不提供虚构计划。

## PostgreSQL 17.6

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT JSON)
SELECT count(*) FROM orders WHERE o_custkey = 1001;
```

只写 EXPLAIN 不执行；ANALYZE 选项会实际执行。`cost=startup..total` 为内部成本，`rows` 为节点输出估计，不是扫描页数。实际行数结合 loops，Buffers 与 Heap Fetches 一起读；并行计划还要检查各 worker。`Rows Removed by Filter` 不等同于全查询总过滤行数，也要结合循环。[D1]

`ANALYZE orders` 更新统计信息，`EXPLAIN ANALYZE` 测实际执行，它们不是同一命令。`CREATE STATISTICS ... (dependencies, mcv, ndistinct)` 能帮助多列同表相关性，但不能视为通用跨表相关性模型。计划缓存可选定制计划（Custom Plan）或通用计划（Generic Plan），热点/冷点差异使选择敏感。实验默认直发 SQL，未声称验证参数缓存行为。

读源码：`costsize.c` 看估算如何影响选择，`selfuncs.c` 看选择率，`nodeNestloop.c/nodeHashjoin.c` 看真正执行。E1/E2/E3 导出 JSON，Java 工具针对 PG 17 语义算平滑 Q-error。

## MySQL 8.4.6 / InnoDB

```sql
EXPLAIN FORMAT=JSON SELECT count(*) FROM orders WHERE o_custkey = 1001;
EXPLAIN ANALYZE SELECT count(*) FROM orders WHERE o_custkey = 1001;
ANALYZE TABLE orders;
```

`EXPLAIN ANALYZE` 从 8.0.18 起可用，会执行支持的语句，本项目只解释 SELECT。8.4 的实际计划使用 TREE 输出，不能把 `FORMAT=JSON` 普通估计计划当实际执行统计。[D2]

`type` 的 system/const/eq_ref/ref/range/index/ALL 描述访问方式，不能构造对所有查询成立的“从好到坏”排行。`rows`、`filtered` 是估算；`key` 是选用索引，不代表所有列都参与范围定位。`Using index` 通常表示覆盖读取，`Using index condition` 是索引条件下推（Index Condition Pushdown, ICP），两者不同。`Using filesort` 不自动证明磁盘排序。

优化器还会考虑直方图、索引统计、范围估计与联接顺序。8.4 的哈希联接规则不应套用 5.7 的 Block Nested Loop 经验。`sql/join_optimizer/` 与 `sql/iterators/` 分别对应决策与执行，InnoDB 二级索引回表要继续读 `storage/innobase/`。[D2]

## Oracle Database 19c

```sql
EXPLAIN PLAN FOR SELECT * FROM orders WHERE o_custkey = 1001;
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(NULL,NULL,'TYPICAL +PREDICATE'));
-- 实际执行时收集 row-source statistics，随后读取该游标：
SELECT /*+ gather_plan_statistics */ count(*) FROM orders WHERE o_custkey = 1001;
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR(NULL,NULL,'ALLSTATS LAST +PREDICATE'));
```

`EXPLAIN PLAN` 写入 PLAN_TABLE，估计计划可能与带真实绑定类型、会话环境的缓存游标不同。实际统计需要执行时收集、正确 SQL_ID/child number 与权限；`NULL,NULL` 依赖当前会话最近游标，自动化工具若插入别的 SQL 应显式指定游标。比较 E-Rows/A-Rows 时关注 Starts，Predicate Information 中 access 与 filter 的位置不同。[D6]

绑定变量窥探（Bind Peeking）与自适应游标共享（Adaptive Cursor Sharing）可能产生不同子游标。自适应计划（Adaptive Plan）只在支持的候选决策范围内生效，不是运行时任意重新排列整个查询。DISPLAY_CURSOR 的 ADAPTIVE 格式用于诊断候选和最终分支，具体输出受配置及执行阶段影响。没有官方开放源码内核可作为本仓库 submodule。

## SQL Server 2022

```sql
SET SHOWPLAN_XML ON;
GO
SELECT count(*) FROM dbo.orders WHERE o_custkey = 1001;
GO
SET SHOWPLAN_XML OFF;
GO
SET STATISTICS IO ON;
SET STATISTICS TIME ON;
SET STATISTICS XML ON;
SELECT count(*) FROM dbo.orders WHERE o_custkey = 1001;
SET STATISTICS XML OFF;
```

SHOWPLAN_XML 不执行查询，SET 要作为其批次唯一语句；`GO` 是 SSMS/sqlcmd 客户端批处理分隔符，不是服务器 T-SQL。STATISTICS XML 则执行并返回实际 XML；还需 SHOWPLAN 权限。图形通常按右到左的数据流理解，XML 的 RelOp 树比截图更适合自动分析。[D7]

Index Seek 不意味着少工作：残余谓词（Residual Predicate）可能使实际读取远超输出；Key Lookup 的次数可能成为主耗时。Memory Grant、Spill、估计/实际行数、并行交换、逻辑读一起检查。缺失索引建议没有全面计入既有索引合并与写开销，不能直接照单新增。

参数嗅探（Parameter Sniffing）与 SQL Server 2022 的 Parameter Sensitive Plan 优化必须结合兼容级别和功能限制；不能把 2022 特性描述为所有旧版本都具有。Query Store 可观察计划历史，历史回归证据与单次 SSMS 图不同。

## Db2 LUW 11.5

```sql
-- Explain 表需先按当前用户/数据库版本初始化。
EXPLAIN PLAN FOR SELECT count(*) FROM orders WHERE o_custkey = 1001;
-- 命令行再运行 db2exfmt 格式化 Explain 表，数据库与输出路径自行指定。
-- db2exfmt -d LABDB -1 -o plan.txt
RUNSTATS ON TABLE LAB.ORDERS WITH DISTRIBUTION AND DETAILED INDEXES ALL;
```

`MON_GET_PKG_CACHE_STMT` 提供包缓存 statement/section 的监控指标与 executable ID，**不是调用后就直接返回完整实际算子计划**。`EXPLAIN_FROM_SECTION` 可提取 section 的 Explain 数据，再使用 db2exfmt；算子实际行数等 section actuals 还依赖相应收集配置、运行范围与工具支持。需把 statement 累计指标、section 计划和算子实际统计分开。[D8]

TBSCAN、IXSCAN、FETCH、NLJOIN、HSJOIN、MSJOIN 表示访问/联接实现。timeron 是成本单位，不是毫秒。RUNSTATS、相关列统计、参数分布和 package cache 状态都可能改变选择；统计更新与缓存失效不能简单描述为所有语句必然立即重编译。

## 执行边界

EXPLAIN ANALYZE/实际计划可能运行昂贵查询。只在隔离实验库运行本项目提供的 SELECT。事务回滚也不能撤销外部函数副作用、序列消耗等所有影响；因此“写语句包上 ROLLBACK 就完全安全”不成立。本仓库不对生产写 SQL 执行实际计划采样。
