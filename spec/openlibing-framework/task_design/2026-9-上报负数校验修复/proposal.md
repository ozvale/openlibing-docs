# 上报负数响应成功未校验修复

## 需求背景

openlibing-framework 上报类接口存在输入校验缺失缺陷：上报负数（如计数值、统计量字段）时接口响应成功（HTTP 200 + success），未对负数做合法性校验，导致脏数据进入下游统计与看板，造成看板数据失真。

本需求在 openlibing-framework 仓修复负数未校验缺陷：在上报接口入参 DTO 层增加非负/范围校验，非法负数入参直接返回失败响应，阻断脏数据进入。

## 功能描述

### 做什么

1. **入参校验补齐**：上报类接口的计数值/统计量字段补齐 `@Min(0)` / `@PositiveOrZero` 等 Bean Validation 注解。
2. **全局异常处理**：校验失败时返回明确的错误响应（HTTP 400 + 业务错误码 + 提示信息），而非静默成功。
3. **测试覆盖**：补充负数入参的拒绝用例，确保校验生效。

### 不做什么

1. 不修复历史已有的负数脏数据（如有需要由运营侧单独清理）。
2. 不改写已有非负字段（仅修复本次缺陷中识别出的字段，避免无关重构）。

## 验收标准

- [x] 上报负数入参接口返回失败响应（HTTP 400），不再静默成功
- [x] 校验失败响应包含明确错误码与提示信息
- [x] 补充负数入参拒绝用例单测，全部通过
- [x] PR 合入 `release_20260923_iter2` 分支

## 影响范围

- **openlibing-framework**：上报类 Controller / DTO 添加 Bean Validation 注解（具体类以上线代码为准）
- **全局**：可能涉及全局异常处理器补充 `MethodArgumentNotValidException` / `ConstraintViolationException` 的统一处理

## 关联

- 业务 Issue: openlibing/openlibing-framework#60
- 业务 PR: openlibing/openlibing-framework（release_20260923_iter2 分支已合入）
