# Ubuntu 本地与 GitHub Actions 共用脚本

脚本不需要 GitHub 账号或 Actions 环境变量。支持从任意当前目录调用，自动定位所属仓库。
实际编译仍按项目要求放在 GitHub Actions；下面的本地命令是交付给 Ubuntu 使用者的操作方法，本次未在本地执行编译。

## Ubuntu 参数示例

使用普通用户执行，安装系统依赖时仅 apt 阶段使用 sudo：

```bash
bash /path/to/db_execute_plan/shell_scripts/mysql-source-trace.sh \
  --install-deps \
  --jobs 2 \
  --work-dir /tmp/planlab-mysql-debug-01 \
  --output-dir "$HOME/planlab-logs/mysql-debug-01"
```

此命令编译固定 submodule 的 Debug mysqld，构造数据，执行包含嵌套子查询、UNION ALL、JOIN 和聚合的 SQL，保存 DBUG、optimizer_trace、实际计划与结果断言。
SQL 位于 `sql/mysql-source-trace/`，日志在指定输出目录。不会上传本地文件；上传由 Actions 的 upload-artifact 步骤负责。

其他入口使用同样参数：

```bash
bash shell_scripts/build-mysql.sh --install-deps --jobs 2 --work-dir /tmp/mysql-01 --output-dir "$HOME/planlab-logs/mysql-01"
bash shell_scripts/build-postgres.sh --install-deps --jobs 2 --work-dir /tmp/pg-01 --output-dir "$HOME/planlab-logs/pg-01"
bash shell_scripts/build-duckdb.sh --install-deps --jobs 2 --work-dir /tmp/duck-01 --output-dir "$HOME/planlab-logs/duck-01"
bash shell_scripts/build-datafusion.sh --install-deps --jobs 2 --work-dir /tmp/df-01 --output-dir "$HOME/planlab-logs/df-01"
bash shell_scripts/build-iceberg.sh --install-deps --jobs 2 --work-dir /tmp/ice-01 --output-dir "$HOME/planlab-logs/ice-01"
```

| 参数 | 含义 / 默认 |
|---|---|
| `--help` | 只显示帮助，不安装依赖、拉源码或编译 |
| `--work-dir DIR` | 编译、虚拟环境、数据库和生成数据的工作目录；本地默认 `.local-runs/planlab-<软件>`，Actions 可借用 RUNNER_TEMP |
| `--output-dir DIR` | 日志及结果目录，默认仓库 `artifacts/<软件>`；相对路径相对于调用时目录 |
| `--jobs N` | 构建并行数，默认 2，必须为正整数 |
| `--install-deps` | 显式安装 Ubuntu apt 构建依赖；不传则系统依赖由使用者预装 |
| `--prepare-only` | 初始化固定源码及工作目录后退出，不创建 venv、不编译；可能下载 submodule |

输出目录必须为空，工作目录不能重复使用；失败后的日志和数据库保留，不自动删除。重跑选择新的 work/output 路径。
工作目录会创建相应源码、tools、SQL 的符号链接和独立 data 目录，避免依赖仓库根目录下的历史生成数据。
不要并行对同一个源目录运行相同引擎的构建，特别是 Iceberg 的 Gradle 输出仍位于其上游源码目录。

脚本用 Python venv 安装固定 Python 依赖，不向系统 Python 执行全局 pip install，兼容 Ubuntu 的 externally-managed Python 环境。
需预装 git、python3；安装系统依赖需要 apt 网络与 sudo 权限，源码/依赖下载也需要网络。
DataFusion 还需先安装 [rustup](https://rustup.rs)，脚本安装并使用 Rust 1.88.0，不改变用户默认工具链。
Iceberg 要求 JDK 17；可通过 JAVA_HOME 指向既有 JDK 17，`--install-deps` 也会安装 openjdk-17-jdk。

## 数据库隔离与清理

MySQL Release/Debug 使用 `--skip-networking` 与各自工作目录下的 Unix socket。
PostgreSQL 关闭 TCP 监听并使用私有 socket 目录，不抢占本机 3306/5432 TCP 服务。
服务启动后设置 EXIT 清理，正常结束或脚本失败会尝试关闭本次服务；SIGKILL/机器断电不保证执行 trap。
不要对已有数据目录执行初始化；本脚本以新工作目录规避覆盖，保留失败现场。
Unix socket 路径受系统长度限制，建议工作目录用 `/tmp/pg-01` 等短路径，PG 路径不要含空格。

可选的 Java PG 计划诊断为独立步骤：

```bash
bash shell_scripts/audit-postgres.sh --output-dir "$HOME/planlab-logs/pg-01"
```

需要 JDK 17 和 Maven。`build-postgres.sh` 不会隐式编译 Java 项目。

## GitHub Actions

工作流执行相同脚本，只指定适合上传的输出目录：

```yaml
run: bash shell_scripts/mysql-source-trace.sh --install-deps --jobs 2 --output-dir artifacts/mysql-source-trace
```

YAML 不包含 apt、cmake、建表、数据生成等内联命令。既有软件工作流输出到 `artifacts`，Debug 工作流输出到 `artifacts/mysql-source-trace`，继续由 upload-artifact 上传。
工作流生成器 `tools/write_workflows.py` 与提交的五份软件 YAML 同步维护；公共脚本改动会触发对应实验重新验证。
