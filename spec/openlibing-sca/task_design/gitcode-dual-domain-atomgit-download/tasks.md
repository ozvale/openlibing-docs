# GitCode 双域名与 Atomgit 文件下载映射 — 实现任务

## 进度: 6/8 complete

- [x] 新增 GitcodeUrlUtil（gitcode.domains 双域名判定 + gitcode.domain.apis 域名→API 基址映射 + normalizeToPrimaryDomain 归一化）及 GitcodeUrlUtilTest 15 用例
- [x] IntegrationApiServiceImpl：移除 replaceAtomgitDomain 紧急改写（atomgit URL 原样入库）、约 20 处单域名判定替换为 isGitcodeUrl、getRepoInfo/getVersionReposId 主域名兜底重查、urlGitCodeAdd 按域名映射 API host、queryRepoSizeKb /repos 重复拼接修复、getCodeHostingPlatformFlag atomgit→gitcode
- [x] DownLoadFilesUtils：downLoadGitcodeSence 按命中域名前缀映射 v5 API 基址（修复 atomgit mergeUrl 请求落到 Web 页面解析失败）、deleteRepoFromGitcode 双域名判定
- [x] Dockerfile：移除过时 click<8.1.0 固定、钉住 pluggy<1.7.0（修复 scancode import 崩溃）、新增 pip3 check + scancode --version 构建期冒烟
- [x] 单测：DownLoadFilesUtilsTest 新增 3 用例（atomgit/gitcode 映射 + domain.apis 生效）、IntegrationApiServiceImplTest 新增/适配约 10 用例；CI 流水线通过（`ci-pipeline-passed`）
- [x] 创建 PR #327（`ms_atomgit` → `release_20261019_iter1`，7 commits），已打 `ai-assisted` 标签
- [ ] 手动验证双域名配置下文件下载正常
- [ ] 手动验证 license-scanner 镜像构建通过冒烟校验

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/327
- 分支: `ms_atomgit` → `release_20261019_iter1`
- 关联 Issue: openlibing/openlibing-sca#88
- 前置设计 spec: atomgit-domain-compat（本 PR 为其落地交付 + 域名→API 映射扩展）
- 同迭代关联 PR: #328（复用 GitcodeUrlUtil 并扩展至评审/查询链路，含尾斜杠归一化增强）、#329（NOTICE 扫描迭代）、#330（Gitee token Bearer 化）
