# openlibing-framework 相关功能 UT 补充

## 需求背景

openlibing-framework 仓部分功能模块单元测试覆盖度不足，存在历史欠债：部分 Service / Controller 缺少对应单测，部分边界场景未覆盖，导致回归风险增加、CI 阶段无法及时发现代码缺陷。

本 Issue 在 release_20260923_iter2 迭代对 framework 相关功能做单测补充，提升覆盖率与回归稳定性。

## 功能描述

### 做什么

1. **识别欠债模块**：扫描 framework 仓 Service / Controller 缺测方法清单。
2. **补充单测**：针对缺测模块补充正常路径 + 边界场景 + 异常路径单测。
3. **修复被测出的问题**：如单测发现既有逻辑缺陷，同步修复。

### 不做什么

1. 不对全仓做 100% 覆盖率追求（按风险评估优先级补充）。
2. 不重构既有实现代码（除非单测发现明确缺陷）。
3. 不引入新测试框架或依赖（复用既有 JUnit5 + Mockito 体系）。

## 验收标准

- [x] 识别的欠债模块单测已补充
- [x] 单测全量通过，CI 阶段无单测失败
- [x] PR 合入 `release_20260923_iter2` 分支

## 影响范围

- **openlibing-framework**：相关模块 `src/test/java/...` 下补充测试类（具体类以上线代码为准）
- **CI**：单测任务通过

## 关联

- 业务 Issue: openlibing/openlibing-framework#105
- 业务 PR: openlibing/openlibing-framework（release_20260923_iter2 分支已合入）
