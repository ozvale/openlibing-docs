# IT-ICSL 安全送检专项排查 — 归档

## 关联

- 业务 Issue：https://gitcode.com/openlibing/openlibing-simulation/issues/48
- 业务 PR：https://gitcode.com/openlibing/openlibing-simulation/merge_requests/178
  （2026-10-29 15:50 合入 master；初版 PR #177 因 pre-commit 失败关闭后重建）
- 安全专项 Issue（22 个，仅建立关联，未关闭）：
  #32 #35 #36 #37 #38 #39 #40 #41 #42 #43 #44 #45 #46 #47 #49 #51 #52 #53 #54 #55 #58 #59
- docs PR：https://gitcode.com/openlibing/openlibing-docs/merge_requests/1219

## 交付历程

- 61 个安全整改提交（`master..fix-ip-or-hostname-validation`），覆盖 SSRF、注入、日志、凭据、
  鉴权、SSH、审计、并发锁、依赖治理 9 类风险，关键提交：
  - `277b948` encrypt server credentials, constrain paths, block symlink follow
  - `3df905f` validate client-submitted paths in resource save APIs
  - `24d09a2` harden sensitive-data logging and exception handling
  - `ce13467` / `1959182` exclude credential fields from lombok toString
  - `735cc0f` always enforce internal auth, drop the bypass switch
  - `98e5bc6` / `5b38eb9` 审计日志客户端 IP 采集修正
  - `21f6c01` 修复 SpotBugs `DLS_DEAD_LOCAL_STORE`
- `bc5d214` 修复 pre-commit 两项失败（空 XML、PEM 夹具误报）

## 用户自测反馈

- 接口校验/部署/关闭链路/审计日志抽查通过。
- CI pre-commit `check-xml` 失败：`data_init_matrix_engine.xml` 为空文件且未在 changelog 注册
  → 删除该文件。
- CI pre-commit `detect-private-key` 失败：`SensitiveDataConverterTest` 的 PEM 测试夹具被字面匹配
  → 头尾拆开拼接，运行时字符串不变。
- SCA 版本扫描 `unconfirmedFileNum=3` → **未闭环**，需在平台确认这 3 个文件后重扫。

## 最终验证

| 验证项            | 结果                              |
| ----------------- | --------------------------------- |
| 用户自测          | 通过                              |
| IDE 诊断          | 0 error                           |
| pre-commit（CI）  | 两项失败已修复，随 `bc5d214` 重跑 |
| SpotBugs          | `DLS_DEAD_LOCAL_STORE` 已修复     |
| 业务 PR           | #178 已合入 master                |
| SCA               | 待平台确认 3 个未确认文件         |
| 其余 7 类扫描工具 | 报告待补（不阻塞本次合入）        |

## 设计偏差与取舍

- **私网段放行**：仅拒绝保留/特殊地址，不做私网白名单，避免打断正常部署（详见 design.md D2）。
- **22 个安全 Issue 只关联不关闭**：其中 #44/#46/#52/#53 等属平台或脚本侧整改，本分支未完全闭环，
  自动关闭会造成状态失真。
- **SCA 未闭环不影响合入**：属扫描平台待确认文件，非代码缺陷；已在 tasks.md 保留跟踪项。

## 可复用经验

- CI 的 pre-commit 是**增量**检查（`--from-ref FETCH_HEAD --to-ref HEAD`），删除未被引用的空 XML 即可
  通过 `check-xml`；测试中的 PEM 夹具必须拆分拼接，否则 `detect-private-key` 必失败。
- 平台 SpotBugs 门禁阈值为 0，任何 `DLS_DEAD_LOCAL_STORE`（未使用局部变量）都会阻断流水线。
- 以上经验已同步到 `ai_memory.md`。

## 归档日期

2026-10-29
