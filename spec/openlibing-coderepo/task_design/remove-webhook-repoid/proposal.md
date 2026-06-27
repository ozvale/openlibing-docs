# Proposal: 去除 webhook 回调 URL 中的 repoId 路径参数并清理重复 webhook

## 背景

当前 webhook 回调 URL 中包含 repoId 路径参数（如 `/hooks/gitcode/401534`），存在以下问题：

1. **安全风险**：repoId 是数据库主键，暴露在 URL 中存在信息泄露风险
2. **重复 webhook**：同一代码仓被录入到多个项目时，会创建多个含不同 repoId 的 webhook，导致 MR 事件被重复处理，产生重复的告警抑制注释代码检视意见
3. **token 获取不合理**：通过 repoId 直接查 repoInfo 获取 token，当 repoId 对应的 repoInfo 无有效 token 时无法回退到其他 repoInfo 的 token
4. **beta 环境残留**：部分代码仓存在 beta 环境测试时创建的 webhook 残留

## 需求

1. 去除 webhook 回调 URL 中的 repoId 路径参数，新 URL 格式为 `/hooks/gitcode`（不含 repoId）
2. 兼容旧 URL（含 repoId），旧路径仍可正常处理事件，repoId 仅记录日志
3. webhook 事件处理中的 token 获取改为通过 repoUrl 反查 repoInfo，按优先级获取有效 token
4. autoSetCoderepoWebHook 检测到旧格式 webhook 时，清理重复的旧 webhook，删除 beta 环境残留 webhook
5. 新建 webhook 时使用新 URL 格式（不含 repoId）

## 验收标准

- 新创建的 webhook URL 不含 repoId
- 旧 URL（含 repoId）仍可正常接收和处理 webhook 事件
- 同一代码仓只保留一个 coderepo webhook
- beta 环境残留 webhook 被自动清理
- token 获取失败时打印 error 日志（用于配置日志告警）

## 关联 Issue

yanzhaohong/openlibing-coderepo#2
