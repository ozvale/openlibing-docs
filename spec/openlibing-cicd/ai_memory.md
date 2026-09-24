# openlibing-cicd — AI 可复用经验

仅沉淀经过验证且会复用的规则。

## Liquibase

- 已执行（history 表有记录）的 changeset **严禁修改内容**（checksum 校验失败会阻断服务启动）；结构变更必须另起新 changeset + preConditions 幂等守卫。
- 本项目 history 表名是自定义的 `LIQUIBASE_DATABASE_CHANGELOG`（application.yaml `database-change-log-table`），不是默认的 `DATABASECHANGELOG`。
- checksum 冲突 DB 直修法：先把表结构手工迁移到目标版本，再 `UPDATE LIQUIBASE_DATABASE_CHANGELOG SET MD5SUM='<当前部署包算出的新值>' WHERE ID=... AND AUTHOR=...`，重启即通过。
- 2026-09 实例：changeset `20260904-create-sec-option-filing` 被反复改写（V1→record_id→package_path）导致 401 环境启动失败。

## GitCode CLI

- 本机安装形态：pip 包 `gitcode-cli 0.5.5`，可执行文件 `C:\Users\admin\AppData\Local\Python\pythoncore-3.14-64\Scripts\gitcode.exe`（不在 PATH，用绝对路径调用；GC_TOKEN 已配置）。

## pre-commit（Windows 本机）

- python 实际路径 `C:\Users\admin\AppData\Local\Python\pythoncore-3.14-64\python.exe`；不在 PATH 时 local 钩子（`python scripts/run-mvn.py`）报 cmd 9009。
- Maven 钩子需要用户级环境变量 `openlibing_mvn_repo_username` / `openlibing_mvn_repo_password`（缺失 exit 2）；本地离线验证可用 `mvn -o` 等价复刻钩子 goals。
- gitleaks 钩子做全工作区扫描，`.idea/workspace.xml`、`src/main/resources/openlibing.pfx`、`target/` 为仓库既有命中，与当次改动无关（属遗留治理项）。
- `spotless:apply` 会直接改写文件，产生的格式化差异需确认后随 commit 落库。

## MQS 消息契约（PR 同步/编译）

- PR 同步主动触发走 `req_type=compile`；触发人只用统一 `account` 字段（不建平台账号组）；`br_name`=目标分支、`tgt_branch`=源分支；整体字段与 coderepo `MqsMessageSenderImpl#buildMessage` 契约对齐。
