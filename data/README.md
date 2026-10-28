# 公开结构与数据血缘

结构取 [TPC-H Rev. 3.0.1 CUSTOMER、ORDERS](https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp) 子集。
保留 c_custkey、c_mktsegment、o_orderkey、o_custkey、o_orderdate、o_totalprice、o_orderstatus。
不是完整 TPC-H schema，不执行官方 22 条查询，不报告 QphH，也不是 TPC 认证性能结果。

`python tools/generate_data.py` 生成固定 1,001 个客户、100,000 条订单；无网络、随机数和个人信息。
前 90,000 条订单属于客户 1，其余均匀分配给客户 2..1001，故热点 90,000 条、每个冷点 10 条。
日期为 1995-01-01 加 `orderkey % 365` 天；金额从整数分转换，避免二进制浮点误差。
记录是仓库自定义合成数据，**不是官方 dbgen 分布**。它刻意制造数据倾斜，适合教学，不代表生产业务。

`expected.json` 在生成时独立计数，作为跨引擎 JOIN/GROUP BY 结果基准。
所有 CI 都验证结果，计划原文另存 artifact；不强制特定算子或虚构加速比。
