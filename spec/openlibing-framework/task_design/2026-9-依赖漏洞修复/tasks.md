# openlibing-framework 依赖漏洞修复 — 实现任务

## 进度: 4/4 complete

### Task 1: 漏洞依赖识别

- [x] 基于安全扫描结果识别 framework 仓待修复依赖清单（直接依赖 + 传递依赖）
- [x] 按风险等级与升级难度排序

### Task 2: 依赖升级与锁定

- [x] 直接依赖 `pom.xml` 升级至无漏洞版本
- [x] 传递依赖通过 `<dependencyManagement>` 锁定版本兜底

### Task 3: API 不兼容适配

- [x] 升级造成 API 不兼容的依赖同步适配调用代码
- [x] 单测同步修复（保留原有测试覆盖语义）

### Task 4: 验证

- [x] `mvn clean compile test` 全量通过
- [x] 安全扫描结果 framework 仓依赖漏洞清零
- [x] PR 合入 `release_20260923_iter2` 分支
