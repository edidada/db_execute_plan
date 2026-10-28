# 实测案例：同一数据的不同访问路径与估计误差

证据：[GitHub Actions run 40729263263](https://github.com/edidada/db_execute_plan/actions/runs/40729263263)，结论 **success**。
父仓库提交 `2b800472cb393e99ad7d2929c2f16e4a9ef9c0a3`；PostgreSQL 17.6 源码提交 `7885b94dd81b98bbab9ed878680d156df7bf857f`。
当次 artifact 中的 JSON 原文已保存到 [evidence/postgres-40729263263](evidence/postgres-40729263263/)，避免 14 天 artifact 过期后失去依据。
这些数字是该次固定实验的观察值；ANALYZE 采样及运行环境可能使复跑数值有小幅变化。

## 案例一：热点仍顺扫，冷点使用索引

| 查询 | 无二级索引 | 建索引后 | 建索引后的估计 / 实际输出 |
|---|---|---|---|
| 客户 1 | Seq Scan | Seq Scan | 89,903 / 90,000 |
| 客户 1001 | Seq Scan | Index Only Scan | 10 / 10 |

对照 [热点计划](evidence/postgres-40729263263/pg-after-index-1.json) 与 [冷点计划](evidence/postgres-40729263263/pg-after-index-2.json)。
索引的存在改变候选路径，不强迫优化器选择它。热点返回 90% 数据，读取大量索引项再访问堆表未必划算；冷点的十行定位则适合索引。
这是 K4 的具体证据，不能把 Seq Scan 一概当错误，也不能只检查 `key` 是否为空。

冷点输出明确为 `Index Only Scan`，同时 `Heap Fetches: 10`。本实验装载后只做 ANALYZE，未用 VACUUM 将相关堆页标为 all-visible。
因此执行器仍需访问堆表验证可见性。这解释了“查询列被索引覆盖”和“完全不读堆表”为何是不同条件。
以后可以增加 VACUUM 的单变量实验；本次没有做，不能声称已经观察到它降为零。

## 案例二：逻辑等价，估计质量不同

| 谓词 | 访问路径 | 估计输出 | 实际输出 | 平滑 Q-error |
|---|---|---:|---:|---:|
| `EXTRACT(YEAR FROM o_orderdate)=1995` | Seq Scan | 500 | 100,000 | 200 |
| `o_orderdate >= DATE '1995-01-01' AND o_orderdate < DATE '1996-01-01'` | Seq Scan | 100,000 | 100,000 | 1 |

原文：[函数谓词](evidence/postgres-40729263263/pg-after-index-3.json)、[范围谓词](evidence/postgres-40729263263/pg-after-index-4.json)。
本 DATE 数据中，两者返回全部订单，结果断言相同。范围形式让优化器更直接利用日期列统计；函数表达式没有相应表达式统计/索引，估计明显偏低。
这说明 SQL 写法会影响**估计可用信息**，不只是索引可搜索性。

二者仍都顺扫，因为选择率实际都是 100%；改善估计不要求一定改成 Index Scan。
若把函数过滤放到更复杂联接链中，误估可能进一步影响顺序、build 侧与内存，需新增查询验证；本次没有构造那条链，故不推断必然产生何种坏计划。

## 案例三：单条联接查询的路径变化

共享的分群聚合结果为：AUTOMOBILE 1,028；BUILDING 46,295；FURNITURE 1,028；HOUSEHOLD 1,028；MACHINERY 1,028，总计 50,407。
这些结果以保存的 [data-manifest.json](evidence/postgres-40729263263/data-manifest.json) 为准；计划中的每个节点仍要与正确性断言分开看。

索引前：日期过滤位于 orders Seq Scan，再与客户 Hash Join；索引后变为 Bitmap Index Scan → Bitmap Heap Scan → Hash Join。
联接实际均为 50,407 行；索引后估计 50,656。上层只有五个分群并排序，这不意味着联接前只处理五行。
见 [索引前](evidence/postgres-40729263263/pg-before-index-5.json)、[索引后](evidence/postgres-40729263263/pg-after-index-5.json)。

这个变化证明优化器选择了另一访问路径，**不自动证明更快**。相邻两次执行存在缓存和测量噪声，未随机化次序或重复采样。
所有当次节点计数与 Java 诊断都保留在 [pg-cardinality-audit.json](evidence/postgres-40729263263/pg-cardinality-audit.json)，便于沿树检查第一个偏差位置。

## 验收层次

该 run 完成源码构建、引擎启动、十次查询结果断言（五条 × 索引前后）、十份实际 JSON 计划和 Java 诊断。
Java 测试两项，失败/错误/跳过均为零。它证明这个实验链可运行，不等于上游全量回归、生产性能或所有优化器功能已验收。

机制与文献见 [K2/K4/K5](01-optimizer-and-execution.md)、[D1/P4/B1](05-references.md)。
