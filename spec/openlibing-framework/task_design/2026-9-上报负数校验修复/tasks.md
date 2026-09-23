# 上报负数响应成功未校验修复 — 实现任务

## 进度: 4/4 complete

### Task 1: 入参校验补齐

- [x] 上报类 DTO 计数值/统计量字段添加 `@Min(0)` / `@PositiveOrZero` 注解
- [x] 上报 Controller 类添加 `@Validated`，方法入参对象添加 `@Valid`

### Task 2: 全局异常处理

- [x] 全局 `@RestControllerAdvice` 新增 `MethodArgumentNotValidException` 处理方法
- [x] 全局 `@RestControllerAdvice` 新增 `ConstraintViolationException` 处理方法
- [x] 返回 HTTP 400 + 业务错误码 + 提示信息

### Task 3: 单测补充

- [x] 新增负数入参拒绝用例（DTO 层与 Controller 层）
- [x] 新增零值与正数入参通过用例（保证非过度校验）

### Task 4: 验证

- [x] `mvn spotless:check test-compile` 通过
- [x] PR 合入 `release_20260923_iter2` 分支
