# 固定版本与源码阅读路线

以下标签是教学复现基线，不表示“当前最新版”或安全维护建议。**gitlink 提交是最终权威**，完整 SHA 见 `versions.lock.json`。
submodule URL 均为官方项目，许可证保留在各上游目录中，不能假设父仓库能改变其许可证。

| 类别 | 软件 / 标签 | 源码入口（相对 submodule） | 要回答的问题 |
|---|---|---|---|
| OLTP RDBMS | PostgreSQL REL_17_6 | `src/backend/optimizer/path/costsize.c`、`src/backend/utils/adt/selfuncs.c` | 估计如何变成路径成本？K2/K3 |
| OLTP RDBMS | PostgreSQL REL_17_6 | `src/backend/optimizer/path/joinrels.c`、`src/backend/executor/nodeNestloop.c`、`nodeHashjoin.c` | 谁选顺序，谁执行？K1/K5 |
| OLTP RDBMS | MySQL mysql-8.4.6 | `sql/join_optimizer/`、`sql/iterators/`、`storage/innobase/` | 优化器的候选访问路径怎样落到迭代器及存储引擎？K4/K5 |
| 嵌入式 OLAP / 数仓查询实验 | DuckDB v1.3.2 | `src/optimizer/`、`src/execution/`、`extension/parquet/` | filter/projection 怎样推进扫描？向量化怎样执行？K1/K6 |
| 可嵌入分析引擎 / 数仓构件 | Apache DataFusion 49.0.2 | `datafusion/optimizer/`、`datafusion/physical-optimizer/`、`datafusion/physical-plan/` | 逻辑规则与物理规则怎样分工？K1/K6 |
| 数据湖 / 湖仓一体表格式 | Apache Iceberg apache-iceberg-1.9.2 | `core/src/main/java/org/apache/iceberg/`、`spark/v3.5/` | Scan、Snapshot、Manifest、提交如何串联？K7 |

查找函数时优先 `rg`，再结合固定版本上下文阅读，不引用漂移的 main 行号：

```text
rg -n 'cost_index|cost_hashjoin' upstream/postgres/src/backend/optimizer
rg -n 'class.*Iterator|HashJoinIterator' upstream/mysql/sql/iterators
rg -n 'FilterPushdown' upstream/duckdb/src/optimizer
rg -n 'EnforceDistribution|AggregateExec' upstream/datafusion/datafusion
rg -n 'class BaseTableScan|class SnapshotProducer' upstream/iceberg/core
```

建议每次只追一条查询：SQL → 逻辑规则 → 基数/成本 → 物理节点 → 执行循环 → 实际统计输出。
不要因源码中存在某个算子就声称本实验一定选择它；计划 artifact 才能证明本次选择。

## 克隆与版本更新

```text
git clone https://github.com/edidada/db_execute_plan.git
cd db_execute_plan
git submodule update --init --depth 1 upstream/postgres
git submodule status
```

默认不必一次下载所有大仓库。CI 每个软件只拉自己的 gitlink；不使用 `git submodule update --remote`，避免随分支漂移。
升级时先在目标 submodule fetch/checkout 明确 tag，再更新 gitlink、lock、依赖兼容版本及文档，跑对应 Actions 后提交。
`tools/register_upstreams.py` 通过官方发布 tag 解析 commit 并注册 gitlink，避免本地下载全部源码；它是首次引入/明确升级辅助工具，不是日常同步命令。

## 扩展阅读与边界

ClickHouse、Apache Doris/StarRocks 是独立完整分析数据库，Apache Hudi/Delta Lake 也是主流湖表方案，适合下一轮增加独立实验。
本次选择五个核心项目保证每个有明确源码构建和演示入口；没有把未构建的大仓库堆进列表冒充验证覆盖。
Oracle、SQL Server、Db2 没有完整开源内核；相关示例见供应商章节，不添加第三方镜像冒充官方源码。
