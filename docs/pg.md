
**4. PostgreSQL 源码**

重点研究：

```text
PostgreSQL
│
├── src/backend/parser/
│   └── SQL 解析
│
├── src/backend/optimizer/
│   ├── path/
│   │   └── 访问路径与 JOIN 搜索
│   └── plan/
│       └── 执行计划构建
│
├── src/backend/executor/
│   ├── execMain.c
│   ├── execProcnode.c
│   ├── nodeSeqscan.c
│   ├── nodeNestloop.c
│   ├── nodeHashjoin.c
│   └── nodeAgg.c
│
└── src/backend/access/
    └── 存储访问方法
```

源码仓库：[PostgreSQL GitHub](https://github.com/postgres/postgres?utm_source=chatgpt.com)

**特别推荐从 `ExecProcNode()` 入手，研究 PostgreSQL 如何递归驱动执行计划树。**
