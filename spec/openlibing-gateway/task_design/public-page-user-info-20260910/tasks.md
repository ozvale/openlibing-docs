# Tasks: 免认证页面已登录用户信息透传与 bcprov 漏洞修复

## 进度: 4/5 complete

### 阶段 1：代码变更 ✅

- [x] Task 1: AuthFilter publicInterface 分支调整
  - commit: 23958e7
  - 内容: 已登录用户访问免认证详情页面时，通过 `getNewServerWebExchange` 封装用户信息后放行（复用已有方法，+8/-3）

- [x] Task 2: bcprov-jdk18on 漏洞修复
  - commit: 08ecf1c
  - 内容: `pom.xml` 版本 1.84 → 1.85

- [x] Task 3: 单元测试修复
  - commit: 05943e3
  - 内容: 更新 `AuthFilterTest.testFilterWithPublicInterfaceAndToken`，stub 过滤器链与 JWT 解析，验证转发的 exchange 携带用户信息查询参数
  - 验证: `Tests run: 1, Failures: 0, Errors: 0`（此前全量 1453 测试仅此 1 个失败）

- [x] Task 4: 推送分支并创建 PR
  - 分支: `codechentao:chentao_release_20260910` → `openlibing:release_20260910`
  - PR: openlibing/openlibing-gateway#190（标签 `ai-assisted`，3 commits，+30/-7，3 文件）
  - CI: `ci-pipeline-passed`，可合并状态通过

### 阶段 2：发布验证 ⏳

- [ ] Task 5: PR 合并与环境验证
  - 评审人审批后合入 release_20260910
  - 部署后验证: 已登录用户访问免登录页面，下游接口可获取用户信息；未登录用户访问行为不变
  - 完成标准: 发布后稳定运行无异常

## 关联 PR

- openlibing/openlibing-gateway#190: `chentao_release_20260910` → `release_20260910`（本变更）
- openlibing/openlibing-gateway#189: 同分支前置变更（Nacos 迁移 + springdoc 修复，见 [nacos-springdoc-20260910](../nacos-springdoc-20260910/)）

## 备注

- 本变更与 PR #189 共用分支 `chentao_release_20260910`，#190 包含 #189 之后的 3 个 commit
- `getNewServerWebExchange` 为已有方法，本次仅在新路径复用，实现细节见 [design.md](design.md)
