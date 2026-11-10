# UT 测试覆盖率插件支持 GitHub - 实现任务

## 分支与 Issue

- [x] 创建 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/280
- [x] `upload-ut-action` 分支 `feat-github-support`（基于 `origin/main`）
- [x] `openlibing-coderepo` 分支 `feat-github-ut-whitelist`（基于 `origin/master`）

## upload-ut-action 代码改造

- [x] `index.js` 新增 `resolvePlatformContext(env)`：`GITHUB_ACTIONS` 单点判定，GitHub/GitCode 变量完全分离
- [x] `index.js` 主流程改用平台上下文（仓库、分支、运行 ID、提交 SHA、仓库名、工作区）
- [x] `index.js` `setOutput` 兼容 `GITHUB_OUTPUT`（GitHub）与 `STEP_OUTPUT`（GitCode）
- [x] `src/obs/ObsUploader.js` 新增 `selectObsBucket(isGithub)`，桶与读地址按平台选择（GitHub：`openlibing-github-action`）
- [x] `package.json` OIDC SDK 升级到 `0.0.7`，同步 `package-lock.json`
- [x] `action.yml` 描述补充双平台支持，版本与 `package.json` 保持一致
- [x] `README.md` 补充 GitHub 使用方式、`id-token: write` 前置条件、输入参数表补齐 `obs_acl`
- [x] `.gitleaks.toml` 新增 `^dist/` 误报白名单（ncc 产物内联第三方依赖，源码仍独立扫描）

## upload-ut-action 测试与构建

- [x] 新增 `test/platform-context.test.js`：GitHub push/PR、GitCode push/MR 上下文映射
- [x] `test/obs-uploader.test.js` 新增 `selectObsBucket` 用例
- [x] `npm test` 全部通过（56/56）
- [x] `npm run package` 重建 `dist/index.js`，`npm run zip` 生成发布包并自增 `action.yml` 版本到 `1.0.2`
- [x] `node --check dist/index.js` 语法校验通过
- [x] `pre-commit run --files` 全部 Passed

## openlibing-coderepo 代码改造

- [x] `ObsBucketServiceImpl` 白名单由单桶改为双桶集合（`openlibing-gitcode-action` + `openlibing-github-action`）
- [x] `ObsBucketServiceImpl.downloadToTempFile` 注释同步双桶
- [x] `ObsBucketService` 接口契约注释同步双桶
- [x] `ObsBucketServiceImplTest` 新增 GitHub 桶下载成功用例，既有用例保持通过（10/10）
- [x] `mvn spotless:check` 通过

## 交付前自检

- [x] 生成前约束自检（仅改动指定两仓、无凭证硬编码、无无关重构）
- [x] 一致性检查（proposal 验收标准 / design 关键决策 / tasks 清单与代码逐条核对）
- [x] 向用户交付本地改动文件清单与验证结果，等待用户自测
