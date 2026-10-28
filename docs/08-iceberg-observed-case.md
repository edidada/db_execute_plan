# 实测案例：快照树、分区元数据与 AQE

证据：[GitHub Actions run 40729814907](https://github.com/edidada/db_execute_plan/actions/runs/40729814907)，结论 **success**。
父提交 `c03c14c7b144b510b86c1bd1f38ace1016ca8319`；Iceberg 发布标签 `apache-iceberg-1.9.2` 对应源码提交 `071d5606bc6199a0be9b3f274ec7fbf111d88821`。
Spark 3.5.6 / Scala 2.12 / JDK 17，单机 local[2]。

上游在这种浅检出的源码构建中，将 runtime jar 与内置 build version 标为 `071d560`，不是 Maven Central 官方发行 jar 名称。
这里的“1.9.2”指锁定发布标签对应源码，实际 jar SHA256 和运行元数据都已保存，避免把源码构建产物冒充官方预编译发行包。

## 从写入到快照

原始数据与断言见 [iceberg-validation.json](evidence/iceberg-40729814907/iceberg-validation.json)。

| 阶段 | snapshot ID | 本次新增行 | 本次新增文件 | 当前总行 / 总数据文件 |
|---|---:|---:|---:|---|
| CTAS 前 90,000 行 | 2900972664143163041 | 90,000 | 12 | 90,000 / 12 |
| 追加 10,000 行 | 7755048607140488407 | 10,000 | 12 | 100,000 / 24 |

snapshot ID 是本次提交生成的标识，重跑不会要求数值相同。
两个快照、两条 history、两份当前 manifest 和 24 个当前 data file 的 JSON 原文见 [证据目录](evidence/iceberg-40729814907/)。
时间旅行明确按旧 snapshot ID 查询并断言 90,000；当前查询断言 100,000。两者不是把文件名相加推断出来的。

当前 files 表的 record_count 总和也为 100,000，且 metadata 表明没有 delete file，因此它与本次 count(*) 一致。
不要把这一结果推广到有 equality/position deletes 的任意 Iceberg 表。

## 隐式分区的实际表示

数据文件分区字段为 `o_orderdate_month`，值 300..311；month 转换使用相对 1970-01 的月编号，恰好对应 1995 年十二个月。
业务 SQL 仍过滤原始日期，而非手动填写这个整数。每个分区本次包含 CTAS 与追加产生的文件，说明分区并不是“一分区只能有一个文件”。

[十二月计划](evidence/iceberg-40729814907/iceberg-pruning-plan.txt) 的 BatchScan 中，日期下界表现为 `o_orderdate >= 9465`。
这是 DATE 内部相对 epoch 的天数表示，不能当成业务年份。
计划证明过滤进入了 Iceberg scan；没有采集文件读取计数，故不宣称实测只读取两个文件或具体减少了多少 I/O。

## 先执行，再读最终 AQE 计划

[执行后计划](evidence/iceberg-40729814907/iceberg-executed-plan.txt) 明确包含 `AdaptiveSparkPlan isFinalPlan=true`。
客户侧被 BroadcastExchange 广播，联接为 BroadcastHashJoin / BuildLeft；聚合使用 partial_count 与最终 HashAggregate，Exchange 表达分布要求，AQEShuffleRead 标记 coalesced 读取。
Iceberg 扫描仅请求 `o_custkey,o_orderdate` 两列，能够与 K1 的投影裁剪建立联系；客户侧 CSV FileScan 又是另一套读路径。

计划保留 Initial Plan 与 Final Plan，便于区分静态规划和 action 后状态。
本次最终计划并没有证明“运行时从某种联接算法改成广播”，因为初始计划也已有 BroadcastHashJoin。
只有看到真实变化及关联指标，才能声称某个 AQE 决策改善了运行；不能因出现 AdaptiveSparkPlan 就杜撰改写过程。

## 上游构建集成的教训

首轮 [40729263445](https://github.com/edidada/db_execute_plan/actions/runs/40729263445) 失败于 generateGitProperties，原因是 submodule 的 `.git` 是指向真实 Git 目录的文件。
`ci/iceberg-submodule.init.gradle` 使用 `git rev-parse --absolute-git-dir` 的结果配置插件，保留真实 commit provenance，再完整重跑通过。
该修复针对构建目录解析，不是更改 Iceberg 内核算法。

机制与文献见 [K6/K7](01-optimizer-and-execution.md)、[E5](03-experiments.md)、[D4/D5/P6](05-references.md)。
