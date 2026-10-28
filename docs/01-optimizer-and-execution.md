# 从关系代数到执行证据：优化器与执行器

本文编号用于与 [实验](03-experiments.md)、[源码](04-source-map.md)、[参考文献](05-references.md) 互相定位。目标是让结论可验证；不以任何团队或学校排名作为质量证据。

## K1 逻辑等价不等于物理等价

SQL 是声明式语言（Declarative Language）。解析（Parsing）之后需要名称绑定、类型解析和权限检查，再得到逻辑计划（Logical Plan）。逻辑重写（Logical Rewrite）可做谓词下推（Predicate Pushdown）、投影裁剪（Projection Pruning）、子查询去关联（Decorrelation）；物理优化再选择访问路径、联接顺序和算子实现。

例如 `customer JOIN orders` 可将订单日期过滤推到联接之前，减少探测次数。只读取客户编号、分群和日期也能减少列式读取量。但外联接的谓词不能随意跨越保留 NULL 的一侧；`WHERE right.x = 1` 与 `ON right.x = 1` 可能改变结果。`NOT IN` 遇到 NULL 也不等价于无条件改写为反联接（Anti Join）。数据库采用多重集语义（Bag Semantics），去重、NULL、溢出和隐式类型转换都是重写的语义约束。[B1][P1][P2]

System R 用动态规划（Dynamic Programming）组合较优子计划，并保留有用顺序（Interesting Orders）。这解释了为什么有时排序并非纯粹浪费：已经有序的输入可以让上层 Merge Join 或聚合免去另一次排序。现代 Memo 式搜索还要记录所需物理属性（Physical Properties），例如排序和数据分布；强制转换属性的 Sort/Exchange 是执行成本。候选计划集合、搜索预算和基数估计共同限制最优性，不能把“成本最低”理解成实际运行必然最快。[P1][P3]

## K2 基数估计是误差传播链

基数（Cardinality）是算子输出行数，选择率（Selectivity）是保留比例。单谓词可粗略用 `N × s`；独立性假设下，合取用 `N × s1 × s2`；等值联接常用 `|R|×|S|/max(NDV_R,NDV_S)` 作为启发式，其中 NDV 是不同值个数（Number of Distinct Values）。这些是分析模型，不是所有内核真实公式。

本实验订单总数 100,000、客户值 1,001；若只保留 NDV 并假设均匀，任一客户约 100 条。然而热点客户实际 90,000 条，冷点仅 10 条。相同谓词形状可能需要不同访问路径。直方图（Histogram）和高频值（Most Common Values, MCV）用于刻画偏斜，多列统计用于刻画相关性。更新统计信息也无法保证解决跨表相关性、表达式估计和参数化计划问题。[P4]

普通 Q-error 为 `max(estimate/actual, actual/estimate)`，正数范围内具有对称性；零基数必须单独定义。本项目 Java 工具采用 **先将两边下限设为 1** 的平滑 Q-error（Smoothed Q-error），不是声称统计学意义上消除了零值误差。`0 vs 0` 得 1，`0 vs 100` 得 100，细节见 `PlanAudit.smoothedQError`。

PostgreSQL 17 的 `Actual Rows` 是每次循环的平均输出行数，`Actual Loops` 是循环数。用于诊断总输出的近似值为两者相乘；与 `Plan Rows` 比较时应比较每循环值。整数显示会舍入，小值乘大 loops 的误差可能明显。`loops=0` 的未执行分支不能判成“估计错了无穷倍”。LIMIT、半联接等可能提前停止，也不能把未消费完的输出当完整执行基数。[D1]

先从叶子向上找到**第一个显著估计偏差**。若一开始就低估过滤结果，随后 Nested Loop、回表和排序的坏选择可能都是后果。只修最慢的最上层算子常治标不治本。Q-error 很高也不必然导致慢查询：误差是否跨越了算法选择阈值，比单个最大误差更有解释力。[P4]

## K3 成本模型不是秒表

成本（Cost）是内部比较单位。启动成本（Startup Cost）决定首行延迟，总成本（Total Cost）用于完整消费；LIMIT、小批量分页和游标的目标不同。PG cost、Oracle Cost、Db2 timeron 不能横向比大小；SQL Server 图上的百分比通常是估算成本比例，也不是实际耗时占比。

成本必须由实验校验：CPU、页访问、缓存命中、物理读、网络、并行调度、临时文件和客户端消费都会影响时延。`Shared Hit` 表示数据库缓冲命中，不代表 CPU 免费；`Shared Read` 也不等于直接命中物理磁盘，可能被操作系统页缓存满足。父节点时间包含子节点工作，逐项相加会重复计数；流水线和并行算子更不能简单累加。[D1][B1]

## K4 访问路径与索引

B+ 树索引适合有序定位与范围访问。联合索引 `(o_custkey,o_orderdate)` 可同时利用客户等值和日期范围；在第二列范围之后的后续列通常不能继续缩小连续扫描区间，但可能成为索引条件或覆盖列。具体规则要看版本、索引类型、Skip Scan 等能力，不能把最左前缀简化成跨引擎绝对定律。[B1][D2]

覆盖索引（Covering Index）让查询所需列都在索引内，减少访问基表；PG 的 Index Only Scan 还受可见性映射（Visibility Map）影响，计划名中出现 Only 也可能有 Heap Fetches。MySQL InnoDB 的二级索引带主键，回表（Bookmark/Key Lookup）按主键访问聚簇索引；PG 普通堆表不是同样的存储组织。

随机页访问可能比顺序扫描昂贵。热点返回全表 90% 时，顺扫可能更优；冷点十条时索引更有价值。MySQL `type` 不是可脱离选择率与覆盖性的成绩排名，`ALL`、`Using filesort`、`Using temporary` 均需结合行数和资源证据。filesort 是 MySQL 排序算法标记，并不等价于“必然写磁盘”。[D2]

可搜索性（SARGability）要求谓词可映射到访问路径。`EXTRACT(YEAR FROM date)=1995` 与半开区间 `[1995-01-01,1996-01-01)` 在本 DATE 数据上等价；普通日期索引可能更易用于后者。若查询命中全年全部数据，改写后仍顺扫完全合理。表达式索引、函数索引和优化器重写会改变结果；对 timestamp 必须进一步处理时区和边界。[E2]

索引不是免费结构：占用存储、增大写放大（Write Amplification）、影响缓存与维护。只看一条 SELECT 的收益会掩盖更新延迟和空间成本。实验仅验证读路径，没有测并发写负载。

## K5 联接、排序与聚合的算法阈值

| 算法 | 直观成本与适用条件 | 容易误判的证据 |
|---|---|---|
| 索引嵌套循环 Index Nested Loop | 外表 N 行，每行内表索引查找；小外表常有利 | 不是看到 Nested Loop 就坏，应看内表 loops 和单次读取 |
| 哈希联接 Hash Join | 典型均摊 O(build+probe)，主要用于等值条件 | 内存不够会分批/溢写；热键可能导致桶倾斜 |
| 排序合并联接 Sort Merge Join | 已有序输入可线性合并，否则还需排序 | 重复键匹配仍可能产生大量组合，不能笼统声称总是 O(N+M) |
| Hash Aggregate | 维护每组状态，内存与组数/状态宽度有关 | 少量输出不代表少量输入；高 NDV 会增大状态 |
| Sort/Group Aggregate | 排序后流式分组，或消费已有顺序 | 检查排序方法、内存与临时磁盘，而非仅看 Sort 名字 |

联接顺序（Join Order）决定中间结果大小，通常比微小 CPU 成本校准更重要。驱动表不是 SQL 文本里先写的表。外联接、非等值条件、排序要求和相关子查询会限制可交换性。MySQL 8.0.18 引入哈希联接；8.4 实验必须以实际输出为准，不用可视化图的菱形形状判断算法。[D2][P2][P4]

溢写（Spill）需要工作内存、并发度与算子数联合评估：PG `work_mem` 并非每条查询的固定总额；多算子、多 worker 和多会话会放大峰值。加内存之前先判断是否误估或不必要地携带宽列。[B1][D1]

## K6 向量化与分布式边界

火山式迭代器（Volcano Iterator）以 `next()` 拉取元组，结构清晰但解释、函数调用和分支开销可能高。向量化执行（Vectorized Execution）成批处理列向量，改善缓存局部性并为 SIMD 创造条件；它不保证所有表达式都 SIMD，也不意味着可以忽略联接顺序。DuckDB/DataFusion 实验用于观察批处理分析执行，不代表完整企业数仓的事务、治理和高可用能力。[P2][P5]

分布式执行需要分区属性，Exchange/Shuffle 会产生网络与序列化成本。广播联接（Broadcast Join）复制小表，重分区联接（Repartition Join）按键重分布两侧；热点键会使单个任务成为长尾（Straggler）。Spark 自适应查询执行（Adaptive Query Execution, AQE）可利用运行统计调整部分物理决策；初始 EXPLAIN 与 action 后最终计划要分别保存。本项目 Spark 为 local[2]，**不构成多节点网络、容错、并发或对象存储性能证据**。[D5]

## K7 湖文件、表元数据与快照

数据仓库（Data Warehouse）是分析管理体系；数据湖（Data Lake）通常以文件/对象存储承载多种数据；湖仓一体（Lakehouse）尝试结合开放存储与事务、治理和分析能力。Parquet 是列式文件格式，Iceberg 是表格式（Table Format），Spark 是执行引擎，Catalog 负责表定位及提交协调；四者不能互换称谓。[P6][D4]

Iceberg 表元数据指向快照（Snapshot）；快照引用 manifest list，再到 manifest 与数据文件。扫描可以利用分区值、文件级统计和文件内行组统计逐层减少工作。隐式分区（Hidden Partitioning）使用户按原始日期过滤，而表使用 `months(date)` 分区转换，不必手写分区目录条件。分区演进（Partition Evolution）使新旧布局共存，规划器按各自 spec 解读，不能假设所有文件共享同一个分区规则。[D4]

时间旅行（Time Travel）读取指定快照，不是从当前文件列表推断历史。元数据提交的原子可见性要依赖正确的 Catalog/FileIO/存储实现；本实验 HadoopCatalog + 本地文件系统只验证单进程提交与读取语义，不代表任意 S3 部署都满足同样的协调条件。小文件合并（Compaction）、快照过期（Expire Snapshots）、孤儿文件清理有不同目的；过早删除历史所需文件会破坏回溯。[D4]

Iceberg `files.record_count` 是文件元数据统计，遇到 delete files 等情形不能无条件当成当前可见记录数。计划出现过滤条件也只说明规划器表达了过滤，不足以证明实际只读了几个文件。E5 保存元数据与执行计划，不报告未经度量的 I/O 加速比。

## K8 可重复的调优推理

一次严谨结论至少包括：版本/提交、DDL/索引、数据分布、统计状态、SQL/参数、配置、计划原文、正确性、执行次数和测量边界。本实验先固定这些输入，再研究差异。先问结果是否正确，再找估计与实际不一致处，最后验证单变量修改。

CI 共享机器的运行时间受宿主噪声影响，索引后实验还会受前阶段缓存预热影响，因此本项目不据此宣称性能冠军。生产评测应随机化 A/B 次序、区分冷暖缓存、报告重复次数和分位数，并同时度量 CPU/IO/内存/写入代价。一次绿色 CI 是本次固定实验通过，不是优化器全面正确的证明。[P4][P7]
