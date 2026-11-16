# 单 Action 重构（single-action-refactor）

## 需求背景

当前 `openlibing/trivy-action` 为“一个仓两个插件”模式：

- `oss-pr-scan-action`：PR 级门禁，`scan({ logPrefix: 'oss-pr-scan' })`
- `oss-version-scan-action`：版本级门禁，`scan({ logPrefix: 'oss-version-scan' })`

两者共用 `shared/index.js`，扫描与门禁逻辑完全一致，差异仅在入口标识、SBOM 输入暴露与 workflow 触发/检出方式。按 `openlibing/malicious-code-scan-action#28` 的单插件模式合并，减少重复产物与维护成本。

关联业务 Issue：https://gitcode.com/openlibing/trivy-action/issues/14
关联业务 PR：https://gitcode.com/openlibing/trivy-action/merge_requests/11
业务分支：`fix-oss-scan-security`（沿用）
docs 分支：`spec-oss-scan-action-security-hardening`（沿用）

## 功能描述

### 做

1. **根级单插件**：根目录新增 `action.yml` + `index.js`，保留 `shared/index.js` 作为核心；构建产物统一为根 `dist/`。
2. **scan-type 强制显式**：`scan-type` 为必填输入，仅接受 `pr` / `version`；缺失或非法直接失败（auto-detect 关闭）。
3. **SBOM 仅 version 可用**：仅 `scan-type=version` 读取 `sbom-output` / `sbom-output-type`；`pr` 强制关闭 SBOM。
4. **删除子插件目录**：删除 `oss-pr-scan-action/`、`oss-version-scan-action/`（含各自 action.yml、index.js、dist、test、package.json、README）。
5. **workflow 更新**：
   - `oss-pr-scan.yml`：根引用 + `scan-type: pr`
   - `oss-version-scan.yml`：根引用 + `scan-type: version`，保留 SBOM 输入
   - `build.yml` / `ut.yml`：根级单次 `npm ci && npm run build` / 测试
6. **测试合并**：两套用例去重合并为根级单个 `test/test-oss-scan-action.test.js`。
7. **README 合并**：单插件文档，含旧引用迁移对照表。

### 不做

- 不改变 `shared/index.js` 的扫描/判定语义与门禁阈值。
- 不新增外部依赖（除根级构建/测试工具）。
- 不修改 runner 环境；Action 引用仅从旧子路径迁移到根引用（PR 自测临时使用 `@v1.4`，main 使用 `@main`）。

## 验收标准

- [x] 根级 `action.yml` 按 `scan-type` 分发 pr/version，`scan-type` 必填且非法值失败
- [x] `pr` 模式不输出 SBOM；`version` 模式支持 `sbom-output` / `sbom-output-type`
- [x] 两个子插件目录删除，仓库内无残留引用
- [x] 两个 workflow 使用根引用 + `scan-type`；build/ut 根级单次执行
- [x] 合并后的测试全部通过，PR 增量覆盖率 ≥80%
- [x] 根级 `ncc build` 成功，dist 含统一入口
- [x] README 含迁移对照表；docs spec 更新

## 落地结果

| 项目       | 结果                                                             |
| ---------- | ---------------------------------------------------------------- |
| 业务 PR    | https://gitcode.com/openlibing/trivy-action/merge_requests/11    |
| 业务提交   | `b73a70d` 重构；`d307ead`/`a4bf9cf` workflow/README 引用 `@v1.4` |
| main 同步  | `50e6925`（main workflow 使用 `@main`）                          |
| 单测       | 82/82 通过                                                       |
| 覆盖率     | 总 97.59%；根 `index.js` 94.11%；`shared/index.js` 97.67%        |
| 增量覆盖率 | 98%（660 变更行，缺失 10）                                       |
| CI         | oss-pr-scan / ut-coverage / pre-commit / build 均 COMPLETED      |
| 标签       | `v1.4` 基于 `fix-oss-scan-security`（指向 `0979a91`）            |

## 影响范围

- 代码：根 `action.yml`、根 `index.js`、`shared/index.js`、根 `test/`
- 产物：根 `dist/index.js`、`dist/licenses.txt`
- workflow：`.gitcode/workflows/oss-pr-scan.yml`、`oss-version-scan.yml`、`build.yml`、`ut.yml`
- 文档：根 `README.md`（合并）、本 spec
- 破坏性：旧子路径引用失效，使用方需迁移到根引用 + `scan-type`
