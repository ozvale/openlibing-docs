# oss-version-scan-action — 版本级开源漏洞与 license 扫描门禁插件

## 需求背景

openlibing 版本级流水线「开源漏洞 + license 扫描」环节，使用与 PR 级完全相同的
`scan_vuls.sh`（trivy fs）逻辑，只是扫描对象为**全量分支代码**（非 PR 预合并），
触发方式为定时/手动。为统一插件化能力，在本次 `oss-scan-action` 仓中增加
版本级插件 `oss-version-scan-action`，与已交付的 `oss-pr-scan-action` 共享核心逻辑。

## 功能描述

### 做什么

1. 在 `schedule`(定时) / `workflow_dispatch`(手动) 事件下触发。**开发自测阶段仅保留
   `workflow_dispatch` 手动触发**，schedule 待正式接入时配置。
2. 由 `checkout` 插件检出目标分支全量代码（`token: ${{ secrets.ROBOT_TOKEN }}`，
   与多仓 checkout 一致），插件不做 git 操作。
3. 复用共享核心 `shared/`：执行 trivy fs 扫描（vuln + license）→ 解析 JSON →
   统计 HIGH/CRITICAL 漏洞与 license 数 → 按 ignore 阈值判定 pass/no pass →
   写入 Step Summary。
4. 判定逻辑与 `scan_vuls.sh` 完全一致，与 `oss-pr-scan-action` 复用同一套实现。

### 不做什么

- **不创建 Issue**：版本级扫描不建 issue，建 issue 行为与扫描门禁解耦（后续按需独立设计）。
- 插件不接收 token 输入：代码获取仅由 workflow 层 `checkout` 完成。
- 不调用平台后端 API，不使用 OIDC/AK/SK。

## 输入参数（action.yml 草案）

| 参数                   | 必填 | 默认值                                      | 说明                  |
| ---------------------- | ---- | ------------------------------------------- | --------------------- |
| `scan-target`          | 否   | `.`（工作区根目录）                         | 待扫描的代码目录路径  |
| `trivy-config`         | 否   | `/opt/cached_resources/trivy_db/trivy.yaml` | trivy 配置文件        |
| `cache-dir`            | 否   | `/opt/cached_resources/trivy_db`            | trivy 漏洞库缓存目录  |
| `ignore-vuln-count`    | 否   | `0`                                         | 高危漏洞豁免个数      |
| `ignore-license-count` | 否   | `0`                                         | 高危 license 豁免个数 |
| `debug`                | 否   | `false`                                     | 开启调试日志          |

> 与 PR 级插件输入完全一致；版本级不额外引入 repository/branch/create-issue 参数。

## 验收标准

- [ ] 插件在全量分支代码上正确执行 trivy 扫描并解析结果
- [ ] 判定逻辑与 `oss-pr-scan-action` 完全一致（同一 shared 实现）
- [ ] 不通过时 `core.setFailed` 阻断流水线
- [ ] workflow_dispatch 手动触发可指定扫描目标（任意分支全量）
- [ ] 无硬编码凭据；单测覆盖解析与判定核心逻辑

## 影响范围

- 同仓：`openlibing-test/oss-scan-action`
- 新增：`oss-version-scan-action/`（action.yml + index.js + dist + package.json + test + README）
- 抽取共享：`shared/index.js`（PR 级同步重构，行为不变）
- 本需求仅在 `openlibing-test` 测试组织开发验证

## 关联

- 迁移基准：`openlibing-ci/scan/opensource/scan_vuls.sh`（与 PR 级同一脚本）
- 共享核心：`oss-scan-action/shared/`（PR + version 复用）
- 测试组织，不关联业务 Issue
