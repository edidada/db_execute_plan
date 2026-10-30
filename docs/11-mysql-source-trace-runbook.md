# MySQL 源码日志实验与 artifact 查看

本次先检查了上一条提交 `b809216`（新增/扩充源码计划文章及 pg.md），保留这些内容。新实现采用独立工作流，不改既有 Release 实验的验收结果。

## 文件分工

* `.github/workflows/mysql-source-trace.yml`：仅配置 checkout、Python、调用 `bash shell_scripts/mysql-source-trace.sh` 和上传产物；没有内联构建/SQL命令。
* `shell_scripts/mysql-source-trace.sh`：初始化官方固定 submodule，安装依赖、编译 Debug mysqld、启动隔离 socket 实例、生成数据、运行实验、打印日志摘要和关闭服务。
* `sql/mysql-source-trace/schema.sql`：InnoDB 建库建表。
* `sql/mysql-source-trace/indexes.sql`：第二阶段建索引及更新统计。
* `sql/mysql-source-trace/query.sql`：两层嵌套派生表子查询、UNION ALL、JOIN、日期过滤、GROUP BY、ORDER BY 查询。
* `trace-on.sql / trace-read.sql / trace-off.sql`：开启、读取、关闭 optimizer_trace。
* `tools/mysql_source_trace.py`：导入固定 CSV，在同一连接采集 trace、实际计划、原生 DBUG 并断言结果。数据结构源自 TPC-H 子集，合成数据与既有实验一致。

## 如何开启日志

### 嵌套子查询观察点

目标 SQL 包含四个 SELECT 查询块：最内层两个 SELECT 用 UNION ALL 拼接日期区间，中间层按客户聚合订单数，最外层联接客户并按分群求和。
两个分支分别为 `[1995-07-01,1995-10-01)` 和 `[1995-10-01,+∞)`，互不重叠且并集等于原始过滤范围；第二分支没有人为增加上界，保持原 SQL 语义。
使用 UNION ALL 保留每一条订单的贡献；若直接换成 UNION，因投影只有客户编号，同一客户的多笔订单会被去重，COUNT 结果将改变。
含 UNION ALL 的派生表与含 GROUP BY 的派生表均不能按普通简单派生表合并；观察其物化（Materialization）、集合运算和读取路径。
是否延迟物化、是否创建临时索引、具体联接顺序均以实际 trace/计划为准，不强制计划形状。
SQL 有嵌套不代表执行器一定逐行重新执行子查询；这正是需要用日志验证的区别。

中间层每客户 COUNT(*)、外层 SUM(order_count)，与原先直接按分群 COUNT(*) 等价：customer 主键保证联接不放大行数，COUNT 值非 NULL，原始日期过滤未变。
因此仍使用现有独立 oracle 检查五组结果，总计 50,407；不改预期结果以迁就新 SQL。
重点比较 trace 的各 select#、集合运算分支、派生表物化决策，以及实际计划的聚合与临时结果读取节点。UNION ALL 不要求去重，但也不能据此保证整个查询没有临时表或排序。Debug 构建日志的性能不用于与原始 SQL 公平排名。

构建开关是 `CMAKE_BUILD_TYPE=Debug`、`WITH_DEBUG=ON`。仅在隔离 Debug 实例的数据装载完成后，为实验连接设置 `SET SESSION debug=...`。
控制串由脚本生成并保存在 artifact 的 `before-index-debug-on.sql` / `after-index-debug-on.sql`：`d,ast` 启用上游原生 AST/Query plan 埋点，`t` 记录已有函数进出，`F/L` 文件/行号，`f` 限定函数，`O` 输出服务端日志文件。
DBUG 使用冒号分隔选项，函数过滤不能直接嵌入 `JOIN::optimize` 之类带 `::` 的名称；采用 `*optimize`、`*choose_table_order` 等 glob 模式。实际生效控制串另存 `*-debug-effective.json`。
连接只追踪指定准备/优化/执行入口，避免每个 InnoDB 行访问的海量 trace。`i` 是 PID，连接编号另存 session.json。

同时开启 `optimizer_trace='enabled=on,one_line=off'`，运行查询后立即读取 INFORMATION_SCHEMA.OPTIMIZER_TRACE，检查没有截断或权限缺失，然后关闭。
另一次执行 `EXPLAIN ANALYZE` 保存实际计划。这是两次执行，不冒充同一查询实例的完整统一时序。

原生源码对应：`sql_union.cc` 的 `ast` 分支输出 PrintQueryPlan，`sql_optimizer.cc` / `sql_planner.cc` 的 Opt_trace 埋点记录决策，TimingIterator 收集实际执行统计。详细固定源码链接见 [源码计划](10-mysql-query-source-log-plan.md)。
DBUG 不是自动跟踪所有函数：本次不新增内核补丁，不声称记录无原生 DBUG_TRACE 的每个 RowIterator::Read；迭代器行数和 loops 由 EXPLAIN ANALYZE 体现。

## 运行与查看

```powershell
gh workflow run mysql-source-trace.yml
gh run list --workflow mysql-source-trace.yml
gh run view <RUN_ID> --log-failed
gh run download <RUN_ID> --dir artifacts/mysql-debug-download
```

网页：仓库 **Actions → mysql-debug-source-trace → 某次运行**；job 内看控制台摘要，运行详情页底部 **Artifacts** 下载 `mysql-debug-source-trace-<RUN_ID>`。
该工作流 artifact 保存 30 天，失败也尝试上传已生成日志。artifact 属于本仓库的 Actions 存储，**不会自动成为 Git 提交中的文件**。

主要产物：`build-and-demo.log`、`CMakeCache.txt`、源码/父仓库 SHA、`mysql-error.log`、两份 `.dbug`、两份 optimizer-trace JSON、两份实际计划、会话配置、SQL 副本和 validation.json。
`validation.json` 只有完整断言成功才生成 passed=true；上传成功不能代替实验通过。原生 Debug 日志可能改变时间，不能拿它排名性能。

## 之前 upload 的文件在哪里

已实时检查旧 artifacts：MySQL 成功 run [40729814921](https://github.com/edidada/db_execute_plan/actions/runs/40729814921)，artifact 名 `mysql-plans-40729814921`，ID `12837018761`，本次检查时尚未过期。
直接打开 [artifact 下载页](https://github.com/edidada/db_execute_plan/actions/runs/40729814921/artifacts/12837018761)，或：

```powershell
gh run download 40729814921 --name mysql-plans-40729814921 --dir artifacts/old-mysql
gh api repos/edidada/db_execute_plan/actions/artifacts --jq '.artifacts[] | {name,id,expired,created_at}'
```

旧工作流保留 14 天，过期后不能依赖 Actions 下载。之前已提交的精简永久证据在 [docs/evidence/mysql-40729814921](evidence/mysql-40729814921/)，包括十份实际计划汇总 JSON、版本和校验完成标记；这些旧证据来自 Release 构建，不包含本次新增的 Debug DBUG/optimizer_trace。

本次完整日志先上传本仓库 Actions；远端实验成功后，将下载精简日志并提交 `docs/evidence/`，获得长期 Git 历史。运行尚未结束时不写成已成功。
