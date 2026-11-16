# 生成 updateinfo（update 发布流程元数据生成）

## 需求背景

openEuler update 发布需要生成 updateinfo.xml（安全更新元数据），供最终用户的
yum/dnf 增量更新消费。该文件由 Jenkins 任务
`update_test_directory_repodata_by_updateinfo` 在测试仓库目录上生成，
此前依赖人工触发，无平台入口、无状态跟踪。

本需求在平台内新增"生成 updateinfo"接口，触发上述 Jenkins 任务，
`update_type` 固定为 `earlyupdateinfo`（提前发布安全更新），
`update_dir` 由评审单版本号自动推导，与导入测试 repo 的目录约定保持一致。

## 需求范围

**范围内**：

- 新增 `POST /publish/jenkins/generateUpdateinfo` 接口（`OpeneulerjenkinsController`）
- 归属校验：仅评审单创建者可操作
- `update_dir` 推导：版本号中 update 日期 + 3 天
  （`..._update20240701` → `update_20240704`），复用既有 `buildUpdateDir`
- 触发 Jenkins `update_test_directory_repodata_by_updateinfo`（参数：
  `update_type=earlyupdateinfo`、`update_dir=<推导值>`，token 解密拼接）
- 新增状态槽 `generateUpdateinfoResult`
- 任务快速完成的特性：入队成功后延迟 30 秒置执行成功（不拦截执行中重复触发，
  重复触发可自愈卡住状态）
- 触发成功/失败写入评审单操作历史

**范围外**：

- Jenkins 任务执行内容本身（repodata 生成逻辑在 Jenkins 侧）
- updateinfo 的对外发布（属于后续正式发布环节）
- token 从 URL query 迁移到请求头（沿用既有 Jenkins 触发模式，风险与豁免评估
  见 `202611-sync-build-result` 的 design.md 风险说明，与该需求表述对齐）

## 验收标准

1. 非创建者调用返回 400 无权限。
2. `update_dir` 推导与导入测试 repo 的目录一致：日期 +3 天、`update_` 前缀。
3. 触发成功后 Jenkins 任务入队（HTTP 201），状态槽置执行中，
   30 秒后（`GENERATE_UPDATEINFO_WAIT_SECONDS`）自动置执行成功。
4. 触发失败时状态槽置执行失败，操作历史记录失败。
5. 执行中重复触发不拦截：可再次触发以自愈（区别于同步构建结果的幂等拦截）。

## 关联

- 业务分支：`feat-update-release-automation`（openlibing-platform-release 仓）
- 实现 commit：`989f5e56`（新增接口）、`1ecea4b7`（补充操作历史）
- 独立于七步自动化编排之外的手动能力（updateinfo 在编排完成后按需触发）
