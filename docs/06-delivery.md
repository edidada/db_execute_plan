# 交付与远端验收

本次在本地仅编写文件、检索官方资料、检出固定源码和做静态检查，不编译数据库或 Java 代码。
静态检查可复用：安装 `requirements-dev.txt` 后执行 `python tools/static_check.py`，验证 Python 语法树、Maven XML、YAML、文档链接及 lock 与实际 gitlink 一致性；它不替代远端运行。

首轮 Iceberg 的 submodule Git 目录解析失败、DataFusion 49 的旧 CSV header 语法失败均已根据实际日志修复；Iceberg 已完整重跑成功，DataFusion 结果以最新运行快照为准。

远端构建结果由 `gh run list` / `gh run view --log-failed` 实时核实。此文件的状态与具体 commit/run 绑定；不将配置完成当作构建通过。
源码构建工作流上限 180 分钟，Java 20 分钟，网络、runner 资源和依赖下载均可能影响完成。

## 验收内容

* 五个官方源码 gitlink、固定版本 lock 与独立源码构建 YAML。
* 公开表结构来源、确定性数据生成与独立结果 oracle。
* 实际计划、索引前后、跨引擎聚合、Iceberg 快照读取的断言与 artifacts。
* Java 17 Maven/Gradle 同源构建和计划计数语义测试。
* 知识点、双语术语、源码路径、书籍/论文/官方文档交叉索引。

## 未作验收的范围

商业数据库实际运行；上游全量测试；真实多节点/对象存储；并发写、故障恢复、生产压力；论文完整实验复现。
这些范围在知识点章节解释机制，但不标为已实测。

## 实时检查快照

检查时间 UTC：`2026-10-28T17:07:06.276166+00:00`。这是该时刻的状态，不承诺之后不变。

| 工作流 | 最新 run | 源码提交 | 状态 |
|---|---|---|---|
| postgres-source-lab | [40729814655](https://github.com/edidada/db_execute_plan/actions/runs/40729814655) | `c03c14c` | success |
| mysql-source-lab | [40729814921](https://github.com/edidada/db_execute_plan/actions/runs/40729814921) | `c03c14c` | in_progress |
| duckdb-source-lab | [40731640877](https://github.com/edidada/db_execute_plan/actions/runs/40731640877) | `a5f0982` | in_progress |
| datafusion-source-lab | [40731832399](https://github.com/edidada/db_execute_plan/actions/runs/40731832399) | `ef0bd7b` | in_progress |
| iceberg-source-lab | [40729814907](https://github.com/edidada/db_execute_plan/actions/runs/40729814907) | `c03c14c` | success |
| java17-plan-audit | [40729263228](https://github.com/edidada/db_execute_plan/actions/runs/40729263228) | `2b80047` | success |

success 才表示该 run 完成验收；in_progress/queued 未完成。failure 需看实际失败日志；cancelled 表示取消，不能当作通过。

复查：`python tools/ci_status.py`；排错：`gh run view <RUN_ID> --log-failed`。原始状态保存在 [ci-status.json](ci-status.json)。
