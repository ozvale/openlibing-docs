# UT 测试覆盖率插件支持 GitHub - 实现任务

## 分支与 Issue

- [x] 创建 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/280
- [x] `upload-ut-action` 分支 `feat-github-support`（基于 `origin/main`）
- [x] `openlibing-coderepo` 分支 `feat-github-ut-whitelist`（基于 `origin/master`）

## upload-ut-action 代码改造

- [x] 新增 `src/util/platform.js` 的 `detectPlatform(env)`：`GITHUB_ACTIONS=true` 且无 `ATOMGIT_*` 关键变量时判定 GitHub，双标志冲突时按 GitCode
- [x] `index.js` 新增 `resolvePlatformContext(env)`，主流程改用平台上下文（仓库、分支、运行 ID、提交 SHA、仓库名、工作区）
- [x] `index.js` 新增 `resolveGithubCommitId`：GitHub PR 事件从 `GITHUB_EVENT_PATH` 解析 `pull_request.base.sha`，缺失回退 `GITHUB_SHA`
- [x] `index.js` `setOutput` 兼容 `GITHUB_OUTPUT`（GitHub）与 `STEP_OUTPUT`（GitCode）
- [x] `src/obs/ObsUploader.js` 新增 `selectObsBucket(isGithub)`，桶与读地址按平台选择（GitHub：`openlibing-github-action`）
- [x] `src/obs/ObsUploader.js` 双标志冲突时显式覆盖 OIDC 提供商为 `GitCodeActions` / `gitcode-actions`
- [x] `package.json` OIDC SDK 升级到 `0.0.7`，同步 `package-lock.json`
- [x] `action.yml` 描述补充双平台支持，版本与 `package.json` 保持一致
- [x] `README.md` 补充 GitHub 使用方式、`id-token: write` 前置条件、输入参数表补齐 `obs_acl`、PR 分支/提交口径
- [x] `.gitleaks.toml` 新增 `^dist/` 误报白名单（ncc 产物内联第三方依赖，源码仍独立扫描）

## upload-ut-action 测试与构建

- [x] 新增 `test/platform-context.test.js`：GitHub push/PR、GitCode push/MR、双标志冲突、PR `base.sha` 上下文映射
- [x] `test/obs-uploader.test.js` 新增 `selectObsBucket` 用例
- [x] `npm test` 全部通过（63/63）
- [x] `npm run package` 重建 `dist/index.js`；grep 校验 `detectPlatform`、`openlibing-github-action`、`GitHubActions` 已内联；`action.yml` 与 `package.json` 均为 `1.0.2`
- [x] `node --check dist/index.js` 语法校验通过（仅作兜底，不作为重建依据）
- [x] `pre-commit run --files` 全部 Passed

## openlibing-coderepo 代码改造

- [x] `ObsBucketServiceImpl` 白名单由单桶改为双桶集合（`openlibing-gitcode-action` + `openlibing-github-action`）
- [x] `ObsBucketServiceImpl.downloadToTempFile` 注释同步双桶，明确"可读集合由单桶扩展为双桶"
- [x] `ObsBucketService` 接口契约注释同步双桶
- [x] `ObsBucketServiceImplTest` 新增 GitHub 桶下载成功用例，既有用例保持通过（10/10）
- [x] `mvn spotless:check` 通过

## 运维前置验证

- [ ] 华为云 IAM 信任委托 `github-actions` 的 `sub` 已限定到允许的 GitHub 组织/仓库/分支，未授权仓库换证失败
- [ ] 后端 OBS 凭证对 `openlibing-github-action` 具备 GetObject 权限，且与 `obs.endpoint` 同区域

## 交付前自检

- [x] 生成前约束自检（仅改动指定两仓、无凭证硬编码、无无关重构）
- [x] 一致性检查（proposal 验收标准 / design 关键决策 / tasks 清单与代码逐条核对）
- [x] 向用户交付本地改动文件清单与验证结果，等待用户自测

## 后续独立需求（不在本次范围）

- [ ] UT OBS 对象 key 加入 `{owner}/{repo}`，并在 `downloadToTempFile` 做 objectKey 与上报 `gitUrl` 的归属一致性校验（破坏性 key 结构变更，需独立需求 + 安全评审）
