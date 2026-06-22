# Tasks: 去除 webhook 回调 URL 中的 repoId 路径参数并清理重复 webhook

## 实现步骤

- [x] 1. WebhookEventDTO 移除 repoId 字段
- [x] 2. WebHookEventController 双路径映射，兼容新旧 URL
  - 新路径 `/hooks/gitcode` 和 `/hooks/gitee`
  - 旧路径 `/hooks/gitcode/{repoId}` 和 `/hooks/gitee/{repoId}`
  - 旧路径 repoId 仅记录 info 日志，不参与业务逻辑
- [x] 3. MergeRequestEventHandler token 获取改造
  - 从 webhook 消息体提取 repoUrl（project.git_http_url / repository.git_http_url）
  - 通过 repoUrl 反查所有匹配的 repoInfo
  - 单个 repoInfo：先仓库私有 token，再项目级 token（isDefault=false）
  - 多个 repoInfo：先遍历所有仓库私有 token，再遍历所有项目级 token
  - 均无效时打印 error 日志（配置日志告警）
- [x] 4. 事件去重 key 从 repoId 改为 owner/repo
- [x] 5. RepoServiceImpl.autoSetCoderepoWebHook 改造
  - 删除 beta 环境残留 webhook（URL 含 beta.openlibing.com）
  - 新 URL 精确匹配：已存在则跳过
  - 旧 URL 前缀匹配：检测到旧 webhook 时执行去重清理
  - 去重逻辑：只保留一个有效 token 对应的旧 webhook，删除其余旧 webhook
  - 新旧 URL 均不存在时创建新 webhook（不含 repoId）
- [x] 6. RepoServiceImpl 新增辅助方法
  - deleteRepoWebhookWithToken：使用公共账号 token 删除 webhook（容错处理）
  - findRepoIdWithValidToken：从多个 repoId 中找到拥有有效 token 的
  - decryptRepoAccessToken / getProjectToken / isTokenValid：token 校验辅助方法
- [x] 7. WebHookEventServiceImpl 日志中去掉 repoId
- [x] 8. 单元测试更新适配

## 关联 Issue

yanzhaohong/openlibing-coderepo#2
