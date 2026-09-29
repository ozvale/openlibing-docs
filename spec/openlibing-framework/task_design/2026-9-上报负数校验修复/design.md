# 上报负数响应成功未校验修复 — 技术设计

## 方案概述

在上报类接口的 DTO 字段补齐 Bean Validation 注解（`@Min` / `@PositiveOrZero`），通过 Controller 层 `@Validated` / `@Valid` 触发校验；校验失败统一由全局异常处理器转换为 HTTP 400 + 业务错误码响应。

## 架构决策

### 决策 1：DTO 层 Bean Validation 注解

**选择**：在 DTO 字段上添加 `@Min(0)` / `@PositiveOrZero` 等 JSR-380 注解。

**原因**：声明式校验、与 Spring MVC 无缝集成，无需在 service 层手写 if 校验逻辑；可被 IDE 与 Swagger 自动识别。

### 决策 2：Controller `@Validated` + `@Valid` 双触发

**选择**：Controller 类加 `@Validated`，方法入参对象加 `@Valid`，方法级单参数校验加 `@Validated`。

**原因**：方法级单参数（如 `@RequestParam @Min(0) Integer count`）需类级 `@Validated` 才能触发；对象入参需 `@Valid` 触发嵌套校验。

### 决策 3：全局异常处理器统一返回

**选择**：全局 `@RestControllerAdvice` 拦截 `MethodArgumentNotValidException`、`ConstraintViolationException`，统一返回 HTTP 400 + 业务错误码。

**原因**：避免每个 Controller 单独处理；统一返回体便于前端识别校验失败。

## 接口设计

### 校验失败响应示例

```json
{
  "code": "VALIDATION_ERROR",
  "message": "count must be greater than or equal to 0",
  "timestamp": "2026-09-23T10:00:00+08:00"
}
```

## 关键代码位置

- 上报类 DTO 字段添加 `@Min(0)` / `@PositiveOrZero`
- 上报 Controller 类添加 `@Validated`，方法入参对象添加 `@Valid`
- 全局异常处理器 `@RestControllerAdvice` 新增 `MethodArgumentNotValidException` / `ConstraintViolationException` 处理方法

## 风险与缓解

| 风险                               | 影响       | 缓解                                                 |
| ---------------------------------- | ---------- | ---------------------------------------------------- |
| 校验过于严格影响存量调用方         | 接口报错   | 与调用方沟通存量数据修复后再发布；非负字段已识别完毕 |
| Bean Validation 失败响应格式不一致 | 前端难识别 | 统一异常处理器返回，格式对齐既有业务错误响应         |

## 关联

- 业务 Issue: openlibing/openlibing-framework#60
- 业务 PR: openlibing/openlibing-framework（release_20260923_iter2 分支已合入）
