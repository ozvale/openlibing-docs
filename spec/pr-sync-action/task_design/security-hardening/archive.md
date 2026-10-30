# 社区安全整改批次（security-hardening）— 归档

## 关联

- 业务 PR: https://gitcode.com/openlibing/pr-sync-action/merge_requests/9（已合入）
- 业务 Issue（修复完成后由责任人验证关闭）：
  - https://gitcode.com/openlibing/pr-sync-action/issues/5
  - https://gitcode.com/openlibing/pr-sync-action/issues/6
  - https://gitcode.com/openlibing/pr-sync-action/issues/7
  - https://gitcode.com/openlibing/pr-sync-action/issues/8（部分修复：env 可覆盖，保留默认值）
  - https://gitcode.com/openlibing/pr-sync-action/issues/9
  - https://gitcode.com/openlibing/pr-sync-action/issues/10（根治：AppCode 回退禁用）
  - https://gitcode.com/openlibing/pr-sync-action/issues/11
  - https://gitcode.com/openlibing/pr-sync-action/issues/12
  - https://gitcode.com/openlibing/pr-sync-action/issues/13
  - https://gitcode.com/openlibing/pr-sync-action/issues/15（评审确认非问题，won't fix）
  - https://gitcode.com/openlibing/pr-sync-action/issues/16
  - https://gitcode.com/openlibing/pr-sync-action/issues/17
  - https://gitcode.com/openlibing/pr-sync-action/issues/18
  - https://gitcode.com/openlibing/pr-sync-action/issues/21
  - https://gitcode.com/openlibing/pr-sync-action/issues/22
- 未纳入本批次：#19（api-scan workflow，由独立 PR 交付）；#20（构建产物 chmod 收敛已随本批次交付，issue 关联见交付历程）

## 交付历程

- commit `a77820e`: APIG 请求体日志脱敏 accessToken（#5/#7/#11/#16/#21/#22）
- commit `1439098`: Gitee 令牌改为 Authorization Bearer 头传输，不再拼 URL（#6/#17）
- commit `a90dfd7`: /pr-sync/trigger 触发请求停止下发 accessToken（#9，cicd 侧配套变更见 openlibing-cicd `feat/pr-sync-trigger-update-type` 分支）
- commit `06314f1`: 批量加固——轮询间隔 30s 下限（#12）、标签操作失败强警告（#13）、出站仅 HTTPS（#18）、pre-commit-action 升级 v1.0.3；新增 scripts/fix-bundle-chmod.js 构建后收敛 bundle 内 chmod 0666→0755（#20）；平台 API 基址支持 GITCODE_API_BASE_URL / GITEE_API_BASE_URL 环境变量覆盖（#8）
- commit `cf34545`: 按评审意见恢复 openlibing_apig_url 默认值与 required:false（#8 只要求可覆盖）
- commit `00d409e`: 按评审意见回滚 Action SHA 钉死，恢复 tag 引用（#15 确认非问题）
- commit `103e344`: 修复 pre-commit 工作流中文注释乱码（PowerShell GBK 误写，经验见 ai_memory）
- commit `51786be`: api-scan workflow 移出本批次（#19 由独立 PR 交付）
- commit `da2de9c`: 禁用 AppCode 静态凭证回退，仅保留 OIDC 免密认证（#10 根治；删除 openlibing_apig_code 输入与 X-Apig-AppCode 传输路径）
- 合入后追加（同 PR 合入前远端追加，非 AI 编码轮次）：任务结果链接可点击系列调整、account 字段改用触发人（2adbdf1）、action.yml 描述对齐（7e0ed1d/cb97b7c）

## 用户自测反馈

- #8 公网地址硬编码：初版将 openlibing_apig_url 改为必填并去掉默认值 → 评审要求"只需可覆盖、不要去掉默认值"→ 修复 commit `cf34545`
- #15 可变 tag 引用：初版钉死不可变 SHA → 评审确认内部 action 仓库受控、非问题 → 回滚 commit `00d409e`
- #19 api-scan workflow：确认由另一个 PR 交付 → 从本批次移除 commit `51786be`
- pre-commit 工作流中文注释乱码：钉 SHA 时 PowerShell 以默认 GBK 解码写坏 UTF-8 文件 → commit `103e344` 恢复，并将教训沉淀至 ai_memory.md

## 最终验证

- 单元测试：jest 18 套件 / 145 用例全部通过
- 构建：npm run all 成功；ncc 打包后 fix-bundle-chmod 脚本收敛生效，dist/index.js 无 0666 残留
- 安全收敛：dist/index.js 无 AppCode（X-Apig-AppCode）代码路径残留；日志脱敏正则覆盖 accessToken 字段
- 流程验证：AppCode 回退禁用后，未声明 id-token 的工作流将跳过执行并输出迁移指引（预期行为变化，已在 PR 描述告知各接入仓检查）

## 设计偏差与取舍

- #10 选择彻底禁用 AppCode 回退而非警告缓解（评审升级）：静态共享凭证无轮换机制，保留代码入口即保留风险；代价是未声明 id-token 的存量工作流需要补声明后才能使用
- #8 选择保留默认网关地址：评审确认"只需可覆盖"，避免破坏依赖默认值的存量接入
- #20 选择构建后收敛而非升级依赖：上游 @actions/io 全版本（含 3.0.2）均含该回退且 3.x 为 ESM 无法被 CJS exec 引用；该代码路径运行时不可达，仅满足最小化基线，上游 toolkit 建议同步跟进
- #15 选择不钉 SHA：评审确认内部 action 仓库受控、可变 tag 非风险项

## 可复用经验

- 已沉淀至 ai_memory.md（Windows 编码、GitCode 触发器 comments 语义、双域名口径）

## 归档日期

2026-10-30
