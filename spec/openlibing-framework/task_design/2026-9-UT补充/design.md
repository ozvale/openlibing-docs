# openlibing-framework 相关功能 UT 补充 — 技术设计

## 方案概述

复用 framework 既有 JUnit5 + Mockito 测试体系，针对识别出的欠债 Service / Controller 模块补充单测；测试粒度按方法组织，覆盖正常路径、边界场景、异常路径。

## 架构决策

### 决策 1：复用既有测试框架

**选择**：沿用 JUnit5 + Mockito，不引入新测试框架。

**原因**：与既有测试代码风格保持一致，避免引入新依赖与学习成本。

### 决策 2：按方法粒度组织测试

**选择**：单测按被测方法组织，每方法覆盖正常 + 边界 + 异常三类用例。

**原因**：方法粒度便于回归定位；三类用例覆盖保证测试有效性。

### 决策 3：单测发现问题同步修复

**选择**：单测发现既有缺陷时同步修复，不单独开 Issue。

**原因**：避免单测欠债修复与缺陷修复脱节；同一 PR 内闭环。

## 测试组织

```text
src/test/java/com/openlibing/framework/<module>/service/impl/
├── XxxServiceImplTest.java
│   ├── methodName_normalCase()
│   ├── methodName_boundaryCase()
│   └── methodName_exceptionCase()
└── ...
```

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 单测覆盖过多导致 CI 时长上升 | CI 慢 | 仅针对欠债模块，非全仓追求 100% 覆盖；Mock 替代集成测试 |
| 单测发现既有缺陷 | 需修复后才能合并 | 同 PR 内修复，避免欠债流转 |

## 关联

- 业务 Issue: openlibing/openlibing-framework#105
- 业务 PR: openlibing/openlibing-framework（release_20260923_iter2 分支已合入）
