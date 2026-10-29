# 验收报告

## 验收依据

本次验收检查实际 GitHub Actions job conclusion、构建日志、下载产物与结果断言，不在本地编译。
机器可读结果见 [acceptance.json](acceptance.json)，当前状态见 [交付快照](06-delivery.md)。
复查命令：`python tools/acceptance_audit.py`；仅检查 main 分支，run 提交必须是当前 HEAD 的祖先。脚本只有在六个最新工作流全部 success 且产物复核通过时才返回 0，排队/运行中/失败均不算通过。
它会核对上游 SHA 与 lock、产物内的父仓库 SHA、数据量、实际计划、SQL 结果及测试报告，并保存精简原始证据。

## 已完成的产物复核

| 对象 | 成功 run | 验收证据 |
|---|---|---|
| PostgreSQL 17.6 | [40729814655](https://github.com/edidada/db_execute_plan/actions/runs/40729814655) | 源码构建、启动、十次 SQL 断言、十份实际 JSON 计划及 Java 对真实计划的诊断 |
| MySQL 8.4.6 | [40729814921](https://github.com/edidada/db_execute_plan/actions/runs/40729814921) | 源码 mysqld、十次 SQL 断言与十份 EXPLAIN ANALYZE 计划 |
| DuckDB v1.3.2 源码 | [40788597839](https://github.com/edidada/db_execute_plan/actions/runs/40788597839) | LLD 成功链接源码 CLI、十次 SQL 断言与实际计划、Parquet 文件及过滤计划；版本标签显示限制见下文 |
| DataFusion 49.0.2 | [40731832399](https://github.com/edidada/db_execute_plan/actions/runs/40731832399) | Cargo release 编译、五组聚合结果与 oracle 完全一致、带 output_rows 等指标的物理计划 |
| Iceberg 1.9.2 源码 | [40729814907](https://github.com/edidada/db_execute_plan/actions/runs/40729814907) | source runtime jar、两个快照、90k/100k 行回溯断言、共享聚合与最终 AQE 计划 |
| Java 17 Maven / Gradle | [40729263228](https://github.com/edidada/db_execute_plan/actions/runs/40729263228) | 两种构建各两项测试，无失败/错误；shaded jar 中含主类，Gradle application distribution 存在 |

产物证据保存在 [evidence](evidence/) 下，以软件名与 run ID 分目录。不是只读取 CI 绿色图标：已核对实际数据、计划文件、测试报告和版本字段。

各工作流 head SHA 不同，报告保留真实 SHA，不伪装成一次统一 HEAD 构建。
已通过项到本次修复提交 `07bc459` 的相关代码差异已检查：Java 源码/构建未变，DataFusion SQL/脚本未变；PG/MySQL 的共享脚本仅修改 `engine == 'duckdb'` 分支，PG/MySQL 执行路径未变；Iceberg 构建与执行脚本未变。

## DuckDB 阻断与修复

原 run [40731640877](https://github.com/edidada/db_execute_plan/actions/runs/40731640877) 在第 1672/1672 步链接 shell 时失败：mbedtls 静态库引用前面的 duckdb_static 中 `EncryptionState` 符号，GNU ld 未回扫该归档。
符号实现存在于固定版本 `src/common/encryption_state.cpp`，不是缺失实现或 SQL 结果错误。
修复提交 `07bc459` 为 shell 显式使用 LLD，并记录链接器版本；上游源码版本与实验数据不变。
LLD 与 GNU ld 对归档反向引用的处理差异见 [LLVM 官方说明](https://lld.llvm.org/ELF/warn_backrefs.html)。

修复后 run：[40788597839](https://github.com/edidada/db_execute_plan/actions/runs/40788597839) **success**，已完成源码构建、十次 SQL 断言及 Parquet 实验，产物复核通过。实际使用 Ubuntu LLD 18.1.3，1672/1672 链接步骤成功。

原始证据见 [duckdb-40788597839](evidence/duckdb-40788597839/)。Parquet 过滤计划输出 8,485 行，Total Files Read 为 1；这不等于测量了跳过多少 row group 或物理磁盘读取量。

### 版本标识限制

该源码构建 CLI 的 `--version` 实际显示 **`v0.0.1 (Unknown Version) 0b83e5d2`**，不是整洁的发行版版本号。
浅检出缺少发布 tag 元数据，使 [上游版本生成逻辑](https://github.com/duckdb/duckdb/blob/v1.3.2/CMakeLists.txt) 回退；实际源码提交 `0b83e5d2f68bc02dfefde74b846bd039f078affa` 与官方 `v1.3.2`、gitlink、lock 和 CI 产物记录完全一致。
本次按固定源码身份验收，不把该 CLI 冒充已正确标记版本的官方发行二进制。机器报告单列 `release_label_matches_tag=false`，保留这一非功能限制。
Iceberg 的源码 jar 使用 commit 作为构建版本标签，也已在 [实测案例](08-iceberg-observed-case.md) 说明。

## 实测结果的重要差异

MySQL 本次热点与冷点都选择 `Covering index lookup`，热点估计 50,038、实际 90,000 行，冷点估计/实际均 10 行。
这与 PostgreSQL 热点保留 Seq Scan 的结果不同，说明存储组织、覆盖读取与成本模型不能跨库套用。
MySQL 的聚合查询使用 Nested loop，内侧覆盖索引查找 `loops=1001`；不能仅凭 Nested Loop 标记判错。
原始数据见 [mysql-plans.json](evidence/mysql-40729814921/mysql-plans.json)。

DataFusion 的 CSV 扫描读取 100,000 行，过滤后 50,407；HashJoinExec 输出 50,407，局部聚合输出 20，最终聚合输出 5。
局部聚合行数大于最终组数是正常的分阶段聚合行为，不是重复计算错误。CSV 中日期谓词在 FilterExec 执行，不能仅凭存在下推规则就声称 CSV 文件物理 I/O 被裁剪。
见 [datafusion-plan.txt](evidence/datafusion-40731832399/datafusion-plan.txt) 与 [结果 CSV](evidence/datafusion-40731832399/datafusion-result.csv)。

## 验收边界

知识点的实测覆盖如下，不能将文献讲解全部计为运行验收：

| 知识点 | 已有运行证据 | 仅讲解、未实测的部分 |
|---|---|---|
| K1 重写 / 物理计划 | DataFusion 投影与过滤位置、Spark 的列裁剪 | 外联接/NULL 重写边界、Memo 搜索过程 |
| K2 基数估计 | PG 估计/实际、loops、平滑 Q-error；MySQL 偏差 | 多列扩展统计、跨表相关性、参数缓存实验 |
| K3 成本 | 原始 cost/实际计划并存、明确不跨库比较单位 | 成本校准、冷暖缓存随机 A/B、资源归因 |
| K4 索引 | PG/MySQL 索引前后、热点/冷点、覆盖与 Heap Fetches | 并发写代价、VACUUM 后单变量对照 |
| K5 联接 / 聚合 | Hash Join、Nested Loop、局部/最终聚合 | Merge Join、内存溢写与高 NDV 压力 |
| K6 向量化 / 分布 | DataFusion batches/metrics、Spark 最终 AQE | 多节点 Shuffle、网络与倾斜容错 |
| K7 湖表 | Iceberg 两快照、隐式分区、元数据、时间旅行 | 分区演进、删除文件、并发提交与对象存储 |
| K8 研究方法 | 固定源码、数据 oracle、原始产物、失败复跑 | 产品性能排名、论文全量复现 |

通过范围是当前五个开源项目的指定源码构建与教学实验，以及 Java 工具，不是上游所有测试或生产系统认证。
商业数据库仅有文档与示例，未运行；没有真实多节点、对象存储、并发写、故障恢复或公平性能排名。
理论知识的解释与文献引用，不等于复现了全部论文实验；“国内外顶级水平”不能作为由这几条 CI 自动证明的排名结论。

## 最终结论

**当前教学实验范围验收通过。**六个 main 分支工作流均为 success，下载产物复核全部通过；Java 的 Maven、Gradle 两个 job 均成功。
本地未编译。DuckDB 的非发行版版本显示限制、未实测的知识点及生产范围均已明确记录；不扩大为所有理论、商业数据库和生产能力全部验收通过。
