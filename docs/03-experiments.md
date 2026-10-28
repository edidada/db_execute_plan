# 实验手册与验收边界

只在 GitHub Actions 编译。工作流各自初始化自己的 submodule，不递归拉取全部软件。
从 GitHub 的 Actions 页面选择对应软件，点击 Run workflow；或执行：

```powershell
gh workflow run postgres.yml
gh run list --limit 20
gh run view <RUN_ID> --log-failed
gh run download <RUN_ID> --dir artifacts/<RUN_ID>
```

`workflow_dispatch` 可单独重跑。失败必须看真实 job 日志；排队、下载失败和超时都不视为成功。
源码构建和数据实验在同一个 job 内依次执行，退出码通过 pipefail 保留。artifact 即使 job 失败也尝试上传。

## E1 热点、冷点与访问路径（K2/K3/K4）

文件：`sql/workload.sql` 前两条；执行器：`tools/relational_demo.py`。
先建表、装载数据、更新统计，执行无二级索引阶段；然后增加 `(o_custkey,o_orderdate)` 和日期索引，重新统计并执行。
客户 1 必须返回 90,000，客户 1001 必须返回 10；PG、MySQL、DuckDB 都断言。

回答：热点与冷点分别估计多少？是否同一个访问路径？索引后是否出现覆盖读取、回表？实际读取是否与输出相差很大？
观察的是优化器实际选择，不强制 Index Scan。PG Index Only Scan 还要看 Heap Fetches。
并未实现写吞吐对照，不能据此说明索引总体收益。

## E2 函数谓词与日期范围（K4）

比较 EXTRACT(YEAR) 与半开日期区间。两条都断言 100,000，证明本数据上语义等价。
因为命中全年，范围改写后保留顺扫可能正是合理选择。
继续研究时应把范围缩到某一天，再固定数据重跑；不要改变时间范围后还宣称只改变了 SQL 写法。

## E3 联接、聚合与谓词下推（K1/K2/K5/K6）

按客户分群统计 1995-07-01 以后的订单数。独立 oracle 在生成器中按客户值和日期逐行累加，不调用数据库查询本身。
PG/MySQL/DuckDB 在索引前后都比较完整五组结果；DataFusion/Iceberg 也运行相同语义聚合并比较。

读计划时记录：日期过滤所在位置、build/probe 侧、联接估计/实际、聚合组数、排序行数。
DataFusion 使用 CSV 外部表，展示其逻辑/物理计划与算子指标；不能将其 CSV 扫描时间与其他引擎缓存内存表时间当公平排名。
Iceberg 的 Spark 计划在 collect 后记录，避免只展示未执行的初始 AQE 计划。

## E4 列式文件和 min/max 裁剪（K6/K7）

DuckDB 将订单按日期排序写 Parquet，设置约 10,000 行的 row group（实现可能按内部向量粒度调整）。
随后解释十二月过滤，保存 `duckdb-parquet-plan.txt`。
对比关系表索引与 Parquet 扫描时，分别关注索引定位/回表以及过滤下推/统计裁剪，不能仅凭算子数比较。
本实验记录实际计划；没有实现冷缓存物理读量测量，也不预设所有行组都能被跳过。

## E5 Iceberg 快照、隐式分区与最终计划（K7）

依赖：源码构建 Iceberg 1.9.2 Spark 3.5/Scala 2.12 runtime，使用 Spark 3.5.6、JDK 17。
建 `months(o_orderdate)` 分区表并写入前 90,000 行，记录 snapshot ID，再追加 10,000 行。
断言旧版本 90,000 行、当前 100,000 行，再断言共享聚合结果。

保存 `files`、`manifests`、`snapshots`、`history` 元数据表，以及十二月过滤的 EXPLAIN FORMATTED 与聚合的最终执行计划。
从 metadata JSON 找到 partition、record_count、lower_bounds/upper_bounds，追踪快照到文件的映射。
这证明本地 HadoopCatalog 上的追加与历史读取；没有验证并发冲突、跨分区演进、MERGE/DELETE、远程对象存储或灾难恢复。
这些是后续课题，不能把附有理论说明当作已经实测。

## E6 Java 17 的 PG JSON 计划诊断（K2）

Maven 为主，父 POM 聚合 `plan-audit` 模块；Gradle 使用相同源码、测试与依赖版本。
CI 用 JUnit 验证热点/冷点误差对称性、零值约定、loops 语义、未执行分支和无效输入。
工具对 `Plan`/`Plans` 树遍历，输出每节点估计、实际每循环行数、近似总行数和平滑 Q-error。

下载 PG 与 Java Maven artifact 后可运行（这是操作说明，本次不在本地执行编译）：

```text
java -jar plan-audit-1.0.0.jar pg-after-index-1.json pg-after-index-2.json
```

仅解析 PostgreSQL 计划 JSON，不声称可把 MySQL、Oracle 等异构 JSON 字段直接套同一模型。
JSON 样本中的 `Actual Rows=1, Actual Loops=10` 与 `Plan Rows=2` 应比较 2 vs 1，而非 2 vs 10。

## 构建范围

| 工作流 | 编译产物 | 真正运行的引擎 | 未覆盖 |
|---|---|---|---|
| postgres.yml | configure/make 的 server 与客户端 | 刚编译的 PostgreSQL | 全套上游 regression、多节点 |
| mysql.yml | CMake/Ninja 的 mysqld/mysql/mysqladmin | 刚编译的 mysqld | Router、NDB、X Plugin、上游全测试 |
| duckdb.yml | CMake `shell` target 的 duckdb CLI | 刚编译的 CLI，非 pip wheel | 上游 unit tests、生产并发 |
| datafusion.yml | Cargo release datafusion-cli | 刚编译的 CLI | 分布式调度服务、上游全测试 |
| iceberg.yml | Gradle shadowJar Spark runtime | 源码 jar + 发行版 Spark | Spark 自身源码构建、Iceberg 全测试 |
| java-plan-audit.yml | Maven shaded jar / Gradle distribution | JDK 17 JUnit | 商业数据库计划适配 |

上游本来使用的构建系统不应为了统一而强行改写：PG 用 make，MySQL/DuckDB 用 CMake，DataFusion 用 Cargo，Iceberg 用 Gradle。本项目新增 Java 代码同时支持 Maven 与 Gradle。

## 阅读一次 CI 结果

artifact 至少包含父仓库 SHA、上游 SHA、runner 信息、数据分布 manifest、构建及演示日志；计划在实验成功到相应阶段后生成。
绿色状态需同时完成源码编译、启动/载入、结果断言与计划采集。依赖下载或基础设施失败也会使 job 失败，应单独解释原因。
build 日志中没有结果断言完成标记时，不得以“二进制已生成”替代完整实验通过。

若需要性能研究，再增加规模、随机 A/B 顺序、重复采样和资源监控。本仓库默认 100k 行，是有意控制的语义/计划教学规模，不是工业级压力测试。
