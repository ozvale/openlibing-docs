# 单 Action 重构 — 实现任务

## 进度: 12/12 complete

- [x] T1（文档）：新增 proposal / design / tasks（docs 仓，本目录）
- [x] T2（入口）：新增根级 `action.yml`（scan-type 必填 + 全部输入，SBOM 标注 version 专用）
- [x] T3（入口）：新增根级 `index.js` 分发器（`resolveScanType` + `run(scanFn)`，非法类型失败）
- [x] T4（核心）：`shared.scan` 增加 `meta.scanType` 门控——`pr` 强制关闭 SBOM，`version`/未传保持原逻辑
- [x] T5（测试）：合并两套测试为根 `test/test-oss-scan-action.test.js`，更新 import 与 Summary 隔离
- [x] T6（测试）：新增 scan-type 解析、run 分发与 SBOM 门控用例（pr 不输出、version 输出）
- [x] T7（构建）：根 `package.json` 增加 `build` / `test` 脚本并更新 lock；UT 使用 `npx c8@10`（未新增 c8 devDependency）
- [x] T8（清理）：删除 `oss-pr-scan-action/`、`oss-version-scan-action/` 目录
- [x] T9（CI）：更新 `oss-pr-scan.yml` / `oss-version-scan.yml` 为根引用 + scan-type；PR 自测引用 `@v1.4` 标签
- [x] T10（CI）：更新 `build.yml` / `ut.yml` / `nightly-schedule-scan.yml` 为根级单次构建与测试
- [x] T11（文档）：合并 README 为单插件文档 + 旧引用迁移对照表
- [x] T12（验证）：根级 `ncc build`、全量单测、覆盖率（≥80%）、pre-commit 与 UT 流水线验证

## 验证结果

| 项目       | 结果                                                                            |
| ---------- | ------------------------------------------------------------------------------- |
| 业务分支   | `fix-oss-scan-security`（PR !11）                                               |
| 业务提交   | `b73a70d` 重构；`d307ead` workflow/README 引用 `@v1.4`；`a4bf9cf` README 格式化 |
| main 同步  | `50e6925`（main workflow 使用 `@main`）                                         |
| 单测       | 82/82 通过                                                                      |
| 覆盖率     | 总 97.59%；根 `index.js` 94.11%；`shared/index.js` 97.67%                       |
| 增量覆盖率 | 98%（660 变更行，缺失 10，UT run 32）                                           |
| 构建       | 根级 `ncc build` 成功，`dist/index.js` 62kB                                     |
| CI         | oss-pr-scan / ut-coverage / pre-commit / build 均 COMPLETED                     |

## 备注

- 业务 Issue：https://gitcode.com/openlibing/trivy-action/issues/14
- 业务分支：`fix-oss-scan-security`（沿用，PR !11）
- docs 分支：`spec-oss-scan-action-security-hardening`（沿用）
- 关键约束：`scan-type` 必填；仅 version 输出 SBOM；旧子目录删除
- 合入 master 后建议将自测 workflow 切回 `@master` 或正式版本标签
