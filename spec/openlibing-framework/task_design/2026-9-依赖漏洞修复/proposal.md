# openlibing-framework 依赖漏洞修复

## 需求背景

openlibing-framework 仓依赖的三方组件存在已知安全漏洞（如 fastjson、log4j、snakeyaml、spring 系列等历史 CVE），被安全扫描工具识别为依赖漏洞，需在迭代内修复至无漏洞版本，避免生产环境被攻击风险与上线门禁拦截。

本 Issue 在 release_20260923_iter2 迭代统一修复 framework 仓依赖漏洞，扫描结果清零。

## 功能描述

### 做什么

1. **漏洞依赖识别**：基于安全扫描工具结果识别 framework 仓待修复依赖清单（含直接依赖与传递依赖）。
2. **依赖升级**：在 `pom.xml` 升级有漏洞依赖至无漏洞版本；无法升级的直接依赖通过 `<dependencyManagement>` 锁定传递依赖版本。
3. **回归验证**：升级后编译、单测、集成测试全量通过，扫描结果清零。

### 不做什么

1. 不引入新依赖（仅升级/锁定既有依赖版本）。
2. 不修复未在扫描结果中的依赖（避免无关 churn）。
3. 不重构既有调用代码（除非 API 不兼容需适配）。

## 验收标准

- [x] 安全扫描结果中 framework 仓依赖漏洞清零
- [x] 升级后 `mvn clean compile test` 全量通过
- [x] API 不兼容依赖已适配调用代码
- [x] PR 合入 `release_20260923_iter2` 分支

## 影响范围

- **openlibing-framework**：`pom.xml` 依赖版本调整；API 不兼容依赖涉及调用代码适配（具体文件以上线代码为准）
- **CI**：安全扫描任务通过

## 关联

- 业务 Issue: openlibing/openlibing-framework#106
- 业务 PR: openlibing/openlibing-framework（release_20260923_iter2 分支已合入）
